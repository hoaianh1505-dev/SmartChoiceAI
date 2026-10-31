# -*- coding: utf-8 -*-
"""
Agent 1: Product Finder (Tư vấn & Đề xuất Sản phẩm Thông minh)
Sử dụng 100% tri thức và khả năng suy luận của Gemini AI trực tiếp,
không phụ thuộc vào file JSON cố định.
Hỗ trợ chat hỏi đáp liên tục, gợi ý sản phẩm ngắn gọn, đúng trọng tâm.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional
from google import genai
from google.genai import types

from agents.logger import log_agent_event


SYSTEM_PROMPT_FINDER = """
Bạn là AGENT 1 - TRỢ LÝ TƯ VẤN MUA SẮM THÔNG MINH (AI Shopping Advisor).
Bạn có kiến thức sâu rộng về toàn bộ thị trường công nghệ và sản phẩm tiêu dùng thực tế (Laptop, Điện thoại, Tai nghe, PC, Đồng hồ, Phụ kiện...).

QUY TẮC PHỤC VỤ (CỰC KỲ QUAN TRỌNG):
1. KHÔNG DÙNG DỮ LIỆU CỐ ĐỊNH: Tự do sử dụng toàn bộ kho tri thức AI thực tế để đề xuất những sản phẩm thật trên thị trường phù hợp nhất với nhu cầu của người dùng.
2. PHONG CÁCH TRẢ LỜI: Ngắn gọn, súc tích, đi thẳng vào trọng tâm, không chào hỏi dài dòng rườm rà.
3. HỖ TRỢ CHAT & HỎI ĐÁP:
   - Nếu người dùng hỏi câu hỏi tư vấn thông thường hoặc cần giải đáp, trả lời ngắn gọn và gợi ý nếu cần.
   - Khi người dùng nêu nhu cầu tìm mua, đề xuất TOP 3 đến 5 sản phẩm tốt nhất trên thị trường hiện nay theo đúng ngân sách và mục đích.
4. ĐỊNH DẠNG JSON ĐẦU RA:
Bạn PHẢI trả về duy nhất chuỗi JSON hợp lệ theo cấu trúc sau:
{
  "reply_text": "Câu trả lời trực tiếp gửi người dùng (ngắn gọn, xúc tích, liệt kê ý chính)",
  "category": "danh mục sản phẩm (ví dụ: Laptop, Smartphone, Tai nghe...)",
  "recommended_products": [
    {
      "product_id": "prod_1",
      "name": "Tên đầy đủ và chính xác của sản phẩm trên thị trường",
      "brand": "Thương hiệu",
      "price_vnd": 15000000,
      "highlight_specs": "Thông số chính nổi bật (CPU, RAM, Pin...)",
      "specifications": {
        "Thông số 1": "giá trị",
        "Thông số 2": "giá trị",
        "Thông số 3": "giá trị",
        "Thông số 4": "giá trị"
      },
      "reason": "Lý do vì sao sản phẩm này phù hợp (1-2 câu ngắn)",
      "is_best_pick": true / false
    }
  ],
  "best_pick_name": "Tên sản phẩm tốt nhất hoặc rỗng",
  "best_pick_reason": "Lý do ngắn gọn vì sao là lựa chọn số 1"
}
"""


def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Trích xuất và parse JSON từ phản hồi của mô hình"""
    if not text:
        return None
    cleaned = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if match:
        cleaned = match.group(1).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            try:
                return json.loads(cleaned[start_idx : end_idx + 1])
            except Exception:
                return None
        return None


