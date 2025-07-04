import streamlit as st
import pandas as pd
import re
import requests
from datetime import datetime, time as dtime

# 擷取 log 內容中的 Approval ID，並過濾時間
@st.cache_data
def extract_approval_ids_from_text(content: str, cutoff: dtime, target_date: str):
    ids = []
    lines = content.splitlines()
    # 將目標日期格式化為 'YYYY-MM-DD'
    date_prefix = datetime.strptime(target_date, "%Y%m%d").strftime("%Y-%m-%d")
    for idx, line in enumerate(lines):
        # 只處理當日的記錄
        if date_prefix not in line or 'Approval ID' not in line:
            continue
        # 解析時間
        tm = re.search(r'_(\d{2}):(\d{2}):(\d{2})', line)
        if not tm:
            continue
        hh, mm, ss = tm.groups()
        t = dtime(int(hh), int(mm), int(ss))
        # 忽略超過結帳時間的紀錄
        if t > cutoff:
            continue
        # 嘗試從同一行提取 Approval ID
        matches = re.findall(r'Approval ID[:：]\s*([A-Z0-9]+)', line)
        if matches:
            ids.extend(matches)
        else:
            # 若同一行沒有，則檢查下一行是否純數值
            if idx + 1 < len(lines):
                next_line = lines[idx + 1].strip()
                if re.fullmatch(r'[A-Z0-9]+', next_line):
                    ids.append(next_line)
    return ids

# 擷取對帳檔中的授權碼，並過濾交易日
@st.cache_data
def extract_auth_codes_from_paydetail(file, target_date: str):
    try:
        df = pd.read_excel(file, header=5)  # 從第6列(Row index 5)開始讀取標題
    except Exception:
        st.error("無法讀取 Excel 檔，請確認格式為 .xls 或 .xlsx。")
        return []
    auth_col = date_col = None
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
        def _normalize(val):
            if pd.isna(val):
                return ""
            if isinstance(val, datetime):
                return val.strftime('%Y%m%d')
            s = str(val).strip()
            if re.fullmatch(r'\d{6}', s):
                return '20' + s
            if re.fullmatch(r'\d{8}', s):
                return s
            try:
                return datetime.strptime(s, '%Y/%m/%d').strftime('%Y%m%d')
            except:
                return s
        df['norm_date'] = df[date_col].apply(_normalize)
        df = df[df['norm_date'] == target_date]
    return df[auth_col].dropna().astype(str).str.strip().tolist()

st.title("授權碼比對工具")
st.markdown('<span style="font-size:12pt; font-weight:bold;">針對卡機連線異常狀況（如為該日結帳後的異常交易，不適用此工具）</span>', unsafe_allow_html=True)

# 1. 上傳台新對帳檔 (Excel)
pay_file = st.file_uploader(
    "1. 上傳台新對帳檔 (檔名前綴：PayDetailRpt，檔案規格： .xls/.xlsx)", type=["xls", "xlsx"]
)
# 2. 輸入機台 MAC 值（可在販賣機後台機台資訊頁找到）
mac = st.text_input("2. 輸入機台 MAC 值（可在販賣機後台機台資訊頁找到）")
# 3. 選擇搜尋日期
date_input = st.date_input("3. 選擇搜尋日期")
# 4. 選擇每日最後結帳時間
time_input = st.time_input("4. 選擇每日最後結帳時間", value=dtime(21, 0))

# 5. 送出按鈕
if st.button("送出"):
    if not pay_file or not mac or not date_input:
        st.warning("請確認已上傳對帳檔、輸入 MAC 值及選擇日期與時間後再送出。")
    elif not pay_file.name.startswith("PayDetailRpt"):
        st.warning("對帳檔名須以 'PayDetailRpt' 開頭。")
    else:
        with st.spinner("處理中..."):
            date_str = date_input.strftime("%Y%m%d")
            # 取得對帳檔授權碼列表
            auth_codes = extract_auth_codes_from_paydetail(pay_file, date_str)
            # 下載 Log 檔
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
            # 取得 Log Approval IDs
            approval_ids = extract_approval_ids_from_text(content, time_input, date_str)
            # Debug: 若未擷取到任何 Approval ID，顯示前幾行與包含 ID 的行
            if not approval_ids:
                st.error("Log 檔 Approval ID 筆數為 0，可能日期或時間範圍不正確。")
                lines = content.splitlines()
                st.write("Log 檔前 10 行:", lines[:10])
                approval_lines = [l for l in lines if "Approval ID" in l]
                st.write("包含 'Approval ID' 的行:", approval_lines)
            # 顯示筆數
            cnt_pay = len(auth_codes)
            cnt_log = len(approval_ids)
            st.write(f"對帳檔授權碼筆數：{cnt_pay}")
            st.write(f"Log 檔 Approval ID 筆數：{cnt_log}")
            if cnt_pay < cnt_log:
                st.error("注意：對帳檔授權碼筆數小於 log 檔 Approval ID 筆數，請確認資料完整性！")
            # 未配對清單
            unmatched = sorted(set(auth_codes) - set(approval_ids))
            st.subheader("比對結果：對帳檔中未出現在 log 檔的授權碼")
            st.write(f"共 {len(unmatched)} 筆未配對的授權碼")
            st.dataframe(pd.DataFrame(unmatched, columns=["未配對的授權碼"]))
