import streamlit as st
import pandas as pd
import re
import requests

# 擷取 log 內容中的 Approval ID
@st.cache_data
def extract_approval_ids_from_text(content: str):
    return re.findall(r'Approval ID[:：]\s*([A-Z0-9]+)', content)

# 擷取對帳檔中的授權碼 (支援標題合併與關鍵字)
@st.cache_data
def extract_auth_codes_from_paydetail(file):
    try:
        df = pd.read_excel(file, header=0)
    except Exception:
        st.error("無法讀取 Excel 檔，請確認格式為 .xls 或 .xlsx。")
        return []
    # 關鍵字匹配欄位名
    for col in df.columns:
        name = str(col).strip()
        if any(keyword in name for keyword in ["授權", "授权", "Auth"]):
            return df[col].dropna().astype(str).str.strip().tolist()
    # 若 header 無法匹配，掃描前 5 列尋找
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
    return df_raw.iloc[header_row+1:, header_col].dropna().astype(str).str.strip().tolist()

st.title("Approval ID 比對工具")

# 1. 上傳對帳檔 (Excel)
pay_file = st.file_uploader(
    "1. 請上傳對帳檔（檔名前綴：PayDetailRpt，Excel 檔 .xls/.xlsx）", 
    type=["xls", "xlsx"]
)

# 2. 輸入 MAC 值
mac = st.text_input("2. 請輸入 MAC 值")
# 3. 輸入搜尋日期 (YYYYMMDD)
date_str = st.text_input("3. 請輸入搜尋日期 (格式: YYYYMMDD)")

# 當三項皆有值時開始比對
if pay_file and mac and date_str:
    if not pay_file.name.startswith("PayDetailRpt"):
        st.warning("對帳檔名需以 'PayDetailRpt' 開頭，請確認後再上傳。")

    with st.spinner("撈取 log 檔並處理中..."):
        # 取得對帳授權碼
        auth_codes = extract_auth_codes_from_paydetail(pay_file)

        # 組 URL 並下載 log
        url = f"http://54.213.216.234/sync/{mac}/sqlite/EDC_log/{date_str}_ui.txt"
        try:
            res = requests.get(url, timeout=10)
            res.raise_for_status()
            log_content = res.text
        except Exception as e:
            st.error(f"無法取得 log 檔: {e}")
            st.stop()

        # 擷取 Approval ID
        approval_ids = extract_approval_ids_from_text(log_content)

        # 比對
        unmatched = sorted(set(auth_codes) - set(approval_ids))

        st.subheader("比對結果：對帳檔中未出現在 log 檔的授權碼")
        st.write(f"共 {len(unmatched)} 筆未配對授權碼")
        st.dataframe(pd.DataFrame(unmatched, columns=["未配對的授權碼"]))

