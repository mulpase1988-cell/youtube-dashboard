import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json
from datetime import datetime
from streamlit_sortables import sort_items

# --- [1] 페이지 기본 설정 ---
st.set_page_config(
    page_title="YouTube 보물창고",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- [2] 디자인 커스텀 CSS (이미지 요청 반영 - 빨간 버튼 및 고정 번호) ---
st.markdown("""
<style>
    /* 전체 앱 배경 및 카운터 초기화 */
    .stApp { counter-reset: rank-counter; }
    
    /* 드래그 항목 컨테이너 레이아웃 */
    .sortable-item {
        display: flex !important;
        align-items: center !important;
        margin-bottom: 12px !important;
        background: transparent !important;
        border: none !important;
        counter-increment: rank-counter;
        cursor: grab !important;
    }

    /* [왼쪽 번호 영역] 고정된 디자인 */
    .sortable-item::before {
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
    }

    /* 대시보드 메트릭 카드 */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .metric-card h3 { font-size: 2rem; margin: 0; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- [3] 유틸리티 함수 (숫자 포맷) ---
def format_korean_number(num):
    if pd.isna(num) or num == 0: return "0"
    num = int(num)
    if num >= 100000000:
        eok = num // 100000000
        man = (num % 100000000) // 10000
        return f"{eok}.{man//1000}억" if man > 0 else f"{eok}억"
    elif num >= 10000:
        man = num // 10000
        cheon = (num % 10000) // 1000
        return f"{man}.{cheon}만" if cheon > 0 else f"{man}만"
    else:
        return f"{num:,}"

def chunk_list(data, num_chunks):
    if not data: return [[] for _ in range(num_chunks)]
    avg = len(data) / float(num_chunks)
    chunks = []
    last = 0.0
    for _ in range(num_chunks):
        next_val = last + avg
        chunks.append(data[int(last):int(next_val)])
        last = next_val
    return chunks

# --- [4] 데이터 연동 로직 (기존 기능 유지) ---
def get_gspread_client():
    credentials_dict = dict(st.secrets["gcp_service_account"])
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
    return gspread.authorize(credentials)

@st.cache_data(ttl=600)
def load_data():
    try:
        client = get_gspread_client()
        sheet = client.open("유튜브보물창고_테스트").sheet1
        df = pd.DataFrame(sheet.get_all_records())
        
        numeric_cols = ['구독자', '동영상', '조회수', '최근 5개 토탈', '최근 10개 토탈', '최근 20개 토탈', '최근 30개 토탈']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return pd.DataFrame()

# --- [5] 설정 저장/로드 (기존 config 시트 활용) ---
def load_config_from_sheet():
    try:
        client = get_gspread_client()
        worksheet = client.open("유튜브보물창고_테스트").worksheet("config")
        return json.loads(worksheet.acell('A1').value)
    except: return None

def save_config_to_sheet(order_data):
    try:
        client = get_gspread_client()
        doc = client.open("유튜브보물창고_테스트")
        try: worksheet = doc.worksheet("config")
        except: worksheet = doc.add_worksheet(title="config", rows=5, cols=5)
        worksheet.update_acell('A1', json.dumps(order_data, ensure_ascii=False))
        return True
    except: return False

def sync_order_with_data(saved_order, df):
    live_cat1 = sorted(df['분류1'].dropna().unique().tolist())
    new_cat1_order = [c for c in saved_order.get('분류1_순서', []) if c in live_cat1]
    for c in live_cat1:
        if c not in new_cat1_order: new_cat1_order.append(c)
    
    saved_order['분류1_순서'] = new_cat1_order
    return saved_order

# --- [6] 페이지별 UI ---
def show_dashboard():
    st.title("📊 대시보드")
    df = load_data()
    if df.empty: return
    
    cat1_order = st.session_state.page_order['분류1_순서']
    selected_cat = st.selectbox("📂 분류 선택", cat1_order)
    
    df_filtered = df[df['분류1'] == selected_cat]
    
    # 상단 지표
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f"<div class='metric-card'><h3>{len(df_filtered)}</h3><p>채널 수</p></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='metric-card'><h3>{format_korean_number(df_filtered['구독자'].sum())}</h3><p>총 구독자</p></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='metric-card'><h3>{format_korean_number(df_filtered['조회수'].sum())}</h3><p>총 조회수</p></div>", unsafe_allow_html=True)
    with c4: st.markdown(f"<div class='metric-card'><h3>{format_korean_number(df_filtered['최근 30개 토탈'].sum())}</h3><p>최근 30개 총합</p></div>", unsafe_allow_html=True)
    
    st.divider()
    st.dataframe(df_filtered, use_container_width=True)

def show_settings():
    st.title("⚙️ 순서 설정")
    df = load_data()
    if df.empty: return

    tab1, tab2 = st.tabs(["📂 분류 순서", "💾 저장"])

    with tab1:
        st.info("💡 카드를 드래그하여 순서를 변경하세요. 번호는 고정됩니다.")
        current_list = st.session_state.page_order['분류1_순서']
        
        # 5열 그리드 배치 (기존 로직 유지)
        chunked = chunk_list(current_list, 5)
        sortable_data = [{'header': '', 'items': c} for c in chunked]
        sorted_data = sort_items(sortable_data, multi_containers=True, direction='vertical', key='main_sort')
        
        new_order = [item for container in sorted_data for item in container['items']]
        if new_order != current_list:
            st.session_state.page_order['분류1_순서'] = new_order
            st.rerun()

    with tab2:
        if st.button("💾 구글 시트에 순서 영구 저장", type="primary"):
            if save_config_to_sheet(st.session_state.page_order):
                st.success("✅ 저장이 완료되었습니다!")
                st.cache_data.clear()

# --- [7] 메인 실행 로직 ---
def main():
    if 'page' not in st.session_state: st.session_state.page = "dashboard"
    
    # 상단 네비게이션
    col1, col2 = st.columns([8, 2])
    with col2:
        btn_label = "🏠 대시보드" if st.session_state.page == "settings" else "⚙️ 순서 설정"
        if st.button(btn_label):
            st.session_state.page = "settings" if st.session_state.page == "dashboard" else "dashboard"
            st.rerun()

    # 데이터 및 설정 로드 초기화
    if 'page_order' not in st.session_state:
        df = load_data()
        saved = load_config_from_sheet()
        st.session_state.page_order = sync_order_with_data(saved if saved else {}, df)

    if st.session_state.page == "dashboard": show_dashboard()
    else: show_settings()

if __name__ == "__main__":
    main()
