import streamlit as st
import pandas as pd
from datetime import datetime
import re
import requests

# 알려주신 노션 시크릿 키와 데이터베이스 ID가 정확히 적용되었습니다.
NOTION_TOKEN = "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"
DATABASE_ID = "36dc06a904be80afa216e3d974743c5b"

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# ----------------------------------------------------
# 페이지 설정
st.set_page_config(page_title="우리집 행복 가계부", page_icon="💰", layout="wide")

# 노션에서 데이터 불러오기 함수
@st.cache_data(ttl=5) # 5초마다 데이터 갱신
def load_data_from_notion():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    response = requests.post(url, headers=HEADERS)
    
    columns = ["날짜", "기록자", "구분", "대분류", "상세내역", "금액", "결제수단"]
    
    if response.status_code != 200:
        return pd.DataFrame(columns=columns)
        
    results = response.json().get("results", [])
    data_list = []
    
    for row in results:
        props = row["properties"]
        try:
            detail = props["상세내역"]["title"][0]["text"]["content"] if props.get("상세내역", {}).get("title") else ""
            date = props["날짜"]["date"]["start"] if props.get("날짜", {}).get("date") else None
            recorder = props["기록자"]["select"]["name"] if props.get("기록자", {}).get("select") else ""
            type_choice = props["구분"]["select"]["name"] if props.get("구분", {}).get("select") else ""
            category = props["대분류"]["select"]["name"] if props.get("대분류", {}).get("select") else ""
            amount = props["금액"]["number"] if props.get("금액", {}).get("number") is not None else 0
            payment = props["결제수단"]["select"]["name"] if props.get("결제수단", {}).get("select") else ""
            
            data_list.append({
                "날짜": date, "기록자": recorder, "구분": type_choice,
                "대분류": category, "상세내역": detail, "금액": amount, "결제수단": payment
            })
        except Exception:
            continue
            
    df = pd.DataFrame(data_list, columns=columns)
    if not df.empty:
        df['날짜'] = pd.to_datetime(df['날짜']).dt.date
        df = df.sort_values(by="날짜", ascending=False)
    return df

# 노션에 데이터 쓰기 함수
def save_to_notion(date, recorder, type_choice, category