import streamlit as st
import pandas as pd
import os
from datetime import datetime
import re

# 페이지 설정
st.set_page_config(
    page_title="우리집 행복 가계부",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 데이터 파일 경로 설정
DATA_FILE = "household_ledger.csv"

# 데이터 로드 및 초기화 함수
def load_data():
    columns = ["날짜", "기록자", "구분", "대분류", "상세내역", "금액", "결제수단"]
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE, encoding='utf-8-sig')
            df['날짜'] = pd.to_datetime(df['날짜']).dt.date
            return df
        except Exception:
            return pd.DataFrame(columns=columns)
    else:
        return pd.DataFrame(columns=columns)

# 데이터 저장 함수
def save_data(df):
    df.to_csv(DATA_FILE, index=False, encoding='utf-8-sig')

# 빠른 입력 파싱 함수
def parse_quick_input(text, recorder):
    # 정규식: 문자(상세내역)와 숫자(금액) 분리 (예: 이마트 15000, 택시 8,000원)
    match = re.search(r'(.*?)\s*([0-9,]+)\s*(원)?', text)
    if not match:
        return None, "입력 형식을 확인해주세요. (예: 이마트 10000)"
    
    detail = match.group(1).strip()
    amount = int(match.group(2).replace(',', ''))
    
    # 키워드 기반 대분류 자동 분류 사전
    category_mapping = {
        "식비": ["마트", "이마트", "홈플러스", "편의점", "식당", "카페", "커피", "배달", "치킨", "피자", "식비", "회식"],
        "교통/차량": ["택시", "버스", "지하철", "주유", "기차", "주차", "대리", "교통"],
        "자녀/육아": ["학원", "장난감", "기저귀", "분유", "학교", "문제집", "첫째", "둘째", "막내", "소아과"],
        "생활용품": ["다이소", "올리브영", "세제", "휴지", "물티슈", "쿠팡"],
        "고정비(주거/통신/보험)": ["관리비", "통신비", "가스비", "전기세", "보험"],
        "의료/건강": ["병원", "약국", "한의원", "치과"],
        "여가/문화": ["영화", "게임", "책", "여행", "넷플릭스"]
    }
    
    # 기본값 설정
    matched_category = "기타 지출"
    for cat, keywords in category_mapping.items():
        if any(kw in detail for kw in keywords):
            matched_category = cat
            break
            
    # 키워드에 없으면 기본적으로 '식비' 또는 '기타 지출'로 배정
    if matched_category == "기타 지출" and detail != "":
         matched_category = "식비" # 가장 빈도가 높은 식비로 임시 배정
            
    return {
        "날짜": datetime.now().date(),
        "기록자": recorder,
        "구분": "지출", # 빠른 입력은 기본 지출로 처리
        "대분류": matched_category,
        "상세내역": detail,
        "금액": amount,
        "결제수단": "신용카드" # 기본값
    }, "성공"

# 초기 데이터 로드
if 'ledger_df' not in st.session_state:
    st.session_state.ledger_df = load_data()

st.title("🏡 부부 공동 가계부 대시보드")
st.markdown("---")

# ================= 사이드바 영역 =================
# 1. 빠른 입력 (채팅 스타일)
st.sidebar.header("⚡ 빠른 입력 (채팅 스타일)")
st.sidebar.markdown("단어와 숫자를 띄어쓰기로 입력하세요.<br>`예: 이마트 50000`, `택시 8000`", unsafe_allow_html=True)

quick_recorder = st.sidebar.radio("기록자 선택", ["남편", "아내"], horizontal=True)

# text_input의 value를 session_state로 관리하여 입력 후 초기화되게 함
if "quick_text" not in st.session_state:
    st.session_state.quick_text = ""

def submit_quick_input():
    user_text = st.session_state.quick_text
    if user_text:
        parsed_data, msg = parse_quick_input(user_text, quick_recorder)
        if parsed_data:
            st.session_state.ledger_df = pd.concat([st.session_state.ledger_df, pd.DataFrame([parsed_data])], ignore_index=True)
            st.session_state.ledger_df = st.session_state.ledger_df.sort_values(by="날짜", ascending=False)
            save_data(st.session_state.ledger_df)
            st.session_state.quick_text = "" # 입력창 초기화
            st.toast(f"✅ '{parsed_data['상세내역']}' {parsed_data['금액']:,}원 기록 완료! ({parsed_data['대분류']})")
        else:
            st.sidebar.error(msg)

