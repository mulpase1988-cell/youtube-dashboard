import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from streamlit_sortables import sort_items

# --- [1] 페이지 기본 설정 ---
st.set_page_config(
    page_title="YouTube 보물창고",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- [2] 디자인 커스텀 CSS (이미지 요청 반영) ---
st.markdown("""
<style>
    /* 전체 앱 배경 및 폰트 */
    .stApp { counter-reset: rank-counter; }
    
    /* 드래그 항목 컨테이너 레이아웃 */
    .sortable-item {
        display: flex !important;
        align-items: center !important;
        margin-bottom: 12px !important;
        background: transparent !important;
        border: none !important;
    }

    /* [왼쪽 번호 영역] 고정된 엑셀 셀 디자인 */
    .sortable-item::before {
        counter-increment: rank-counter;
        content: counter(rank-counter);
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 55px !important;
        height: 45px !important;
        background-color: #ffffff !important;
        color: #333 !important;
        font-weight: bold !important;
        border: 1px solid #d1d3d4 !important;
        margin-right: -1px !important;
        flex-shrink: 0 !important;
    }

    /* [오른쪽 버튼 영역] 빨간색 라운드 버튼 */
    .sortable-item > div:last-child {
        background-color: #ff4b4b !important;
        color: white !important;
        border-radius: 0 8px 8px 0 !important;
        padding: 0 20px !important;
        height: 45px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        width: 100% !important;
        font-weight: 600 !important;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1) !important;
        cursor: grab !important;
    }

    /* 대시보드 메트릭 카드 */
    .metric-card {
        background: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #ff4b4b;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

# --- [3] 데이터 로드 및 전처리 (기존 로직 유지) ---
@st.cache_data(ttl=600)
def load_data():
    # 1. 시트 연결 시도
    if "gcp_service_account" in st.secrets:
        try:
            credentials_dict = dict(st.secrets["gcp_service_account"])
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
            client = gspread.authorize(creds)
            sheet = client.open("유튜브보물창고_테스트").sheet1
            df = pd.DataFrame(sheet.get_all_records())
            
            # [숫자 변환 로직] 콤마 제거 및 정수형 변환
            numeric_cols = ['구독자', '조회수', '최근 30개 토탈', '동영상']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0).astype(int)
            return df
        except Exception as e:
            st.warning(f"시트 연결 중 오류 발생: {e}")
    
    # 2. 연결 실패 시 샘플 데이터 (기존 로직 유지)
    return pd.DataFrame({
        "채널명": ["샘플 채널 A", "샘플 채널 B", "샘플 채널 C"],
        "분류1": ["연예인", "예능", "cctv"],
        "구독자": [100000, 50000, 30000],
        "조회수": [1000000, 500000, 300000],
        "최근 30개 토탈": [50000, 20000, 10000]
    })

# --- [4] 대시보드 페이지 ---
def show_dashboard():
    st.title("📊 대시보드")
    df = load_data()
    
    # 저장된 순서가 있으면 적용, 없으면 기본값
    cat1_list = st.session_state.get('분류1_순서', sorted(df['분류1'].unique().tolist()))
    selected_cat = st.selectbox("분류 선택", cat1_list)
    
    df_filtered = df[df['분류1'] == selected_cat]
    
    # 지표 카드 레이아웃
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f"<div class='metric-card'><h3>{len(df_filtered)}</h3><p>채널 수</p></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='metric-card'><h3>{df_filtered['구독자'].sum():,}</h3><p>총 구독자</p></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='metric-card'><h3>{df_filtered['조회수'].sum():,}</h3><p>총 조회수</p></div>", unsafe_allow_html=True)
    
    st.divider()
    st.dataframe(df_filtered, use_container_width=True)

# --- [5] 순서 설정 페이지 (요청 디자인 적용) ---
def show_settings():
    st.title("⚙️ 순서 설정")
    df = load_data()
    
    if '분류1_순서' not in st.session_state:
        st.session_state['분류1_순서'] = sorted(df['분류1'].unique().tolist())

    st.info("💡 카드를 드래그하여 순서를 변경하세요. 왼쪽의 번호는 고정됩니다.")

    # 드래그 앤 드롭 기능
    current_list = st.session_state['분류1_순서']
    sorted_list = sort_items(current_list, direction='vertical', key='main_sorter')

    if sorted_list != current_list:
        st.session_state['분류1_순서'] = sorted_list
        st.rerun()

    if st.button("💾 순서 저장 (세션 임시 저장)", type="primary"):
        st.success("순서가 현재 세션에 반영되었습니다. 대시보드에서 확인하세요!")

# --- [6] 메인 네비게이션 ---
def main():
    if 'page' not in st.session_state:
        st.session_state.page = "dashboard"

    # 상단 내비게이션 바
    nav_col1, nav_col2 = st.columns([8, 2])
    with nav_col2:
        label = "🏠 대시보드" if st.session_state.page == "settings" else "⚙️ 순서 설정"
        if st.button(label):
            st.session_state.page = "settings" if st.session_state.page == "dashboard" else "dashboard"
            st.rerun()

    if st.session_state.page == "dashboard":
        show_dashboard()
    else:
        show_settings()

if __name__ == "__main__":
    main()
