import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from streamlit_sortables import sort_items

# --- [1] 페이지 설정 ---
st.set_page_config(
    page_title="YouTube 보물창고",
    page_icon="🎬",
    layout="wide"
)

# CSS 디자인 (기존 유지)
st.markdown("""
<style>
    .stApp { counter-reset: item-rank; }
    .sortable-item {
        display: flex !important; align-items: center !important;
        margin-bottom: 8px !important; cursor: grab !important;
        counter-increment: item-rank;
    }
    .sortable-item::before {
        content: counter(item-rank);
        display: flex !important; align-items: center !important; justify-content: center !important;
        width: 45px !important; height: 40px !important;
        background-color: white !important; border: 1px solid #ccc !important;
        margin-right: 15px !important; font-weight: bold !important;
    }
    .sortable-item > div:last-child {
        background-color: #ff4b4b !important; color: white !important;
        border-radius: 8px !important; padding: 0 15px !important;
        height: 40px !important; display: flex !important; align-items: center !important;
        width: 100% !important; font-weight: 500 !important;
    }
    .metric-card {
        background: #f8f9fa; padding: 20px; border-radius: 10px;
        border-left: 5px solid #ff4b4b; text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# --- [2] 데이터 로드 로직 ---
@st.cache_data(ttl=600)
def load_data():
    if "gcp_service_account" not in st.secrets:
        # 샘플 데이터 (테스트용)
        return pd.DataFrame({
            "채널명": [f"채널 {i}" for i in range(1, 11)],
            "분류1": ["연예인", "예능", "음악", "게임", "브이로그", "뉴스", "스포츠", "IT", "영화", "요리"],
            "구독자": [100000] * 10, "조회수": [1000000] * 10
        })
    
    try:
        credentials_dict = dict(st.secrets["gcp_service_account"])
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open("유튜브보물창고_테스트").sheet1
        df = pd.DataFrame(sheet.get_all_records())
        
        # 숫자 변환
        for col in ['구독자', '조회수']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"데이터 로드 오류: {e}")
        return pd.DataFrame()

# --- [3] 페이지별 함수 ---
def show_dashboard():
    st.title("📊 대시보드")
    df = load_data()
    if df.empty: return

    # 저장된 순서 불러오기
    cat1_order = st.session_state.get('분류1_순서', sorted(df['분류1'].unique().tolist()))
    selected_cat = st.selectbox("분류 선택", cat1_order)
    
    df_filtered = df[df['분류1'] == selected_cat]
    
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='metric-card'><h3>{len(df_filtered)}</h3><p>채널 수</p></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='metric-card'><h3>{df_filtered['구독자'].sum():,}</h3><p>총 구독자</p></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='metric-card'><h3>{df_filtered['조회수'].sum():,}</h3><p>총 조회수</p></div>", unsafe_allow_html=True)
    
    st.divider()
    st.dataframe(df_filtered, use_container_width=True)

def show_settings():
    st.title("⚙️ 순서 설정")
    df = load_data()
    if df.empty: return

    # 세션 상태 초기화
    if '분류1_순서' not in st.session_state:
        st.session_state['분류1_순서'] = sorted(df['분류1'].unique().tolist())

    st.info("💡 카드를 드래그하여 순서를 변경하세요.")
    
    # 5열 그리드 구성을 위해 리스트 분할
    items = st.session_state['분류1_순서']
    # 단일 컨테이너로 먼저 테스트 (다중 컨테이너는 로직이 복잡하므로 1줄로 먼저 구현)
    sorted_items = sort_items(items, direction='vertical', key='sort_items_key')

    if sorted_items != items:
        st.session_state['분류1_순서'] = sorted_items
        st.rerun()

    if st.button("💾 순서 확정 저장", type="primary"):
        st.success("순서가 적용되었습니다. 대시보드에서 확인하세요!")

# --- [4] 메인 네비게이션 ---
def main():
    if 'page' not in st.session_state:
        st.session_state.page = "dashboard"

    # 사이드바 대신 상단 우측 버튼
    col1, col2 = st.columns([8, 2])
    with col2:
        btn_label = "🏠 대시보드" if st.session_state.page == "settings" else "⚙️ 순서 설정"
        if st.button(btn_label):
            st.session_state.page = "settings" if st.session_state.page == "dashboard" else "dashboard"
            st.rerun()

    if st.session_state.page == "dashboard":
        show_dashboard()
    else:
        show_settings()

if __name__ == "__main__":
    main()
