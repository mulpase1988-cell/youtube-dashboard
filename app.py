import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import json

# ===== 숫자 포맷 함수 =====
def format_korean_number(num):
    """숫자를 한국식 단위로 변환 (150만, 1.5억 등)"""
    if pd.isna(num) or num == 0:
        return '-'
    
    num = int(num)
    
    if num >= 100000000:  # 1억 이상
        return f"{num/100000000:.1f}억"
    elif num >= 10000:  # 1만 이상
        return f"{num/10000:.0f}만"
    else:
        return f"{num:,}"

# ===== 구글 시트 연결 설정 =====
SHEET_NAME = '유튜브보물창고_테스트'

@st.cache_data(ttl=600)
def load_data():
    """구글 시트에서 데이터 로드"""
    try:
        service_account_info = dict(st.secrets["gcp_service_account"])
        
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            service_account_info, scope
        )
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).sheet1
        data = sheet.get_all_values()
        
        if len(data) < 2:
            st.error("시트에 데이터가 없습니다.")
            return pd.DataFrame()
        
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
        return pd.DataFrame()

# ===== 페이지 설정 =====
st.set_page_config(
    page_title="🎬 YouTube 보물창고",
    page_icon="🎬",
    layout="wide"
)

# ===== 커스텀 CSS =====
st.markdown("""
<style>
    /* 메트릭 카드 스타일 */
    [data-testid="stMetricValue"] {
        font-size: 32px;
        font-weight: bold;
        color: #1f77b4;
    }
    
    /* 버튼 스타일 - 크고 이쁘게 */
    .stButton > button {
        width: 100%;
        height: 70px;
        font-size: 20px;
        font-weight: bold;
        border-radius: 12px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
        box-shadow: 0 6px 20px rgba(118, 75, 162, 0.6);
        transform: translateY(-2px);
    }
    
    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 10px 20px;
        font-size: 16px;
        font-weight: bold;
        border-radius: 10px 10px 0 0;
        background-color: #f0f2f6;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #667eea;
        color: white;
    }
    
    /* 테이블 헤더 */
    thead tr th {
        background-color: #667eea !important;
        color: white !important;
        font-weight: bold;
        text-align: center;
    }
    
    /* 순서 조정 버튼 스타일 */
    .order-button {
        padding: 5px 10px;
        margin: 2px;
        border-radius: 5px;
        border: 1px solid #ddd;
        background: white;
        cursor: pointer;
    }
</style>
""", unsafe_allow_html=True)

# ===== 세션 상태 초기화 =====
if '분류1_순서' not in st.session_state:
    st.session_state.분류1_순서 = []

if '분류2_순서' not in st.session_state:
    st.session_state.분류2_순서 = {}

# ===== 타이틀 =====
col1, col2, col3 = st.columns([4, 1, 1])
with col1:
    st.title("🎬 YouTube 보물창고")
with col2:
    if st.button("🔄 새로고침", key="refresh_main"):
        st.cache_data.clear()
        st.rerun()
with col3:
    st.metric("업데이트", datetime.now().strftime("%H:%M"))

st.markdown("---")

# ===== 데이터 로드 =====
with st.spinner('📊 구글 시트에서 데이터 로딩 중...'):
    df = load_data()

if df.empty:
    st.warning("⚠️ 데이터를 불러올 수 없습니다.")
    st.stop()

st.success(f"✅ {len(df)}개 채널 데이터 로드 완료!")

# ===== 분류1/분류2 순서 초기화 =====
분류1_list_original = sorted(df['분류1'].dropna().unique().tolist())

if not st.session_state.분류1_순서:
    st.session_state.분류1_순서 = 분류1_list_original.copy()

# 새로운 분류1이 추가되었을 경우
for cat in 분류1_list_original:
    if cat not in st.session_state.분류1_순서:
        st.session_state.분류1_순서.append(cat)

