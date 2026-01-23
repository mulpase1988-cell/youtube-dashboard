import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import json

# ===== 구글 시트 연결 설정 =====
SHEET_NAME = '유튜브보물창고_테스트'

@st.cache_data(ttl=600)  # 10분마다 데이터 새로고침
def load_data():
    """구글 시트에서 데이터 로드"""
    try:
        # Streamlit Cloud의 secrets에서 service account 정보 가져오기
        service_account_info = dict(st.secrets["gcp_service_account"])
        
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Service Account로 인증
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            service_account_info, scope
        )
        client = gspread.authorize(creds)
        
        # 시트 열기
        sheet = client.open(SHEET_NAME).sheet1
        
        # 모든 데이터 가져오기
        data = sheet.get_all_values()
        
        if len(data) < 2:
            st.error("시트에 데이터가 없습니다.")
            return pd.DataFrame()
        
        # DataFrame 생성
        df = pd.DataFrame(data[1:], columns=data[0])
        
        # 숫자 컬럼 변환
        numeric_cols = ['구독자', '동영상', '조회수', 
                        '최근 5개 토탈', '최근 10개 토탈', 
                        '최근 20개 토탈', '최근 30개 토탈']
        
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.replace(',', ''), 
                    errors='coerce'
                ).fillna(0)
        
        return df
        
    except Exception as e:
        st.error(f"데이터 로드 실패: {str(e)}")
        st.info("💡 Secrets 설정을 확인해주세요!")
        return pd.DataFrame()

# ===== 페이지 설정 =====
st.set_page_config(
    page_title="🎬 YouTube 보물창고",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== 타이틀 =====
st.title("🎬 YouTube 보물창고 대시보드")
st.caption("실시간 구글 시트 연동 | 10분마다 자동 새로고침")

# ===== 데이터 로드 =====
with st.spinner('📊 구글 시트에서 데이터 로딩 중...'):
    df = load_data()

if df.empty:
    st.warning("⚠️ 데이터를 불러올 수 없습니다.")
    st.info("""
    **확인 사항:**
    1. Streamlit Cloud Secrets에 service account 정보가 있나요?
    2. Service account 이메일이 구글 시트에 공유되어 있나요?
    3. 시트 이름이 '유튜브보물창고_테스트'가 맞나요?
    """)
    st.stop()

# ===== 데이터 로드 성공 알림 =====
st.success(f"✅ {len(df)}개 채널 데이터 로드 완료!")

# ===== 수동 새로고침 버튼 =====
col1, col2, col3 = st.columns([1, 1, 4])
with col1:
    if st.button("🔄 데이터 새로고침"):
        st.cache_data.clear()
        st.rerun()
with col2:
    st.metric("마지막 업데이트", datetime.now().strftime("%H:%M:%S"))

st.divider()

# ===== 분류1 탭 구조 =====
분류1_list = sorted(df['분류1'].dropna().unique().tolist())

if len(분류1_list) == 0:
    st.warning("⚠️ 분류1 데이터가 없습니다.")
    st.stop()

# 탭 생성
tabs = st.tabs(분류1_list)

for idx, 분류1 in enumerate(분류1_list):
    with tabs[idx]:
        # 해당 분류1 데이터 필터링
        filtered_df = df[df['분류1'] == 분류1].copy()
        
        st.subheader(f"📂 {분류1} 카테고리")
        
        # ===== 분류2 필터 =====
        분류2_list = ['전체'] + sorted(filtered_df['분류2'].dropna().unique().tolist())
        
        selected_분류2 = st.radio(
            "📁 분류2 선택",
            분류2_list,
            horizontal=True,
            key=f"radio_{분류1}"
        )
        
        # 분류2 필터 적용
        if selected_분류2 != '전체':
            display_df = filtered_df[filtered_df['분류2'] == selected_분류2].copy()
        else:
            display_df = filtered_df.copy()
        
        st.divider()
        
        # ===== 통계 카드 =====
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📊 채널 수", f"{len(display_df):,}개")
        
        with col2:
            avg_subscribers = display_df['구독자'].mean()
            st.metric("👥 평균 구독자", f"{avg_subscribers:,.0f}")
        
        with col3:
            avg_views = display_df['조회수'].mean()
            st.metric("👀 평균 조회수", f"{avg_views:,.0f}")
        
        with col4:
            avg_recent30 = display_df['최근 30개 토탈'].mean()
            st.metric("🎬 평균 최근30개", f"{avg_recent30:,.0f}")
        
        st.divider()
        
        # ===== 정렬 및 검색 =====
        col1, col2, col3 = st.columns([2, 2, 4])
        
        with col1:
            sort_column = st.selectbox(
                "📊 정렬 기준",
                ['최근 30개 토탈', '최근 20개 토탈', '최근 10개 토탈', 
                 '최근 5개 토탈', '구독자', '조회수'],
                key=f"sort_{분류1}_{selected_분류2}"
            )
        
        with col2:
            sort_order = st.radio(
                "정렬 순서",
                ['내림차순 ↓', '올림차순 ↑'],
                horizontal=True,
                key=f"order_{분류1}_{selected_분류2}"
            )
        
        with col3:
            search_query = st.text_input(
                "🔍 채널명 검색",
                placeholder="채널명을 입력하세요...",
                key=f"search_{분류1}_{selected_분류2}"
            )
        
        # 검색 필터
        if search_query:
            display_df = display_df[
                display_df['채널명'].astype(str).str.contains(search_query, case=False, na=False)
            ]
        
        # 정렬
        ascending = (sort_order == '올림차순 ↑')
        display_df = display_df.sort_values(sort_column, ascending=ascending)
        
        # ===== 리스트 테이블 =====
        st.subheader(f"📋 채널 리스트 ({len(display_df)}개)")
        
        # 표시할 컬럼
        display_columns = [
            '채널명', 'URL', '국가', '구독자', '동영상', '조회수',
            '운영기간', '최초업로드', '최근업로드',
            '최근 5개 토탈', '최근 10개 토탈', '최근 20개 토탈', '최근 30개 토탈'
        ]
        
        # 존재하는 컬럼만 선택
        available_columns = [col for col in display_columns if col in display_df.columns]
        
        if len(display_df) > 0:
            # 데이터프레임 표시
            st.dataframe(
                display_df[available_columns].style.format({
                    '구독자': '{:,.0f}',
                    '동영상': '{:,.0f}',
                    '조회수': '{:,.0f}',
                    '최근 5개 토탈': '{:,.0f}',
                    '최근 10개 토탈': '{:,.0f}',
                    '최근 20개 토탈': '{:,.0f}',
                    '최근 30개 토탈': '{:,.0f}'
                }, na_rep='-'),
                use_container_width=True,
                height=600
            )
            
            # CSV 다운로드
            csv = display_df[available_columns].to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label=f"📥 CSV 다운로드 ({분류1} - {selected_분류2})",
                data=csv,
                file_name=f"youtube_{분류1}_{selected_분류2}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                key=f"download_{분류1}_{selected_분류2}"
            )
        else:
            st.info("검색 결과가 없습니다.")

# ===== 푸터 =====
st.divider()
col1, col2 = st.columns(2)
with col1:
    st.caption(f"📅 마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
with col2:
    st.caption("💾 데이터 소스: Google Sheets (실시간 연동)")
