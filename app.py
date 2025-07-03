import streamlit as st
import pandas as pd
import re

# 擷取 log 檔中的 Approval ID
@st.cache_data
def extract_approval_ids_from_log(file):
    content = file.read().decode('utf-8')
    return re.findall(r'Approval ID[:：]\s*([A-Z0-9]+)', content)

# 擷取對帳檔中的授權碼 (支援標題合併與部分匹配)
@st.cache_data
def extract_auth_codes_from_paydetail(file):
    try:
        # 先讀取表頭
        df = pd.read_excel(file, header=0)
    except Exception:
        st.error("無法讀取 Excel 檔，請確認檔案格式為 .xls 或 .xlsx。")
        return []
    # 嘗試標準欄位名
    for col in df.columns:
        name = str(col).strip()
        if any(keyword in name for keyword in ["授權", "授权", "Auth"]):
            return df[col].dropna().astype(str).str.strip().tolist()
    # 若標準 header 找不到，讀取原始表格掃描前 5 列
    df_raw = pd.read_excel(file, header=None)
    header_row = header_col = None
    for i in range(min(5, len(df_raw))):
        for j, cell in enumerate(df_raw.iloc[i].tolist()):
            text = str(cell)
            if any(keyword in text for keyword in ["授權", "授权", "Auth"]):
                header_row, header_col = i, j
                break
        if header_row is not None:
            break
    if header_row is None:
        st.error("未找到授權碼欄位，請確認檔案中包含對應標題。")
        return []
    # 從 header_row + 1 開始抓取該欄所有值
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