# ===== 사이드바: 순서 조정 =====
with st.sidebar:
    st.header("⚙️ 설정")
    
    st.subheader("📂 분류1 순서 조정")
    
    # 분류1 순서 조정
    for idx, 분류1 in enumerate(st.session_state.분류1_순서):
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.write(f"{idx+1}. {분류1}")
        
        with col2:
            if idx > 0:
                if st.button("⬆️", key=f"up_{분류1}"):
                    st.session_state.분류1_순서[idx], st.session_state.분류1_순서[idx-1] = \
                        st.session_state.분류1_순서[idx-1], st.session_state.분류1_순서[idx]
                    st.rerun()
        
        with col3:
            if idx < len(st.session_state.분류1_순서) - 1:
                if st.button("⬇️", key=f"down_{분류1}"):
                    st.session_state.분류1_순서[idx], st.session_state.분류1_순서[idx+1] = \
                        st.session_state.분류1_순서[idx+1], st.session_state.분류1_순서[idx]
                    st.rerun()
    
    st.divider()
    
    st.subheader("📁 분류2 순서 조정")
    
    selected_cat1_for_cat2 = st.selectbox(
        "분류1 선택",
        st.session_state.분류1_순서,
        key="cat1_for_cat2_order"
    )
    
    if selected_cat1_for_cat2:
        분류2_list_original = sorted(
            df[df['분류1'] == selected_cat1_for_cat2]['분류2'].dropna().unique().tolist()
        )
        
        # 세션 상태 초기화
        if selected_cat1_for_cat2 not in st.session_state.분류2_순서:
            st.session_state.분류2_순서[selected_cat1_for_cat2] = 분류2_list_original.copy()
        
        # 새로운 분류2 추가
        for cat2 in 분류2_list_original:
            if cat2 not in st.session_state.분류2_순서[selected_cat1_for_cat2]:
                st.session_state.분류2_순서[selected_cat1_for_cat2].append(cat2)
        
        # 분류2 순서 조정
        for idx, 분류2 in enumerate(st.session_state.분류2_순서[selected_cat1_for_cat2]):
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.write(f"{idx+1}. {분류2}")
            
            with col2:
                if idx > 0:
                    if st.button("⬆️", key=f"up2_{selected_cat1_for_cat2}_{분류2}"):
                        current_list = st.session_state.분류2_순서[selected_cat1_for_cat2]
                        current_list[idx], current_list[idx-1] = current_list[idx-1], current_list[idx]
                        st.rerun()
            
            with col3:
                if idx < len(st.session_state.분류2_순서[selected_cat1_for_cat2]) - 1:
                    if st.button("⬇️", key=f"down2_{selected_cat1_for_cat2}_{분류2}"):
                        current_list = st.session_state.분류2_순서[selected_cat1_for_cat2]
                        current_list[idx], current_list[idx+1] = current_list[idx+1], current_list[idx]
                        st.rerun()
    
    st.divider()
    
    if st.button("🔄 순서 초기화"):
        st.session_state.분류1_순서 = 분류1_list_original.copy()
        st.session_state.분류2_순서 = {}
        st.rerun()

# ===== 메인 탭 구조 =====
분류1_list = st.session_state.분류1_순서

if len(분류1_list) == 0:
    st.warning("⚠️ 분류1 데이터가 없습니다.")
    st.stop()

# 탭 생성: 전체 + 각 분류1
tab_names = ["📊 전체 온서블"] + 분류1_list
tabs = st.tabs(tab_names)

# ===== 탭 0: 전체 온서블 뷰 =====
with tabs[0]:
    st.header("📊 전체 온서블 조회")
    
    # 전체 통계
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📌 총 채널 수", f"{len(df)}개")
    
    with col2:
        total_subscribers = df['구독자'].sum()
        st.metric("👥 총 구독자", format_korean_number(total_subscribers))
    
    with col3:
        total_views = df['조회수'].sum()
        st.metric("👀 총 조회수", format_korean_number(total_views))
    
    with col4:
        total_recent30 = df['최근 30개 토탈'].sum()
        st.metric("🎬 총 최근30개", format_korean_number(total_recent30))
    
    st.divider()
    
    # 분류1별 통계 테이블
    st.subheader("📋 분류1별 통계")
    
    # 사용자 지정 순서로 정렬
    stats_list = []
    for cat1 in 분류1_list:
        cat1_df = df[df['분류1'] == cat1]
        if len(cat1_df) > 0:
            stats_list.append({
                '분류1': cat1,
                '채널 수': len(cat1_df),
                '총 구독자': cat1_df['구독자'].sum(),
                '평균 구독자': cat1_df['구독자'].mean(),
                '총 조회수': cat1_df['조회수'].sum(),
                '평균 조회수': cat1_df['조회수'].mean(),
                '총 최근30개': cat1_df['최근 30개 토탈'].sum(),
                '평균 최근30개': cat1_df['최근 30개 토탈'].mean()
            })
    
    stats_by_category = pd.DataFrame(stats_list)
    
    # 포맷 적용
    display_stats = stats_by_category.copy()
    for col in ['총 구독자', '평균 구독자', '총 조회수', '평균 조회수', '총 최근30개', '평균 최근30개']:
        if col in display_stats.columns:
            display_stats[col] = display_stats[col].apply(format_korean_number)
    
    st.dataframe(display_stats, use_container_width=True, hide_index=True)
    
    st.divider()
    
    # 전체 채널 리스트
    st.subheader("📋 전체 채널 리스트")
    
    # 정렬 옵션
    col1, col2, col3 = st.columns([2, 2, 4])
    
    with col1:
        sort_column_all = st.selectbox(
            "📊 정렬 기준",
            ['최근 30개 토탈', '최근 20개 토탈', '최근 10개 토탈', 
             '최근 5개 토탈', '구독자', '조회수'],
            key="sort_all"
        )
    
    with col2:
        sort_order_all = st.radio(
            "정렬 순서",
            ['내림차순 ↓', '올림차순 ↑'],
            horizontal=True,
            key="order_all"
        )
    
    with col3:
        search_query_all = st.text_input(
            "🔍 채널명 검색",
            placeholder="채널명을 입력하세요...",
            key="search_all"
        )
    
    # 검색 필터
    display_df_all = df.copy()
    if search_query_all:
        display_df_all = display_df_all[
            display_df_all['채널명'].astype(str).str.contains(search_query_all, case=False, na=False)
        ]
    
    # 정렬 (2차 정렬: 채널명)
    ascending_all = (sort_order_all == '올림차순 ↑')
    display_df_all = display_df_all.sort_values(
        by=[sort_column_all, '채널명'],
        ascending=[ascending_all, True]
    )
    
    # 표시할 컬럼 (분류2 추가!)
    display_columns_all = [
        '채널명', 'URL', '분류1', '국가', '분류2', '구독자', '동영상', '조회수',
        '최근 5개 토탈', '최근 10개 토탈', '최근 20개 토탈', '최근 30개 토탈'
    ]
    
    available_columns_all = [col for col in display_columns_all if col in display_df_all.columns]
    
    # 한국식 숫자 포맷 적용
    display_df_formatted = display_df_all[available_columns_all].copy()
    for col in ['구독자', '동영상', '조회수', '최근 5개 토탈', '최근 10개 토탈', '최근 20개 토탈', '최근 30개 토탈']:
        if col in display_df_formatted.columns:
            display_df_formatted[col] = display_df_formatted[col].apply(format_korean_number)
    
    st.dataframe(display_df_formatted, use_container_width=True, height=600, hide_index=True)
    
    # CSV 다운로드
    csv = display_df_all[available_columns_all].to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 전체 데이터 CSV 다운로드",
        data=csv,
        file_name=f"youtube_all_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

