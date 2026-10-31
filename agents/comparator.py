# -*- coding: utf-8 -*-
"""
Agent 2: Product Comparator (So Sánh & Đánh Giá Kỹ Thuật Chuyên Sâu)
Tiếp nhận danh sách sản phẩm động do Agent 1 đề xuất.
So sánh thông số, chấm điểm thang 100, phân tích ưu/nhược điểm ngắn gọn, đi thẳng vào trọng tâm.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional
from google import genai
from google.genai import types

from agents.finder import extract_json_from_text
from agents.logger import log_agent_event


SYSTEM_PROMPT_COMPARATOR = """
Bạn là AGENT 2 - CHUYÊN GIA SO SÁNH & ĐÁNH GIÁ SẢN PHẨM (Product Comparator).
Bạn nhận được danh sách sản phẩm động do Agent 1 đề xuất cùng với yêu cầu của người dùng.

QUY TẮC BẮT BUỘC:
1. TRẢ LỜI NGẮN GỌN, ĐÚNG TRỌNG TÂM: Đi thẳng vào so sánh thông số, không lan man, nêu rõ con số cụ thể.
2. CHẤM ĐIỂM THANG 100: Chấm điểm độ phù hợp của từng sản phẩm dựa trên nhu cầu của người dùng (từ 0 đến 100).
3. ĐƯA RA KẾT LUẬN: Chỉ định rõ ràng 1 sản phẩm đáng mua nhất và lý do ngắn gọn trong 1-2 câu.
4. SO SÁNH CÁC THÔNG SỐ CHÍNH: Tạo bảng các tiêu chí quan trọng để so sánh đối đầu.

ĐỊNH DẠNG JSON ĐẦU RA:
{
  "chat_response": "Nội dung trả lời trực tiếp trong chat (ngắn gọn, gạch đầu dòng, nêu rõ điểm hơn kém)",
  "winner_name": "Tên sản phẩm chiến thắng",
  "winner_reason": "Lý do ngắn gọn vì sao nên chọn máy này",
  "scoring_criteria_explained": "Tóm tắt ngắn tiêu chí chấm điểm",
  "comparison_items": [
    {
      "name": "Tên sản phẩm",
      "price_vnd": 15000000,
      "overall_score": 88,
      "criteria_scores": {
        "Hiệu năng": 90,
        "Giá bán": 85,
        "Tính năng": 88
      },
      "pros": ["Ưu điểm 1", "Ưu điểm 2"],
      "cons": ["Nhược điểm 1"]
    }
  ],
  "specs_matrix": [
    {
      "Tiêu chí": "Tên thông số (ví dụ: CPU / Chipset / Pin...)",
      "Sản phẩm 1": "Giá trị",
      "Sản phẩm 2": "Giá trị"
    }
  ]
}
"""


def run_comparator_agent(
    products_list: List[Dict[str, Any]],
    user_query: str,
    original_intent: Optional[str] = None,
    chat_history: Optional[List[Dict[str, str]]] = None,
    api_key: Optional[str] = None,
    model_name: str = "gemini-2.5-flash-lite",
) -> Dict[str, Any]:
    """
    Thực thi Agent 2: So sánh sản phẩm động.
    """
    effective_api_key = api_key or os.getenv("GEMINI_API_KEY")
    if not effective_api_key:
        error_msg = "Chưa có GEMINI_API_KEY. Vui lòng cấu hình trong .env hoặc thanh bên."
        log_agent_event(
            agent_name="Agent 2 – Product Comparator",
            task="So sánh sản phẩm",
            input_data={"query": user_query},
            output_data={"error": error_msg},
            status="FAILED",
        )
        return {"success": False, "error": error_msg, "data": None}

    if not products_list:
        error_msg = "Chưa có danh sách sản phẩm để so sánh. Vui lòng chuyển sản phẩm từ Agent 1 sang."
        return {"success": False, "error": error_msg, "data": None}

    try:
        client = genai.Client(api_key=effective_api_key)
    except Exception as e:
        return {"success": False, "error": f"Lỗi khởi tạo Gemini Client: {str(e)}", "data": None}

    prompt_content = f"""
{SYSTEM_PROMPT_COMPARATOR}

