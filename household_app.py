import streamlit as st
import pandas as pd
from datetime import datetime
import re
import requests

# 알려주신 노션 시크릿 키와 데이터베이스 ID
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
def save_to_notion(date, recorder, type_choice, category, detail, amount, payment):
    url = "https://api.notion.com/v1/pages"
    
    data = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "상세내역": {"title": [{"text": {"content": detail}}]},
            "날짜": {"date": {"start": str(date)}},
            "기록자": {"select": {"name": recorder}},
            "구분": {"select": {"name": type_choice}},
            "대분류": {"select": {"name": category}},
            "금액": {"number": amount},
            "결제수단": {"select": {"name": payment}}
        }
    }
    response = requests.post(url, headers=HEADERS, json=data)
    return response.status_code == 200, response.text

# 빠른 입력 파싱 함수
def parse_quick_input(text, recorder):
    match = re.search(r'(.*?)\s*([0-9,]+)\s*(원)?', text)
    if not match: return None, "입력 형식을 확인해주세요. (예: 이마트 10000)"
    
    detail = match.group(1).strip()
    amount = int(match.group(2).replace(',', ''))
    
    category_mapping = {
        "식비": ["마트", "이마트", "홈플러스", "편의점", "식당", "카페", "커피", "배달", "치킨", "피자", "식비", "회식"],
        "교통/차량": ["택시", "버스", "지하철", "주유", "기차", "주차", "대리", "교통"],
        "자녀/육아": ["학원", "장난감", "기저귀", "분유", "학교", "문제집", "첫째", "둘째", "막내", "소아과"],
        "생활용품": ["다이소", "올리브영", "세제", "휴지", "물티슈", "쿠팡"],
        "고정비(주거/통신/보험)": ["관리비", "통신비", "가스비", "전기세", "보험"],
        "의료/건강": ["병원", "약국", "한의원", "치과"],
        "여가/문화": ["영화", "게임", "책", "여행", "넷플릭스"]
    }
    
    matched_category = "기타 지출"
    for cat, keywords in category_mapping.items():
        if any(kw in detail for kw in keywords):
            matched_category = cat; break
            
    if matched_category == "기타 지출" and detail != "": matched_category = "식비"
            
    return {
        "날짜": datetime.now().date(), "기록자": recorder, "구분": "지출",
        "대분류": matched_category, "상세내역": detail, "금액": amount, "결제수단": "신용카드"
    }, "성공"

# ----------------------------------------------------
st.title("🏡 부부 공동 가계부 (Notion 연동)")
st.markdown("---")

ledger_df = load_data_from_notion()

# 사이드바
st.sidebar.header("⚡ 빠른 입력 (채팅 스타일)")
quick_recorder = st.sidebar.radio("기록자 선택", ["남편", "아내"], horizontal=True)

if "quick_text" not in st.session_state: st.session_state.quick_text = ""

def submit_quick_input():
    user_text = st.session_state.quick_text
    if user_text:
        parsed_data, msg = parse_quick_input(user_text, quick_recorder)
        if parsed_data:
            success, error_msg = save_to_notion(
                parsed_data["날짜"], parsed_data["기록자"], parsed_data["구분"],
                parsed_data["대분류"], parsed_data["상세내역"], parsed_data["금액"], parsed_data["결제수단"]
            )
            if success:
                st.session_state.quick_text = "" 
                st.toast(f"✅ 노션 저장 완료! ({parsed_data['상세내역']} {parsed_data['금액']:,}원)")
                st.cache_data.clear() # 데이터 새로고침
            else:
                st.sidebar.error(f"저장 실패! 상세 에러 내용: {error_msg}")
        else:
            st.sidebar.error(msg)

st.sidebar.text_input("내역 금액 (예: 이마트 50000)", key="quick_text", on_change=submit_quick_input)

# 메인 화면
if not ledger_df.empty:
    ledger_df['년월'] = pd.to_datetime(ledger_df['날짜']).dt.to_period('M')
    selected_month = st.selectbox("조회할 월", sorted(ledger_df['년월'].unique().astype(str), reverse=True))
    
    df_month = ledger_df[ledger_df['년월'].astype(str) == selected_month]
    
    col1, col2, col3 = st.columns(3)
    t_income = df_month[df_month['구분']=="수입"]['금액'].sum()
    t_expense = df_month[df_month['구분']=="지출"]['금액'].sum()
    col1.metric("총 수입", f"{t_income:,.0f} 원")
    col2.metric("총 지출", f"- {t_expense:,.0f} 원")
    col3.metric("이번 달 잔액", f"{t_income - t_expense:,.0f} 원")
    
    st.markdown("---")
    st.subheader("📅 노션 실시간 데이터")
    st.dataframe(df_month.drop(columns=['년월']), width="stretch")
else:
    st.info("노션에 아직 데이터가 없습니다. 왼쪽에서 첫 지출을 입력해 보세요!")