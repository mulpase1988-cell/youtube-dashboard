import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json
from datetime import datetime
from streamlit_sortables import sort_items

# -------------------------------------------------------------
# 1. 페이지 설정 및 디자인 (사진의 번호 고정 디자인 반영)
# -------------------------------------------------------------
st.set_page_config(
    page_title="YouTube 보물창고",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    /* 1. 순서 설정 페이지 전용: 카운터 초기화 (번호 고정 효과) */
    div[data-testid="stTabContent"] { counter-reset: item-rank; }

    /* 2. Sortable 아이템 스타일 (행 전체) */
    .sortable-item {
        background-color: transparent !important;
        border: none !important;
        padding: 0 !important;
        margin-bottom: 0 !important;
        display: flex !important;
        align-items: center !important;
        height: 48px !important;
        cursor: grab !important;
    }
    
    /* 3. 번호 박스 (왼쪽 고정 영역 - 엑셀 스타일) */
    .sortable-item::before {
        content: counter(item-rank);
        counter-increment: item-rank;
        background-color: #ffffff !important;
        color: #333 !important;
        font-weight: bold !important;
        font-size: 16px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 55px !important;
        height: 100% !important;
        border: 1px solid #d1d1d1 !important;
        margin-right: 15px !important;
        flex-shrink: 0 !important;
    }
    
    /* 4. 실제 드래그되는 카드 (오른쪽 빨간 영역) */
    .sortable-item > div {
        flex-grow: 1 !important;
        background-color: #FF4B4B !important;
        color: white !important;
        padding: 10px 15px !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        text-align: center !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
        border: 1px solid #e03e3e !important;
        max-width: 250px !important;
        font-size: 15px !important;
    }

    /* 기존 대시보드 스타일 유지 */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-card h3 { font-size: 2rem; margin: 0; font-weight: bold; color: white !important; }
    .metric-card p { margin: 0; opacity: 0.9; }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# 2. 유틸리티 함수 (기존 로직 그대로 유지)
# -------------------------------------------------------------
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
    else: return f"{num:,}"

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

# -------------------------------------------------------------
# 3. 구글 시트 연결 및 설정 관리
# -------------------------------------------------------------
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
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        numeric_columns = ['구독자', '동영상', '조회수', '최근 5개 토탈', '최근 10개 토탈', '최근 20개 토탈', '최근 30개 토탈']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"데이터 로드 실패: {str(e)}")
        return pd.DataFrame()

def load_config_from_sheet():
    try:
        client = get_gspread_client()
        doc = client.open("유튜브보물창고_테스트")
        worksheet = doc.worksheet("config")
        config_json = worksheet.acell('A1').value
        return json.loads(config_json) if config_json else None
    except: return None

def save_config_to_sheet(order_data):
    try:
        client = get_gspread_client()
        doc = client.open("유튜브보물창고_테스트")
        try: worksheet = doc.worksheet("config")
        except: worksheet = doc.add_worksheet(title="config", rows=10, cols=10)
        worksheet.update_acell('A1', json.dumps(order_data, ensure_ascii=False))
        return True
    except: return False

def sync_order_with_data(saved_order, df):
    live_cat1 = set(df['분류1'].dropna().unique())
    current_cat1_order = saved_order.get('분류1_순서', [])
    new_cat1_order = [c for c in current_cat1_order if c in live_cat1]
    for c in sorted(list(live_cat1)):
        if c not in new_cat1_order: new_cat1_order.append(c)
    saved_order['분류1_순서'] = new_cat1_order
    
    if '분류2_순서' not in saved_order: saved_order['분류2_순서'] = {}
    for cat1 in new_cat1_order:
        live_cat2 = set(df[df['분류1'] == cat1]['분류2'].dropna().unique())
        live_cat2.add('전체')
        current_cat2_order = saved_order['분류2_순서'].get(cat1, ['전체'])
        new_cat2_order = [c for c in current_cat2_order if c in live_cat2]
        for c in sorted(list(live_cat2)):
            if c not in new_cat2_order: new_cat2_order.append(c)
        saved_order['분류2_순서'][cat1] = new_cat2_order
    return saved_order

# -------------------------------------------------------------
# 4. UI 컴포넌트 (기존 기능 복구)
# -------------------------------------------------------------
def show_navigation():
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    with col1: st.markdown("# 🎬 YouTube 보물창고")
    with col2:
        if st.button("🏠 대시보드", key="nav_dashboard", use_container_width=True):
            st.session_state.page = "dashboard"; st.rerun()
    with col3:
        if st.button("⚙️ 순서 설정", key="nav_settings", use_container_width=True):
            st.session_state.page = "settings"; st.rerun()
    with col4:
        if st.button("🔄 새로고침", key="nav_refresh", use_container_width=True):
            st.cache_data.clear(); st.rerun()

def show_dashboard():
    df = load_data()
    if df.empty: return
    if 'page_order' not in st.session_state:
        saved = load_config_from_sheet()
        st.session_state.page_order = sync_order_with_data(saved if saved else {'분류1_순서': [], '분류2_순서': {}}, df)

    분류1_list = st.session_state.page_order['분류1_순서']
    if 'selected_분류1' not in st.session_state: st.session_state.selected_분류1 = 분류1_list[0] if 분류1_list else None
    
    st.markdown("### 📂 분류 선택")
    buttons_per_row = 6
    for i in range(0, len(분류1_list), buttons_per_row):
        cols = st.columns(buttons_per_row)
        for j, cat in enumerate(분류1_list[i:i+buttons_per_row]):
            with cols[j]:
                is_active = (st.session_state.selected_분류1 == cat)
                if st.button(cat, key=f"btn_{cat}", use_container_width=True, type="primary" if is_active else "secondary"):
                    st.session_state.selected_분류1 = cat; st.rerun()
    
    st.markdown("---")
    if st.session_state.selected_분류1: show_category_detail(df, st.session_state.selected_분류1)

