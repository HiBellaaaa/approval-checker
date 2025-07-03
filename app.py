import streamlit as st
import pandas as pd
import re

# 擷取 log 檔中的 Approval ID
@st.cache_data
def extract_approval_ids_from_log(file):
    content = file.read().decode('utf-8')
    return re.findall(r'Approval ID[:：]\s*([A-Z0-9]+)', content)

# 擷取對帳檔中的授權碼
@st.cache_data
def extract_auth_codes_from_paydetail(file):
    try:
        df = pd.read_excel(file)
    except Exception:
        st.error("無法讀取 Excel 檔，請確認檔案格式為 .xls 或 .xlsx。")
        return []
    if "授權碼" in df.columns:
        return df["授權碼"].dropna().astype(str).str.strip().tolist()
    else:
        st.error("未找到 '授權碼' 欄位，請確認檔案中包含此欄位。")
        return []

st.title("Approval ID 比對工具")

# 上傳對帳檔 (Excel)
pay_file = st.file_uploader(
    "1. 請上傳對帳檔（檔名開頭：PayDetailRpt，Excel 檔 .xls/.xlsx）", 
    type=["xls", "xlsx"],
)
# 上傳 log 檔 (txt)
log_file = st.file_uploader(
    "2. 請上傳 log 檔案（例如：20250703_ui.txt）", 
    type=["txt"],
)

if pay_file:
    if not pay_file.name.startswith("PayDetailRpt"):
        st.warning("檔名不符合開頭 'PayDetailRpt'，請確認後再上傳。")

if pay_file and log_file:
    with st.spinner("處理中..."):
        auth_codes = extract_auth_codes_from_paydetail(pay_file)
        approval_ids = extract_approval_ids_from_log(log_file)

        # 找出未配對的授權碼
        unmatched = sorted(set(auth_codes) - set(approval_ids))

        st.subheader("比對結果：對帳檔中未出現在 log 檔的授權碼")
        st.write(f"共 {len(unmatched)} 筆未配對")
        st.dataframe(pd.DataFrame(unmatched, columns=["未配對的授權碼"]))