# ===== 탭 1~N: 각 분류1별 상세 =====
for idx, 분류1 in enumerate(분류1_list):
    with tabs[idx + 1]:
        filtered_df = df[df['분류1'] == 분류1].copy()
        
        st.header(f"📂 {분류1}")
        
        # 분류2 리스트 (사용자 지정 순서 적용)
        if 분류1 in st.session_state.분류2_순서:
            분류2_list = ['전체'] + st.session_state.분류2_순서[분류1]
        else:
            분류2_list = ['전체'] + sorted(filtered_df['분류2'].dropna().unique().tolist())
        
        selected_분류2 = st.radio(
            "📁 분류2 선택",
            분류2_list,
            horizontal=True,
            key=f"radio_{분류1}"
        )
        
        if selected_분류2 != '전체':
            display_df = filtered_df[filtered_df['분류2'] == selected_분류2].copy()
        else:
            display_df = filtered_df.copy()
        
        st.divider()
        
        # 통계 카드
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📊 채널 수", f"{len(display_df)}개")
        
        with col2:
            avg_subscribers = display_df['구독자'].mean()
            st.metric("👥 평균 구독자", format_korean_number(avg_subscribers))
        
        with col3:
            avg_views = display_df['조회수'].mean()
            st.metric("👀 평균 조회수", format_korean_number(avg_views))
        
        with col4:
            avg_recent30 = display_df['최근 30개 토탈'].mean()
            st.metric("🎬 평균 최근30개", format_korean_number(avg_recent30))
        
        st.divider()
        
        # 정렬 및 검색
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
        
        # 정렬 (2차 정렬: 채널명)
        ascending = (sort_order == '올림차순 ↑')
        display_df = display_df.sort_values(
            by=[sort_column, '채널명'],
            ascending=[ascending, True]
        )
        
        # 리스트 테이블
        st.subheader(f"📋 채널 리스트 ({len(display_df)}개)")
        
        # 표시할 컬럼 (분류2 추가! 국가 뒤)
        display_columns = [
            '채널명', 'URL', '국가', '분류2', '구독자', '동영상', '조회수',
            '운영기간', '최초업로드', '최근업로드',
            '최근 5개 토탈', '최근 10개 토탈', '최근 20개 토탈', '최근 30개 토탈'
        ]
        
        available_columns = [col for col in display_columns if col in display_df.columns]
        
        if len(display_df) > 0:
            # 한국식 숫자 포맷 적용
            display_df_formatted = display_df[available_columns].copy()
            for col in ['구독자', '동영상', '조회수', '최근 5개 토탈', '최근 10개 토탈', '최근 20개 토탈', '최근 30개 토탈']:
                if col in display_df_formatted.columns:
                    display_df_formatted[col] = display_df_formatted[col].apply(format_korean_number)
            
            st.dataframe(display_df_formatted, use_container_width=True, height=600, hide_index=True)
            
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
    st.caption("💾 데이터 소스: Google Sheets (10분마다 자동 새로고침)")