def show_category_detail(df, 분류1):
    df_filtered = df[df['분류1'] == 분류1].copy()
    분류2_list = st.session_state.page_order['분류2_순서'].get(분류1, ['전체'])

    st.markdown(f"## 📊 {분류1}")
    col1, col2 = st.columns([1, 3])
    with col1: selected_분류2 = st.selectbox("🔍 분류2 선택", 분류2_list, key=f"분류2_{분류1}")
    
    df_display = df_filtered[df_filtered['분류2'] == selected_분류2].copy() if selected_분류2 != '전체' else df_filtered.copy()
    
    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(f"<div class='metric-card'><h3>{len(df_display)}</h3><p>총 채널 수</p></div>", unsafe_allow_html=True)
    m2.markdown(f"<div class='metric-card'><h3>{format_korean_number(df_display['구독자'].sum())}</h3><p>총 구독자</p></div>", unsafe_allow_html=True)
    m3.markdown(f"<div class='metric-card'><h3>{format_korean_number(df_display['조회수'].sum())}</h3><p>총 조회수</p></div>", unsafe_allow_html=True)
    m4.markdown(f"<div class='metric-card'><h3>{format_korean_number(df_display['최근 30개 토탈'].sum())}</h3><p>최근 30개 합계</p></div>", unsafe_allow_html=True)
    
    st.markdown("---")
    c1, c2 = st.columns([2, 1])
    with c1: search_query = st.text_input("🔍 채널명 검색", key=f"search_{분류1}")
    with c2: sort_by = st.selectbox("정렬 기준", ['최근 30개 토탈', '최근 20개 토탈', '최근 10개 토탈', '구독자', '조회수'], key=f"sort_{분류1}")
    
    if search_query: df_display = df_display[df_display['채널명'].str.contains(search_query, case=False, na=False)]
    df_display = df_display.sort_values(by=[sort_by, '채널명'], ascending=[False, True])
    
    df_fmt = df_display.copy()
    for col in df_fmt.columns:
        if df_fmt[col].dtype in ['int64', 'float64']: df_fmt[col] = df_fmt[col].apply(format_korean_number)
    st.dataframe(df_fmt, use_container_width=True, height=500)

# -------------------------------------------------------------
# 5. 순서 설정 (ValueError 해결 및 사진 디자인 적용)
# -------------------------------------------------------------
def show_settings():
    st.markdown("## ⚙️ 순서 설정")
    df = load_data()
    if df.empty: return
    
    if 'page_order' not in st.session_state:
        saved = load_config_from_sheet()
        st.session_state.page_order = sync_order_with_data(saved if saved else {'분류1_순서': [], '분류2_순서': {}}, df)

    tab1, tab2, tab3 = st.tabs(["📂 분류1 순서", "📁 분류2 순서", "💾 저장"])

    with tab1:
        st.info("💡 오른쪽 빨간색 카드를 드래그하세요. 왼쪽 번호는 고정되어 표시됩니다.")
        items = [str(x) for x in st.session_state.page_order['분류1_순서'] if x]
        
        # [수정] multi_containers=True를 명시하여 ValueError 해결
        sorted_data = sort_items(
            [{'header': '', 'items': items}], 
            multi_containers=True, 
            direction='vertical', 
            key='sort_cat1_final'
        )
        
        if sorted_data:
            new_order = sorted_data[0]['items']
            if new_order != items:
                st.session_state.page_order['분류1_순서'] = new_order
                st.rerun()

    with tab2:
        selected_cat1 = st.selectbox("분류2를 수정할 대분류를 선택하세요", st.session_state.page_order['분류1_순서'])
        sub_items = [str(x) for x in st.session_state.page_order['분류2_순서'].get(selected_cat1, []) if x]
        
        # [수정] 여기도 동일하게 multi_containers=True 적용
        sorted_sub = sort_items(
            [{'header': f'[{selected_cat1}] 소분류 순서', 'items': sub_items}], 
            multi_containers=True, 
            direction='vertical', 
            key=f'sort_sub_{selected_cat1}'
        )
        
        if sorted_sub:
            new_sub_order = sorted_sub[0]['items']
            if new_sub_order != sub_items:
                st.session_state.page_order['분류2_순서'][selected_cat1] = new_sub_order
                st.rerun()

    with tab3:
        st.markdown("### 💾 설정 저장")
        if st.button("💾 구글 시트에 최종 저장하기", type="primary", use_container_width=True):
            if save_config_to_sheet(st.session_state.page_order):
                st.success("✅ 저장이 완료되었습니다!")
                st.cache_data.clear()
            else: st.error("❌ 저장 실패")

def main():
    if 'page' not in st.session_state: st.session_state.page = "dashboard"
    show_navigation()
    st.divider()
    if st.session_state.page == "dashboard": show_dashboard()
    elif st.session_state.page == "settings": show_settings()
    st.divider()
    st.markdown(f"*Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

if __name__ == "__main__":
    main()