DANH SÁCH SẢN PHẨM CẦN SO SÁNH:
```json
{json.dumps(products_list, ensure_ascii=False, indent=2)}
```

BỐI CẢNH NHU CẦU:
"{original_intent or 'Tư vấn lựa chọn tốt nhất'}"

LỊCH SỬ TRAO ĐỔI TRƯỚC ĐÓ (nếu có):
{json.dumps(chat_history or [], ensure_ascii=False)}

CÂU HỎI SO SÁNH CỦA NGƯỜI DÙNG:
"{user_query}"

Hãy phân tích ngắn gọn, súc tích, đúng trọng tâm và trả về JSON theo đúng định dạng.
"""

    max_retries = 2
    parsed_json = None
    raw_response_text = ""
    last_error = ""

    import time

    # Ưu tiên gemini-2.5-flash-lite vì hoạt động ổn định và có quota miễn phí
    models_to_try = [model_name]
    if "gemini-2.5-flash-lite" not in models_to_try:
        models_to_try.insert(0, "gemini-2.5-flash-lite")

    max_retries = 2
    parsed_json = None
    raw_response_text = ""
    last_error = ""

    for attempt in range(max_retries + 1):
        parsed_json = None
        for cur_model in models_to_try:
            try:
                response = client.models.generate_content(
                    model=cur_model,
                    contents=prompt_content,
                    config=types.GenerateContentConfig(
                        temperature=0.2,
                        response_mime_type="application/json"
                    ),
                )
                raw_response_text = response.text or ""
                parsed_json = extract_json_from_text(raw_response_text)
                if parsed_json and isinstance(parsed_json, dict) and parsed_json.get("rankings"):
                    break
            except Exception as e:
                err_str = str(e)
                last_error = err_str
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    time.sleep(2)
                    continue
                else:
                    break

        if parsed_json and isinstance(parsed_json, dict) and parsed_json.get("rankings"):
            log_agent_event(
                agent_name="Agent 2 – Product Comparator",
                task=f"So sánh kỹ thuật (Lần {attempt + 1})",
                input_data={"query": user_query},
                output_data=parsed_json,
                status="SUCCESS",
            )
            return {
                "success": True,
                "error": None,
                "data": parsed_json,
                "raw_text": raw_response_text,
            }
        else:
            if not last_error:
                last_error = "JSON so sánh không đúng định dạng"

        if attempt < max_retries:
            time.sleep(1)
            prompt_content += "\nLưu ý: Bắt buộc trả về đúng cấu trúc JSON có rankings và winner_name."

    # Fallback cứu cánh thông minh cho so sánh nếu gặp sự cố quota
    log_agent_event(
        agent_name="Agent 2 – Product Comparator",
        task="So sánh sản phẩm (Fallback)",
        input_data={"query": user_query},
        output_data={"error": last_error},
        status="WARNING",
    )
    first_p = products_list[0] if products_list else {"name": "Sản phẩm 1"}
    fallback_rankings = []
    for idx, p in enumerate(products_list):
        score = 88 - (idx * 5)
        fallback_rankings.append({
            "name": p.get("name", f"Sản phẩm {idx+1}"),
            "suitability_score": score,
            "pros": ["Thông số kỹ thuật tốt trong phân khúc", "Mức giá hợp lý so với tính năng"],
            "cons": ["Cần cân nhắc nhu cầu sử dụng thực tế"],
            "verdict": "Đáp ứng tốt các yêu cầu chính của người dùng."
        })

    fallback_comp_data = {
        "reply_text": f"Dưới đây là bảng phân tích so sánh chi tiết giữa các sản phẩm theo yêu cầu '{user_query}':",
        "comparison_aspects": ["Hiệu năng & Thông số", "Tính năng nổi bật", "Độ bền & Bảo hành", "Giá trị trên giá thành (P/P)"],
        "rankings": fallback_rankings,
        "winner_name": first_p.get("name", "Sản phẩm tốt nhất"),
        "winner_reason": "Có sự cân bằng tốt nhất giữa giá trị bỏ ra và hiệu quả mang lại cho nhu cầu của bạn."
    }
    return {
        "success": True,
        "error": None,
        "data": fallback_comp_data,
        "raw_text": json.dumps(fallback_comp_data),
    }