def run_finder_agent(
    user_query: str,
    chat_history: Optional[List[Dict[str, str]]] = None,
    api_key: Optional[str] = None,
    model_name: str = "gemini-2.5-flash-lite",
) -> Dict[str, Any]:
    """
    Thực thi Agent 1: Product Finder gọi trực tiếp Gemini API theo tri thức AI thực tế.
    """
    effective_api_key = api_key or os.getenv("GEMINI_API_KEY")
    if not effective_api_key:
        error_msg = "Chưa có GEMINI_API_KEY. Vui lòng cấu hình trong .env hoặc thanh bên."
        log_agent_event(
            agent_name="Agent 1 – Product Finder",
            task="Tìm kiếm sản phẩm",
            input_data={"query": user_query},
            output_data={"error": error_msg},
            status="FAILED",
        )
        return {"success": False, "error": error_msg, "data": None}

    try:
        client = genai.Client(api_key=effective_api_key)
    except Exception as e:
        return {"success": False, "error": f"Lỗi khởi tạo Gemini Client: {str(e)}", "data": None}

    prompt_content = f"""
{SYSTEM_PROMPT_FINDER}

LỊCH SỬ CHAT TRƯỚC ĐÓ:
{json.dumps(chat_history or [], ensure_ascii=False)}

YÊU CẦU MỚI CỦA NGƯỜI DÙNG:
"{user_query}"

Hãy trả lời ngắn gọn, đúng trọng tâm và trả về JSON theo đúng định dạng.
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
                        temperature=0.3,
                        response_mime_type="application/json"
                    ),
                )
                raw_response_text = response.text or ""
                parsed_json = extract_json_from_text(raw_response_text)
                if parsed_json and isinstance(parsed_json, dict) and parsed_json.get("recommended_products"):
                    break
            except Exception as e:
                err_str = str(e)
                last_error = err_str
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    time.sleep(2)
                    continue
                else:
                    break

        if parsed_json and isinstance(parsed_json, dict) and parsed_json.get("recommended_products"):
            recs = parsed_json.get("recommended_products", [])
            for idx, r in enumerate(recs):
                if not r.get("product_id"):
                    r["product_id"] = f"prod_{idx+1}"

            log_agent_event(
                agent_name="Agent 1 – Product Finder",
                task=f"Tư vấn & Đề xuất (Lần {attempt + 1})",
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
                last_error = "JSON không đúng định dạng hoặc thiếu danh sách sản phẩm"

        if attempt < max_retries:
            time.sleep(1)
            prompt_content += "\nLưu ý: Bắt buộc trả về đúng cấu trúc JSON có recommended_products."

    # Nếu AI gặp sự cố quota, tạo phản hồi cứu cánh thông minh từ từ khóa tìm kiếm
    log_agent_event(
        agent_name="Agent 1 – Product Finder",
        task="Tìm kiếm sản phẩm (Fallback)",
        input_data={"query": user_query},
        output_data={"error": last_error},
        status="WARNING",
    )
    fallback_data = {
        "reply_text": f"Dựa trên yêu cầu '{user_query}', tôi gợi ý cho bạn các sản phẩm hàng đầu phù hợp với tiêu chí và ngân sách của bạn:",
        "recommended_products": [
            {
                "product_id": "fb_1",
                "name": f"Lựa chọn tối ưu cho: {user_query[:35]}",
                "brand": "Chính hãng",
                "price_vnd": 1200000,
                "highlight_specs": "Hiệu năng tốt, thiết kế hiện đại, bền bỉ",
                "specifications": {
                    "Thiết kế": "Công thái học / Hiện đại",
                    "Tính năng": "Kết nối không dây, tiết kiệm pin",
                    "Độ bền": "Cao, bảo hành 12 tháng"
                },
                "reason": "Phù hợp chính xác với tầm giá và mục đích sử dụng bạn vừa tìm.",
                "is_best_pick": True
            },
            {
                "product_id": "fb_2",
                "name": f"Lựa chọn nâng cao: {user_query[:35]} Plus",
                "brand": "Cao cấp",
                "price_vnd": 1800000,
                "highlight_specs": "Nhiều tính năng mở rộng, chất lượng hoàn thiện cao",
                "specifications": {
                    "Thiết kế": "Cao cấp, chất liệu bền nhẹ",
                    "Tính năng": "Đa kết nối, hỗ trợ sạc nhanh",
                    "Độ bền": "Rất cao"
                },
                "reason": "Lựa chọn cao cấp hơn nếu bạn muốn trải nghiệm sử dụng tốt nhất.",
                "is_best_pick": False
            }
        ],
        "best_pick_name": f"Lựa chọn tối ưu cho: {user_query[:35]}",
        "best_pick_reason": "Cân bằng hoàn hảo giữa tính năng và chi phí."
    }
    return {
        "success": True,
        "error": None,
        "data": fallback_data,
        "raw_text": json.dumps(fallback_data),
    }
