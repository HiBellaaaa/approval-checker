import streamlit as st
import pandas as pd
import re

# 擷取 log 檔中的 Approval ID
@st.cache_data
def extract_approval_ids_from_log(file):
    content = file.read().decode('utf-8')
    return re.findall(r'Approval ID[:：]\s*([A-Z0-9]+)', content)

# 擷取對帳檔中的授權碼 (支援標題合併情況)
@st.cache_data
def extract_auth_codes_from_paydetail(file):
    try:
        # 嘗試以第一列為 header
        df = pd.read_excel(file)
    except Exception:
        st.error("無法讀取 Excel 檔，請確認檔案格式為 .xls 或 .xlsx。")
        return []
    # 支援多種欄位名稱
    col_candidates = ["授權碼", "授权码", "Auth Code", "AuthCode"]
    # 先檢查標準 header
    for col in df.columns:
        if str(col).strip() in col_candidates:
            return df[col].dropna().astype(str).str.strip().tolist()
    # 如果 header 不在第一列，嘗試掃描整張表格以找出合併標題
    df_raw = pd.read_excel(file, header=None)
    header_row, header_col = None, None
    for i in range(min(5, len(df_raw))):  # 假設標題不會超過前 5 列
        for j, cell in enumerate(df_raw.iloc[i].tolist()):
            if str(cell).strip() in col_candidates:
                header_row, header_col = i, j
                break
        if header_row is not None:
            break
    if header_row is None:
        st.error("未找到授權碼欄位，請確認檔案中包含「授權碼」或「授权码」欄位。")
        return []
    # 取得 header_row 下一列開始所有非空值
    codes = df_raw.iloc[header_row+1:, header_col].dropna().astype(str).str.strip().tolist()
    return codes

st.title("Approval ID 比對工具")

# 上傳對帳檔 (Excel)
pay_file = st.file_uploader(
    "1. 請上傳對帳檔（檔名開頭：PayDetailRpt，Excel 檔 .xls/.xlsx）", 
    type=["xls", "xlsx"]
)
# 上傳 log 檔 (txt)
log_file = st.file_uploader(
    "2. 請上傳 log 檔案（例如：20250703_ui.txt）", 
    type=["txt"]
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
