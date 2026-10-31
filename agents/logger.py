"""
Module quản lý logs hoạt động của các AI Agent.
Lưu vết: Nhiệm vụ, Đầu vào, Đầu ra JSON, Trạng thái và Dữ liệu đã chuyển giữa 2 agents.
Không hiển thị chain-of-thought nội bộ.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
import streamlit as st

def init_logger():
    if "agent_logs" not in st.session_state:
        st.session_state.agent_logs = []

def log_agent_event(
    agent_name: str,
    task: str,
    input_data: Any,
    output_data: Any,
    status: str = "SUCCESS",
    transferred_data: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Ghi nhận một sự kiện hoạt động của AI Agent.
    status: SUCCESS | FAILED | WARNING | INFO
    """
    init_logger()
    log_entry = {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "agent_name": agent_name,
        "task": task,
        "input_data": input_data,
        "output_data": output_data,
        "status": status,
        "transferred_data": transferred_data
    }
    st.session_state.agent_logs.append(log_entry)
    return log_entry

def get_agent_logs() -> List[Dict[str, Any]]:
    init_logger()
    return st.session_state.agent_logs

def clear_agent_logs():
    st.session_state.agent_logs = []
