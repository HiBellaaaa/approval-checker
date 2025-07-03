import streamlit as st
import pandas as pd
import re
import requests
from datetime import datetime, time as dtime

# 擷取 log 內容中的 Approval ID，並過濾時間
@st.cache_data
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

# 擷取對帳檔中的授權碼，並過濾交易日
@st.cache_data
def extract_auth_codes_from_paydetail(file, target_date: str):
    try:
        df = pd.read_excel(file, header=0)
    except Exception:
        st.error("無法讀取 Excel 檔，請確認格式為 .xls 或 .xlsx。")
        return []
    # 找到授權碼欄位與交易日欄位
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
    # 過濾交易日
    if date_col is not None:
        df = df[df[date_col].astype(str).str.contains(target_date)]
    # 擷取授權碼
    return df[auth_col].dropna().astype(str).str.strip().tolist()

st.title("授權碼比對工具")
# 小標題：針對卡機連線異常狀況
st.markdown('<span style="font-size:12pt; font-weight:bold;">針對卡機連線異常狀況</span>', unsafe_allow_html=True)

# 1. 上傳台新對帳檔 (Excel)
pay_file = st.file_uploader(
    "1. 上傳台新對帳檔 (檔名前綴：PayDetailRpt，檔案規格： .xls/.xlsx)",
    type=["xls", "xlsx"]
)
# 2. 輸入機台 MAC 值（可在販賣機後台機台資訊頁找到）
mac = st.text_input("2. 輸入機台 MAC 值（可在販賣機後台機台資訊頁找到）")
# 3. 選擇搜尋日期
date_input = st.date_input("3. 選擇搜尋日期")
# 4. 選擇每日最後結帳時間
time_input = st.time_input("4. 選擇每日最後結帳時間", value=dtime(19,0))

# 5. 送出按鈕
if st.button("送出"):
    if not pay_file or not mac or not date_input:
        st.warning("請確認已上傳對帳檔、輸入 MAC 值及選擇日期與時間後再送出。")
    elif not pay_file.name.startswith("PayDetailRpt"):
        st.warning("對帳檔名須以 'PayDetailRpt' 開頭。")
    else:
        with st.spinner("處理中..."):
            # 轉日期字串
            date_str = date_input.strftime("%Y%m%d")
            # 取得授權碼列表（過濾交易日）
            auth_codes = extract_auth_codes_from_paydetail(pay_file, date_str)
            # 下載並擷取 log Approval IDs（過濾時間）
            url = f"http://54.213.216.234/sync/{mac}/sqlite/EDC_log/{date_str}_ui.txt"
            try:
                res = requests.get(url, timeout=10)
                res.raise_for_status()
                try:
                    content = res.content.decode('utf-8')
                except UnicodeDecodeError:
                    content = res.content.decode('big5', errors='ignore')
            except Exception as e:
                st.error(f"無法取得 log 檔: {e}")
                st.stop()
            approval_ids = extract_approval_ids_from_text(content, time_input, date_str)

            # 列出各自筆數
            cnt_pay = len(auth_codes)
            cnt_log = len(approval_ids)
            st.write(f"對帳檔授權碼筆數：{cnt_pay}")
            st.write(f"Log 檔 Approval ID 筆數：{cnt_log}")

            # 若對帳檔小於 log 檔，警告
            if cnt_pay < cnt_log:
                st.error("注意：對帳檔授權碼筆數小於 log 檔 Approval ID 筆數，請確認資料完整性！")

            # 顯示未配對
            unmatched_auth = sorted(set(auth_codes) - set(approval_ids))
            st.subheader("比對結果：對帳檔中未出現在 log 檔的授權碼")
            st.write(f"共 {len(unmatched_auth)} 筆未配對的授權碼")
            st.dataframe(pd.DataFrame(unmatched_auth, columns=["未配對的授權碼"]))
