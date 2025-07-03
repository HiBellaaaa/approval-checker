import streamlit as st
import pandas as pd
import re
import requests

# 擷取 log 內容中的 Approval ID
@st.cache_data
def extract_approval_ids_from_text(content: str):
    return re.findall(r'Approval ID[:：]\s*([A-Z0-9]+)', content)

# 擷取對帳檔中的授權碼 (支援多標題與關鍵字匹配)
@st.cache_data
def extract_auth_codes_from_paydetail(file):
    try:
        df = pd.read_excel(file, header=0)
    except Exception:
        st.error("無法讀取 Excel 檔，請確認格式為 .xls 或 .xlsx。")
        return []
    # 部分字串匹配欄位名
    for col in df.columns:
        name = str(col)
        if any(keyword in name for keyword in ["授權", "授权", "Auth"]):
            return df[col].dropna().astype(str).str.strip().tolist()
    # 若標準 header 不行，掃描前 5 列
    df_raw = pd.read_excel(file, header=None)
    header_row = header_col = None
    for i in range(min(5, len(df_raw))):
        for j, cell in enumerate(df_raw.iloc[i].tolist()):
            if any(keyword in str(cell) for keyword in ["授權", "授权", "Auth"]):
                header_row, header_col = i, j
                break
        if header_row is not None:
            break
    if header_row is None:
        st.error("未找到授權碼欄位，請確認表格包含對應文字。")
        return []
    return df_raw.iloc[header_row+1:, header_col].dropna().astype(str).str.strip().tolist()

st.title("Approval ID 比對工具 (附 Log 檔除錯) ")

# 1. 上傳對帳檔 (Excel)
pay_file = st.file_uploader(
    "1. 上傳對帳檔 (檔名前綴：PayDetailRpt，Excel .xls/.xlsx)",
    type=["xls", "xlsx"]
)
# 2. 輸入 MAC 值
mac = st.text_input("2. 輸入 MAC 值")
# 3. 輸入搜尋日期 (YYYYMMDD)
date_str = st.text_input("3. 輸入搜尋日期 (格式 YYYYMMDD)")

if pay_file and mac and date_str:
    if not pay_file.name.startswith("PayDetailRpt"):
        st.warning("檔名須以 'PayDetailRpt' 開頭。")

    with st.spinner("撈取 log 檔並處理中..."):
        # 取得授權碼列表
        auth_codes = extract_auth_codes_from_paydetail(pay_file)
        # 下載 log 檔內容
        url = f"http://54.213.216.234/sync/{mac}/sqlite/EDC_log/{date_str}_ui.txt"
        try:
            res = requests.get(url, timeout=10)
            res.raise_for_status()
            log_content = res.text
        except Exception as e:
            st.error(f"無法取得 log 檔: {e}")
            st.stop()

        # 顯示並提供下載 log 檔
        st.subheader("Log 檔原始內容預覽")
        st.text_area("Log content", log_content, height=300)
        st.download_button(
            label="下載 Log 檔",
            data=log_content,
            file_name=f"{date_str}_ui.txt",
            mime="text/plain"
        )

        # 取得 Approval IDs 並比對
        approval_ids = extract_approval_ids_from_text(log_content)
        set_auth = set(auth_codes)
        set_approval = set(approval_ids)
        unmatched_auth = sorted(set_auth - set_approval)

        # 顯示結果
        st.subheader("比對結果：對帳檔中未出現在 log 檔的授權碼")
        st.write(f"共 {len(unmatched_auth)} 筆未配對授權碼")
        st.dataframe(pd.DataFrame(unmatched_auth, columns=["未配對的授權碼"]))

        # 顯示除錯統計資訊
        st.subheader("比對統計資訊")
        st.write(f"對帳 Excel 授權碼數量（總/去重）：{len(auth_codes)}/{len(set_auth)}")
        st.write(f"Log Approval ID 數量（總/去重）：{len(approval_ids)}/{len(set_approval)}")
        st.write(f"交集數量：{len(set_auth & set_approval)}")
