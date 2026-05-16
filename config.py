import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()  # 自动读取项目根目录的 .env 文件

SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"
MODEL = "deepseek-ai/DeepSeek-V3"


def get_api_key() -> str:
    # 优先级：Streamlit Cloud secrets > .env / 系统环境变量
    if hasattr(st, "secrets") and "SILICONFLOW_API_KEY" in st.secrets:
        return st.secrets["SILICONFLOW_API_KEY"]
    return os.getenv("SILICONFLOW_API_KEY", "")