st.sidebar.text_input("내역 금액", key="quick_text", on_change=submit_quick_input)

st.sidebar.markdown("---")

# 2. 상세 입력 (수동 선택 - 접었다 펴기)
with st.sidebar.expander("📝 상세 입력 (직접 선택하기)"):
    with st.form(key="ledger_form", clear_on_submit=True):
        date = st.date_input("날짜", datetime.now().date())
        recorder = st.selectbox("상세 기록자", ["남편", "아내"])
        type_choice = st.selectbox("구분", ["지출", "수입"])
        
        if type_choice == "지출":
            category = st.selectbox("대분류", ["식비", "생활용품", "자녀/육아", "교통/차량", "고정비(주거/통신/보험)", "여가/문화", "의료/건강", "기타 지출"])
        else:
            category = st.selectbox("대분류", ["급여", "부수입", "금융소득", "기타 수입"])
            
        detail = st.text_input("상세 내역")
        amount = st.number_input("금액 (원)", min_value=0, step=1000, value=0)
        payment = st.selectbox("결제 수단", ["신용카드", "체크카드", "계좌이체", "현금", "기타"])
        
        submit_button = st.form_submit_button(label="상세 기록하기")

    if submit_button:
        if amount > 0 and detail.strip():
            new_data = {
                "날짜": date, "기록자": recorder, "구분": type_choice,
                "대분류": category, "상세내역": detail, "금액": amount, "결제수단": payment
            }
            st.session_state.ledger_df = pd.concat([st.session_state.ledger_df, pd.DataFrame([new_data])], ignore_index=True)
            st.session_state.ledger_df = st.session_state.ledger_df.sort_values(by="날짜", ascending=False)
            save_data(st.session_state.ledger_df)
            st.rerun()

# ================= 메인 화면 영역 =================
tab1, tab2 = st.tabs(["📊 이번 달 통계 & 분석", "🔍 전체 내역 조회"])

df_current = st.session_state.ledger_df.copy()

with tab1:
    if not df_current.empty:
        df_current['년월'] = pd.to_datetime(df_current['날짜']).dt.to_period('M')
        current_month = datetime.now().strftime("%Y-%m")
        available_months = sorted(df_current['년월'].unique().astype(str), reverse=True)
        selected_month = st.selectbox("조회할 월 선택", available_months, index=0 if current_month in available_months else 0)
        
        df_month = df_current[df_current['년월'].astype(str) == selected_month]
        
        total_income = df_month[df_month['구분'] == "수입"]['금액'].sum()
        total_expense = df_month[df_month['구분'] == "지출"]['금액'].sum()
        balance = total_income - total_expense
        
        col1, col2, col3 = st.columns(3)
        col1.metric("총 수입", f"{total_income:,.0f} 원")
        col2.metric("총 지출", f"- {total_expense:,.0f} 원")
        col3.metric("이번 달 잔액", f"{balance:,.0f} 원")
        
        st.markdown("---")
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.subheader("🛒 지출 카테고리별 비율")
            df_expense = df_month[df_month['구분'] == "지출"]
            if not df_expense.empty:
                expense_by_cat = df_expense.groupby("대분류")["금액"].sum()
                st.bar_chart(expense_by_cat)
                
        with col_chart2:
            st.subheader("👤 기록자별 지출 분담")
            if not df_expense.empty:
                expense_by_user = df_expense.groupby("기록자")["금액"].sum()
                st.bar_chart(expense_by_user)
                
        st.subheader("📅 이번 달 최근 기록")
        st.dataframe(df_month.drop(columns=['년월']), use_container_width=True)
    else:
        st.info("아직 등록된 가계부 내역이 없습니다. 왼쪽 사이드바에서 첫 내역을 입력해 보세요!")

with tab2:
    if not df_current.empty:
        st.dataframe(df_current.drop(columns=['년월'] if '년월' in df_current.columns else []), use_container_width=True)
