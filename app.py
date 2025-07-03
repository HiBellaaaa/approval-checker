import streamlit as st
import pandas as pd
import re
import requests
from datetime import datetime, time as dtime

# 擷取 log 內容中的 Approval ID，並過濾時間\ n@st.cache_data
 def extract_approval_ids_from_text(content: str, cutoff: dtime, target_date: str):
    ids = []
    for line in content.splitlines():
        m = re.match(r"(\d{4}-\d{2}-\d{2})_(\d{2}):(\d{2}):(\d{2}).*Approval ID[:：]\s*([A-Z0-9]+)", line)
        if m:
            date_part, hh, mm, ss, code = m.groups()
            if date_part == datetime.strptime(target_date, "%Y%m%d").strftime("%Y-%m-%d"):
                t = dtime(int(hh), int(mm), int(ss))
                if t <= cutoff:
                    ids.append(code)
    return ids

# 擷取對帳檔中的授權碼，並過濾交易日\ n@st.cache_data
 def extract_auth_codes_from_paydetail(file, target_date: str):
    try:
        df = pd.read_excel(file, header=0)
    except Exception:
        st.error("無法讀取 Excel 檔，請確認格式為 .xls 或 .xlsx。")
        return []
    auth_col, date_col = None, None
    for col in df.columns:
        name = str(col)
        if any(k in name for k in ["授權", "授权", "Auth"]):
            auth_col = col
        if "交易日" in name or "Trans Date" in name:
            date_col = col
    if auth_col is None:
        st.error("未找到授權碼欄位。")
        return []
    if date_col is not None:
        # 定義正規化函式，將各種日期格式轉為 YYYYMMDD
        def _normalize(val):
            if pd.isna(val):
                return ""
            if isinstance(val, datetime):
                return val.strftime('%Y%m%d')
            s = str(val).strip()
            # 處理6位數如250703，補前綴20
            if re.fullmatch(r'\d{6}', s):
                return '20' + s
            # 處理8位數如20250703
            if re.fullmatch(r'\d{8}', s):
                return s
            # 處理斜線分隔日期如2025/07/03
            try:
                return datetime.strptime(s, '%Y/%m/%d').strftime('%Y%m%d')
            except:
                return s
        df['norm_date'] = df[date_col].apply(_normalize)
        df = df[df['norm_date'] == target_date]
    return df[auth_col].dropna().astype(str).str.strip().tolist()

st.title("授權碼比對工具")
st.markdown('<span style="font-size:12pt; font-weight:bold;">針對卡機連線異常狀況</span>', unsafe_allow_html=True)

# 上傳、輸入與流程省略，保持原有邏輯
# ...
