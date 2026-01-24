import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json
from datetime import datetime
from streamlit_sortables import sort_items

# --- [설정] 페이지 설정 ---
st.set_page_config(
    page_title="YouTube 보물창고",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- [디자인] 커스텀 CSS (번호 고정 + 빨간 버튼) ---
st.markdown("""
<style>
    .stApp { counter-reset: item-rank; }
    div[data-testid="stTabContent"] { counter-reset: item-rank; }
    
    /* 드래그 아이템 전체 컨테이너 */
    .sortable-item {
        background-color: transparent !important;
        border: none !important;
        padding: 0 !important;
        margin-bottom: 8px !important;
        display: flex !important;
        align-items: center !important;
        cursor: grab !important;
        counter-increment: item-rank;
    }

    /* 왼쪽 번호 영역 (고정된 엑셀 셀 디자인) */
    .sortable-item::before {
        content: counter(item-rank);
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 45px !important;
        height: 40px !important;
        background-color: white !important;
        color: #333 !important;
        font-weight: bold !important;
        border: 1px solid #ccc !important;
        margin-right: 15px !important;
        flex-shrink: 0 !important;
    }

    /* 오른쪽 내용 영역 (빨간색 둥근 버튼) */
    .sortable-item > div:last-child {
        background-color: #ff4b4b !important;
        color: white !important;
        border-radius: 8px !important;
        padding: 0 15px !important;
        height: 40px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 100% !important;
        font-weight: 500 !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
    }

    .sortable-container-header { display: none !important; }
    
    /* 대시보드 메트릭 카드 디자인 */
    .metric-card {
        background: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #ff4b4b;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# --- [데이터] 구글 시트 연결 및 로드 (숫자 변환 포함) ---
def get_gspread_client():
    if "gcp_service_account" not in st.secrets:
        return None
    try:
        credentials_dict = dict(st.secrets["gcp_service_account"])
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
        return gspread.authorize(credentials)
    except:
        return None

@st.cache_data(ttl=600)
def load_data():
    client = get_gspread_client()
    if not client:
        # 시트 연결 실패 시 샘플 데이터 반환
        return pd.DataFrame({
            "채널명": ["샘플 채널 A", "샘플 채널 B"],
            "분류1": ["연예인", "예능"],
            "분류2": ["전체", "전체"],
            "구독자": [100000, 50000],
            "조회수": [1000000, 500000],
            "최근 30개 토탈": [50000, 20000]
        })
    
    try:
        sheet = client.open("유튜브보물창고_테스트").sheet1
        df = pd.DataFrame(sheet.get_all_records())
        
        # [해결됨] 숫자 컬럼 변환 로직
        numeric_cols = ['구독자', '조회수', '최근 30개 토탈', '동영상']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0).astype(int)
        return df
    except:
        return pd.DataFrame()

# --- [유틸] 데이터 처리 함수들 ---
def chunk_list(data, n):
    # 5열 배치를 위해 리스트를 분할
    res = [[] for _ in range(n)]
    for i, item in enumerate(data):
        res[i % n].append(item)
    return res

def sync_order(saved_order, df):
    live_cat1 = sorted(df['분류1'].unique().tolist()) if not df.empty else []
    current_order = saved_order.get('분류1_순서', [])
    new_order = [c for c in current_order if c in live_cat1]
    for c in live_cat1:
        if c not in new_order: new_order.append(c)
    return {'분류1_순서': new_order}

# --- [페이지 1] 대시보드 (함수 추가됨) ---
def show_dashboard():
    df = load_data()
    st.title("📊 대시보드")
    
    if df.empty:
        st.error("데이터를 불러올 수 없습니다.")
        return

    # 분류 선택 UI
    cat1_list = st.session_state.get('page_order', {}).get('분류1_순서', sorted(df['분류1'].unique()))
    selected_cat = st.selectbox("분류 선택", cat1_list)
    
    df_filtered = df[df['분류1'] == selected_cat]
    
    # 상단 요약 지표
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f"<div class='metric-card'><h3>{len(df_filtered)}</h3><p>채널 수</p></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='metric-card'><h3>{df_filtered['구독자'].sum():,}</h3><p>총 구독자</p></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='metric-card'><h3>{df_filtered['조회수'].sum():,}</h3><p>총 조회수</p></div>", unsafe_allow_html=True)
    
    st.divider()
    st.dataframe(df_filtered, use_container_width=True)

# --- [페이지 2] 순서 설정 ---
def show_settings():
    st.title("⚙️ 순서 설정")
    df = load_data()
    
    if 'page_order' not in st.session_state:
        st.session_state.page_order = sync_order({}, df)

    tab1, tab2 = st.tabs(["📂 분류 순서 정렬", "💾 저장"])

    with tab1:
        st.info("💡 카드를 드래그하여 순서를 변경하세요. 왼쪽의 번호는 고정됩니다.")
        current_list = st.session_state.page_order['분류1_순서']
        
        # 5열 그리드 배치
        chunked = chunk_list(current_list, 5)
        sortable_data = [{'header': '', 'items': c} for c in chunked]
        
        sorted_data = sort_items(sortable_data, multi_containers=True, direction='vertical', key='sort_main')
        
        # 결과 합치기 (열 순서대로)
        new_order = []
        max_len = max(len(c['items']) for c in sorted_data)
        for i in range(max_len):
            for container in sorted_data:
                if i < len(container['items']):
                    new_order.append(container['items'][i])
        
        if new_order != current_list:
            st.session_state.page_order['분류1_순서'] = new_order
            st.rerun()

    with tab2:
        if st.button("💾 구글 시트에 순서 저장 (준비 중)", type="primary"):
            st.success("순서가 세션에 임시 저장되었습니다.")

# --- 메인 실행 로직 ---
def main():
    if 'page' not in st.session_state:
        st.session_state.page = "dashboard"

    # 네비게이션바
    col1, col2 = st.columns([8, 2])
    with col2:
        if st.button("🏠 대시보드" if st.session_state.page == "settings" else "⚙️ 순서 설정"):
            st.session_state.page = "settings" if st.session_state.page == "dashboard" else "dashboard"
            st.rerun()

    if st.session_state.page == "dashboard":
        show_dashboard()
    else:
        show_settings()

if __name__ == "__main__":
    main()
