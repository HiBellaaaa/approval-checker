import streamlit as st
import pandas as pd
import re

def extract_approval_ids_from_log(file):
    content = file.read().decode('utf-8')
    approval_ids = re.findall(r'Approval ID[:：]\s*([A-Z0-9]+)', content)
    return pd.Series(approval_ids, name="Approval ID")

def extract_auth_codes_from_paydetail(file):
    df = pd.read_csv(file)
    if "授權碼" in df.columns:
        auth_codes = df["授權碼"].dropna().astype(str).str.strip()
        return auth_codes.rename("Auth Code")
    else:
        st.error("未找到 '授權碼' 欄位，請確認檔案格式。")
        return pd.Series([], name="Auth Code")

st.title("Approval ID 比對工具")

pay_file = st.file_uploader("請上傳對帳檔（檔名開頭：PayDetailRpt）", type=['csv'])
log_file = st.file_uploader("請上傳 log 檔案（例如：20250703_ui.txt）", type=['txt'])

if pay_file and log_file:
    with st.spinner("處理中..."):
        pay_auth_codes = extract_auth_codes_from_paydetail(pay_file)
        log_approval_ids = extract_approval_ids_from_log(log_file)

        unmatched = sorted(set(pay_auth_codes) - set(log_approval_ids))

        st.subheader("比對結果 - 對帳檔中未出現在 log 檔的授權碼：")
        st.write(f"共 {len(unmatched)} 筆")
        st.dataframe(pd.DataFrame(unmatched, columns=["未配對的授權碼"]))