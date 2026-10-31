# -*- coding: utf-8 -*-
"""
SmartChoice AI – Trợ lý AI Tư vấn và So sánh Sản phẩm Thực tế
Hoạt động linh hoạt bằng 100% Gemini AI, không dùng dữ liệu cố định.
Giao diện ô gõ trực quan, dễ nhập liệu trên mọi thiết bị.
"""

import json
import os
import re
import streamlit as st
from dotenv import load_dotenv

# Nạp biến môi trường từ .env
load_dotenv()

from agents.finder import run_finder_agent
from agents.comparator import run_comparator_agent
from agents.logger import log_agent_event, clear_agent_logs

# ----------------- Cấu hình trang -----------------
st.set_page_config(
    page_title="SmartChoice AI – Trợ Lý Mua Sắm Cá Nhân",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------- Tùy biến Giao diện CSS -----------------
st.markdown("""
<style>
    .main-title {
        font-size: 2.3rem;
        font-weight: 800;
        background: linear-gradient(90deg, #1E3A8A, #3B82F6, #06B6D4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #475569;
        margin-bottom: 1.2rem;
    }
</style>
""", unsafe_allow_html=True)


def safe_parse_score(val, default: int = 75) -> int:
    """Chuyển đổi điểm số an toàn về số nguyên 0-100"""
    try:
        if isinstance(val, (int, float)):
            return max(0, min(100, int(round(val))))
        nums = re.findall(r"\d+", str(val))
        if nums:
            return max(0, min(100, int(nums[0])))
    except Exception:
        pass
    return default


# ----------------- Khởi tạo Session State -----------------
def init_session_state():
    if "chat_history_finder" not in st.session_state:
        st.session_state.chat_history_finder = []
    if "chat_history_comparator" not in st.session_state:
        st.session_state.chat_history_comparator = []
    if "last_finder_result" not in st.session_state:
        st.session_state.last_finder_result = None
    if "transferred_products" not in st.session_state:
        st.session_state.transferred_products = None
    if "transferred_user_query" not in st.session_state:
        st.session_state.transferred_user_query = ""
    if "last_comparator_result" not in st.session_state:
        st.session_state.last_comparator_result = None
    if "active_tab_index" not in st.session_state:
        st.session_state.active_tab_index = 0
    if "pending_finder_query" not in st.session_state:
        st.session_state.pending_finder_query = None
    if "pending_comparator_query" not in st.session_state:
        st.session_state.pending_comparator_query = None

init_session_state()


# ----------------- Thanh Bên (Sidebar) -----------------
with st.sidebar:
    st.markdown("### 🛍️ SmartChoice AI")
    st.caption("Trợ Lý Mua Sắm & So Sánh Công Nghệ")

    effective_api_key = os.getenv("GEMINI_API_KEY", "")
    if effective_api_key:
        st.success("🟢 AI Sẵn Sàng (Live Gemini)")
    else:
        api_key_input = st.text_input(
            "Nhập Gemini API Key:",
            type="password",
            help="Lấy API Key tại: https://aistudio.google.com/app/apikey"
        )
        if api_key_input:
            effective_api_key = api_key_input
            st.success("✅ Đã kết nối API")

    selected_model = st.selectbox(
        "Mô hình AI:",
        options=["gemini-2.5-flash-lite", "gemini-2.5-flash"],
        index=0,
    )

    st.markdown("---")
    if st.button("🔄 Bắt đầu cuộc trò chuyện mới", use_container_width=True):
        st.session_state.chat_history_finder = []
        st.session_state.chat_history_comparator = []
        st.session_state.last_finder_result = None
        st.session_state.transferred_products = None
        st.session_state.transferred_user_query = ""
        st.session_state.last_comparator_result = None
        st.session_state.active_tab_index = 0
        st.session_state.pending_finder_query = None
        st.session_state.pending_comparator_query = None
        clear_agent_logs()
        st.rerun()


# ----------------- Header -----------------
st.markdown('<div class="main-title">SmartChoice AI Shopping Advisor</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Trò chuyện hỏi đáp, tìm kiếm bất kỳ sản phẩm nào và so sánh đối đầu chi tiết</div>', unsafe_allow_html=True)


# ----------------- Điều Hướng Tab -----------------
tab_labels = [
    "💬 1. Chat & Tìm Sản Phẩm (Agent 1)",
    "⚖️ 2. So Sánh & Chấm Điểm (Agent 2)"
]

current_tab = st.radio(
    "Chọn chế độ:",
    options=tab_labels,
    index=st.session_state.active_tab_index,
    horizontal=True,
    label_visibility="collapsed"
)
selected_tab_idx = tab_labels.index(current_tab)
if selected_tab_idx != st.session_state.active_tab_index:
    st.session_state.active_tab_index = selected_tab_idx

st.markdown("---")


# ==============================================================================
# TAB 1: CHAT & TÌM KIẾM SẢN PHẨM (AGENT 1)
# ==============================================================================
if st.session_state.active_tab_index == 0:
    st.markdown("### 💬 Trò chuyện với Agent 1: Tư Vấn & Gợi Ý Sản Phẩm")
    st.caption("Nhập bất kỳ nhu cầu hoặc câu hỏi nào vào ô bên dưới, hoặc sử dụng thanh chat ở đáy màn hình:")

    # Ô NHẬP LIỆU CHÍNH Ở ĐẦU TRANG - DỄ NHÌN, DỄ GÕ, BẤM ENTER HOẶC CLICK NÚT ĐỀU ĐƯỢC
    with st.container(border=True):
        st.markdown("**✍️ Nhập câu hỏi hoặc nhu cầu của bạn:**")
        with st.form("finder_top_form", clear_on_submit=True):
            col_in1, col_in2 = st.columns([5, 1])
            with col_in1:
                user_form_text = st.text_input(
                    "Nhập câu hỏi:",
                    placeholder="Ví dụ: Tôi cần chuột công thái học không dây văn phòng dưới 1 triệu...",
                    label_visibility="collapsed",
                    key="finder_text_input_field"
                )
            with col_in2:
                btn_send = st.form_submit_button("🚀 Gửi AI", type="primary", use_container_width=True)

    # Gợi ý nhanh các câu hỏi mẫu
    st.caption("Hoặc bấm chọn nhanh gợi ý mẫu:")
    col_q1, col_q2, col_q3, col_q4 = st.columns(4)
    with col_q1:
        if st.button("🖱️ Chuột công thái học < 1tr", use_container_width=True):
            st.session_state.pending_finder_query = "Tôi cần tìm chuột công thái học không dây làm việc văn phòng giá dưới 1 triệu."
            st.rerun()
    with col_q2:
        if st.button("💻 Laptop code & game 18tr", use_container_width=True):
            st.session_state.pending_finder_query = "Tôi có 18 triệu, tư vấn cho tôi laptop học lập trình và chơi game nhẹ."
            st.rerun()
    with col_q3:
        if st.button("📱 iPhone vs Samsung tầm 20tr", use_container_width=True):
            st.session_state.pending_finder_query = "Tầm 20 triệu nên chọn iPhone hay Samsung nào chụp ảnh đẹp và giữ giá?"
            st.rerun()
    with col_q4:
        if st.button("⌨️ Phím cơ văn phòng 1.5tr", use_container_width=True):
            st.session_state.pending_finder_query = "Tìm cho tôi bàn phím cơ không dây gõ êm cho văn phòng giá tầm 1.5 triệu."
            st.rerun()

    st.markdown("---")

    # Bắt chat input cố định ở đáy màn hình
    chat_bar_input = st.chat_input("Nhập câu hỏi hoặc yêu cầu mua sắm của bạn vào đây...")

    # XỬ LÝ TRUY VẤN TỪ MỌI NGUỒN (Ô đầu trang, Chat bar ở đáy, hoặc Nút gợi ý)
    trigger_query = None
    if st.session_state.pending_finder_query:
        trigger_query = st.session_state.pending_finder_query
        st.session_state.pending_finder_query = None
    elif btn_send and user_form_text and user_form_text.strip():
        trigger_query = user_form_text.strip()
    elif chat_bar_input and chat_bar_input.strip():
        trigger_query = chat_bar_input.strip()

    if trigger_query:
        st.session_state.chat_history_finder.append({"role": "user", "content": trigger_query})

        with st.spinner("Agent 1 đang phân tích nhu cầu và tìm kiếm sản phẩm tối ưu..."):
            res = run_finder_agent(
                user_query=trigger_query,
                chat_history=st.session_state.chat_history_finder[:-1],
                api_key=effective_api_key,
                model_name=selected_model
            )

        if res["success"]:
            data = res["data"]
            reply_text = data.get("reply_text", "")
            st.session_state.chat_history_finder.append({"role": "assistant", "content": reply_text})

            # Lưu lại danh sách sản phẩm đề xuất
            prods = data.get("recommended_products", [])
            if prods:
                st.session_state.last_finder_result = data
            st.rerun()
        else:
            error_text = f"⚠️ {res.get('error', 'Đang cập nhật đề xuất...')}"
            st.session_state.chat_history_finder.append({"role": "assistant", "content": error_text})
            st.rerun()

    # Hiển thị lịch sử hội thoại
    chat_container_finder = st.container()
    with chat_container_finder:
        if not st.session_state.chat_history_finder:
            st.info("👋 Chào bạn! Hãy nhập bất kỳ câu hỏi hoặc nhu cầu mua sắm nào của bạn vào ô bên trên hoặc thanh chat ở đáy trang.")
        for msg in st.session_state.chat_history_finder:
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.write(msg["content"])
            else:
                with st.chat_message("assistant"):
                    st.write(msg["content"])

    # Hiển thị thẻ các sản phẩm được đề xuất gần nhất
    finder_data = st.session_state.last_finder_result
    if finder_data and finder_data.get("recommended_products"):
        prods = finder_data["recommended_products"]
        best_name = finder_data.get("best_pick_name")

        st.markdown("---")
        st.markdown(f"#### 🏆 Danh Sách Sản Phẩm Được Gợi Ý ({len(prods)} sản phẩm)")

        for p in prods:
            p_name = p.get("name", "")
            is_best = p.get("is_best_pick", False) or (best_name and str(best_name).lower() in p_name.lower())

            with st.container(border=True):
                col_c1, col_c2 = st.columns([3, 1])
                with col_c1:
                    if is_best:
                        st.markdown("🌟 **ĐỀ XUẤT HÀNG ĐẦU**")
                    brand_tag = f"`{str(p.get('brand', '')).upper()}` " if p.get('brand') else ""
                    st.markdown(f"### {brand_tag}{p_name}")
                with col_c2:
                    price = p.get("price_vnd", 0)
                    if isinstance(price, (int, float)) and price > 0:
                        st.markdown(f"<h3 style='color:#DC2626; text-align:right; margin:0;'>{int(price):,} đ</h3>", unsafe_allow_html=True)
                    elif price:
                        st.markdown(f"<h3 style='color:#DC2626; text-align:right; margin:0;'>{price}</h3>", unsafe_allow_html=True)

                specs_text = p.get('highlight_specs') or 'Chưa có thông tin'
                st.markdown(f"⚙️ **Thông số chính:** {specs_text}")

                reason_text = p.get('reason', '')
                if reason_text:
                    st.info(f"💡 **Lý do chọn:** {reason_text}")

        st.markdown("---")
        if st.button("👉 CHUYỂN CÁC SẢN PHẨM NÀY QUA AGENT 2 ĐỂ SO SÁNH", type="primary", use_container_width=True):
            st.session_state.transferred_products = prods
            st.session_state.transferred_user_query = trigger_query or "So sánh các sản phẩm được đề xuất"
            log_agent_event(
                agent_name="Hệ Thống Phối Hợp",
                task="Chuyển dữ liệu sang Agent 2",
                input_data={"products_count": len(prods)},
                output_data={"names": [p.get("name") for p in prods]},
                status="SUCCESS",
            )
            # Tự động nhảy sang Tab 2
            st.session_state.active_tab_index = 1
            st.rerun()

        # Ô HỎI TIẾP Ở CUỐI TRANG NẾU ĐÃ CÓ KẾT QUẢ
        st.markdown("---")
        with st.container(border=True):
            st.markdown("**💬 Bạn muốn hỏi thêm điều gì về các sản phẩm này không?**")
            with st.form("finder_bottom_form", clear_on_submit=True):
                col_b1, col_b2 = st.columns([5, 1])
                with col_b1:
                    bottom_text = st.text_input(
                        "Hỏi tiếp:",
                        placeholder="Hỏi tiếp (ví dụ: Có mẫu nào màu trắng không? Con nào pin trâu hơn?)...",
                        label_visibility="collapsed"
                    )
                with col_b2:
                    btn_bottom_send = st.form_submit_button("💬 Gửi Tiếp", use_container_width=True)

            if btn_bottom_send and bottom_text and bottom_text.strip():
                st.session_state.pending_finder_query = bottom_text.strip()
                st.rerun()


# ==============================================================================
# TAB 2: SO SÁNH & CHẤM ĐIỂM (AGENT 2)
# ==============================================================================
else:
    st.markdown("### ⚖️ Trò chuyện với Agent 2: So Sánh & Chấm Điểm Đối Đầu")
    st.caption("Agent 2 chuyên so sánh chi tiết thông số, trả lời câu hỏi so sánh cụ thể và chấm điểm thang 100.")

    transferred = st.session_state.transferred_products

    # Chat bar ở đáy màn hình cho Tab 2
    chat_bar_comp = st.chat_input("Nhập câu hỏi so sánh hoặc tên 2-3 sản phẩm bạn muốn so sánh...")

    # NẾU CHƯA CÓ SẢN PHẨM CHUYỂN TỪ AGENT 1: CHO PHÉP NHẬP TRỰC TIẾP TÊN CÁC SẢN PHẨM CẦN SO SÁNH
    if not transferred:
        with st.container(border=True):
            st.markdown("**🔍 Bạn muốn so sánh trực tiếp những sản phẩm nào?**")
            st.caption("Bạn có thể nhập tên 2-3 sản phẩm bất kỳ để Agent 2 tìm hiểu và so sánh đối đầu ngay:")
            with st.form("direct_compare_form", clear_on_submit=True):
                col_d1, col_d2 = st.columns([5, 1])
                with col_d1:
                    direct_input = st.text_input(
                        "Sản phẩm so sánh:",
                        placeholder="Ví dụ: So sánh iPhone 15 Pro và Samsung Galaxy S24...",
                        label_visibility="collapsed"
                    )
                with col_d2:
                    btn_direct = st.form_submit_button("⚖️ So Sánh", type="primary", use_container_width=True)

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("💬 Hoặc Quay lại Chat với Agent 1 để nhận gợi ý", use_container_width=True):
                    st.session_state.active_tab_index = 0
                    st.rerun()
            with col_btn2:
                if st.button("⚡ So sánh mẫu: iPhone 15 vs Samsung S24", use_container_width=True):
                    st.session_state.pending_comparator_query = "So sánh iPhone 15 và Samsung Galaxy S24"
                    st.rerun()

        # Xử lý nếu người dùng nhập trực tiếp sản phẩm vào Tab 2
        trigger_direct = st.session_state.pending_comparator_query or (btn_direct and direct_input and direct_input.strip()) or (chat_bar_comp and chat_bar_comp.strip())
        if trigger_direct:
            st.session_state.pending_comparator_query = None
            st.session_state.chat_history_comparator.append({"role": "user", "content": trigger_direct})

            with st.spinner("AI đang tìm dữ liệu thông số của các sản phẩm để tiến hành so sánh..."):
                # Dùng finder agent tra cứu nhanh sản phẩm
                f_res = run_finder_agent(
                    user_query=f"Tìm thông số chi tiết của: {trigger_direct}",
                    chat_history=[],
                    api_key=effective_api_key,
                    model_name=selected_model
                )
                if f_res["success"] and f_res["data"].get("recommended_products"):
                    transferred = f_res["data"]["recommended_products"]
                    st.session_state.transferred_products = transferred
                    st.session_state.transferred_user_query = trigger_direct
                    st.rerun()
                else:
                    st.warning("Không tìm thấy thông tin sản phẩm. Vui lòng thử lại với tên sản phẩm cụ thể hơn.")

    else:
        # BẢNG THÔNG SỐ ĐỘNG
        st.markdown(f"**Danh sách {len(transferred)} sản phẩm đang được so sánh:**")
        table_rows = []
        for p in transferred:
            price_val = p.get('price_vnd', 0)
            price_str = f"{int(price_val):,} đ" if isinstance(price_val, (int, float)) and price_val > 0 else str(price_val)
            row = {
                "Sản phẩm": p.get("name"),
                "Giá ước tính": price_str,
                "Thông số nổi bật": p.get("highlight_specs", "")
            }
            specs = p.get("specifications", {})
            if isinstance(specs, dict):
                for k, v in specs.items():
                    row[k] = v
            table_rows.append(row)

        st.dataframe(table_rows, use_container_width=True)

        st.markdown("---")

        # Ô NHẬP CÂU HỎI SO SÁNH TRỰC TIẾP
        with st.container(border=True):
            st.markdown("**✍️ Đặt câu hỏi so sánh hoặc phân tích cho Agent 2:**")
            with st.form("comparator_top_form", clear_on_submit=True):
                col_cin1, col_cin2 = st.columns([5, 1])
                with col_cin1:
                    user_comp_form_text = st.text_input(
                        "Đặt câu hỏi so sánh:",
                        placeholder="Ví dụ: Con nào pin trâu nhất? Camera con nào chụp đêm đẹp hơn?...",
                        label_visibility="collapsed"
                    )
                with col_cin2:
                    btn_comp_send = st.form_submit_button("🚀 So Sánh", type="primary", use_container_width=True)

        # Nút tự động & gợi ý nhanh
        col_comp1, col_comp2 = st.columns([2, 1])
        with col_comp1:
            st.caption("Gợi ý hỏi nhanh:")
        with col_comp2:
            if st.button("📊 Tự động chấm điểm & so sánh toàn diện", type="secondary", use_container_width=True):
                st.session_state.pending_comparator_query = "So sánh đối đầu toàn diện các sản phẩm này, chỉ ra điểm hơn kém và chấm điểm thang 100."
                st.rerun()

        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            if st.button("⚡ Máy nào mạnh nhất?", use_container_width=True):
                st.session_state.pending_comparator_query = "Trong các sản phẩm này, con nào có hiệu năng mạnh nhất?"
                st.rerun()
        with sc2:
            if st.button("🔋 So sánh pin và độ bền", use_container_width=True):
                st.session_state.pending_comparator_query = "So sánh chi tiết về thời lượng pin và độ bền của các sản phẩm này."
                st.rerun()
        with sc3:
            if st.button("💰 Đáng tiền nhất (P/P)?", use_container_width=True):
                st.session_state.pending_comparator_query = "Xét trên tỷ lệ hiệu năng trên giá tiền (P/P), con nào đáng mua nhất?"
                st.rerun()

        # XỬ LÝ TRUY VẤN SO SÁNH
        trigger_comp = (
            st.session_state.pending_comparator_query
            or (btn_comp_send and user_comp_form_text and user_comp_form_text.strip())
            or (chat_bar_comp and chat_bar_comp.strip())
        )

        if trigger_comp:
            st.session_state.pending_comparator_query = None
            st.session_state.chat_history_comparator.append({"role": "user", "content": trigger_comp})

            with st.spinner("Agent 2 đang phân tích thông số và chấm điểm đối đầu..."):
                res2 = run_comparator_agent(
                    products_list=transferred,
                    user_query=trigger_comp,
                    original_intent=st.session_state.transferred_user_query,
                    chat_history=st.session_state.chat_history_comparator[:-1],
                    api_key=effective_api_key,
                    model_name=selected_model
                )

            if res2["success"]:
                comp_data = res2["data"]
                st.session_state.last_comparator_result = comp_data
                reply_text = comp_data.get("reply_text") or comp_data.get("chat_response") or "Đã hoàn thành so sánh đối đầu:"

                st.session_state.chat_history_comparator.append({"role": "assistant", "content": reply_text})
                st.rerun()
            else:
                error_text = f"⚠️ {res2.get('error', 'Đang phân tích...')}"
                st.session_state.chat_history_comparator.append({"role": "assistant", "content": error_text})
                st.rerun()

        # Khung chat Agent 2
        chat_container_comparator = st.container()
        with chat_container_comparator:
            for msg in st.session_state.chat_history_comparator:
                if msg["role"] == "user":
                    with st.chat_message("user"):
                        st.write(msg["content"])
                else:
                    with st.chat_message("assistant"):
                        st.write(msg["content"])

        # Hiển thị bảng chấm điểm và sản phẩm chiến thắng
        comp_res = st.session_state.last_comparator_result
        if comp_res:
            st.markdown("---")
            winner_name = comp_res.get("winner_name")
            winner_reason = comp_res.get("winner_reason")
            if winner_name:
                st.success(f"👑 **SẢN PHẨM ĐÁNG MUA NHẤT: {winner_name}**\n\n**Lý do:** {winner_reason}")

            items = comp_res.get("rankings") or comp_res.get("comparison_items", [])
            if items:
                cols_score = st.columns(len(items))
                for i, it in enumerate(items):
                    with cols_score[i]:
                        raw_sc = it.get('suitability_score') or it.get('overall_score', 80)
                        overall_sc = safe_parse_score(raw_sc)
                        with st.container(border=True):
                            st.markdown(f"**{it.get('name')}**")
                            st.markdown(f"<h2 style='color:#2563EB; margin:0;'>{overall_sc} / 100</h2>", unsafe_allow_html=True)
                            st.caption("Điểm phù hợp")

                            scores_dict = it.get("criteria_scores", {})
                            if isinstance(scores_dict, dict) and scores_dict:
                                for crit, raw_val in scores_dict.items():
                                    parsed_sc = safe_parse_score(raw_val)
                                    crit_name = str(crit).replace("_", " ")
                                    st.progress(parsed_sc / 100.0, text=f"{crit_name}: {parsed_sc}đ")

                            st.markdown("**Ưu điểm:**")
                            for pro in it.get("pros", []):
                                st.markdown(f"✅ {pro}")
                            st.markdown("**Nhược điểm:**")
                            for con in it.get("cons", []):
                                st.markdown(f"⚠️ {con}")

