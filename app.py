import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json
from datetime import datetime
from streamlit_sortables import sort_items

# 1. 페이지 설정
st.set_page_config(
    page_title="YouTube 보물창고",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"  # 오른쪽 창을 기본으로 열어둠
)

# 2. 커스텀 CSS (엑셀 스타일 + 오른쪽 사이드바 결합)
st.markdown("""
<style>
    /* [기존 기능] 엑셀/표 스타일 번호 고정 */
    .stApp { counter-reset: item-rank; }
    div[data-testid="stTabContent"] { counter-reset: item-rank; }

    .sortable-item {
        background-color: white !important;
        color: #333 !important;
        border: 1px solid #ccc !important;
        border-radius: 4px !important;
        padding: 0 !important;
        margin-bottom: 8px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
        font-size: 15px !important;
        font-weight: 500 !important;
        cursor: grab !important;
        display: flex !important;
        align-items: center !important;
        height: 42px !important;
        overflow: hidden !important;
        counter-increment: item-rank;
    }
    
    .sortable-item::before {
        content: counter(item-rank);
        background-color: #eee !important;
        color: #555 !important;
        font-weight: bold !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 45px !important;
        height: 100% !important;
        border-right: 1px solid #ccc !important;
        margin-right: 12px !important;
        flex-shrink: 0 !important;
    }

    /* [신규 기능] 사이드바를 오른쪽으로 이동 */
    [data-testid="stSidebar"] {
        left: auto !important;
        right: 0 !important;
        width: 350px !important;
        background-color: #f8f9fa;
        border-left: 1px solid #ddd;
    }
    /* 메인 컨텐츠 여백 조정 (사이드바가 오른쪽에 있으므로) */
    [data-testid="stSidebarNav"] { display: none; }
    
    /* 사이드바 내 버튼 스타일 */
    .sidebar-btn-container .stButton > button {
        width: 100%;
        text-align: left;
        padding: 0.5rem 1rem;
        margin-bottom: 4px;
    }

    /* 지표 카드 스타일 */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-card h3 { font-size: 2rem; margin: 0; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 데이터 로드 및 처리 함수 (기존과 동일) ---
def format_korean_number(num):
    if pd.isna(num) or num == 0: return "0"
    num = int(num)
    if num >= 100000000:
        eok, man = divmod(num, 100000000)
        return f"{eok}.{man//10000000}억" if man >= 10000000 else f"{eok}억"
    elif num >= 10000:
        man, cheon = divmod(num, 10000)
        return f"{man}.{cheon//1000}만" if cheon >= 1000 else f"{man}만"
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
        num_cols = ['구독자', '동영상', '조회수', '최근 5개 토탈', '최근 10개 토탈', '최근 20개 토탈', '최근 30개 토탈']
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return pd.DataFrame()

# --- 설정 저장/로드 (기존과 동일) ---
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
        try: ws = doc.worksheet("config")
        except: ws = doc.add_worksheet(title="config", rows=10, cols=10)
        ws.update_acell('A1', json.dumps(order_data, ensure_ascii=False))
        return True
    except: return False

def sync_order_with_data(saved_order, df):
    live_cat1 = set(df['분류1'].dropna().unique())
    new_cat1 = [c for c in saved_order.get('분류1_순서', []) if c in live_cat1]
    for c in sorted(live_cat1):
        if c not in new_cat1: new_cat1.append(c)
    saved_order['분류1_순서'] = new_cat1
    if '분류2_순서' not in saved_order: saved_order['분류2_순서'] = {}
    for cat1 in new_cat1:
        live_cat2 = set(df[df['분류1'] == cat1]['분류2'].dropna().unique())
        live_cat2.add('전체')
        new_cat2 = [c for c in saved_order['분류2_순서'].get(cat1, ['전체']) if c in live_cat2]
        for c in sorted(live_cat2):
            if c not in new_cat2: new_cat2.append(c)
        saved_order['분류2_순서'][cat1] = new_cat2
    return saved_order

# --- 내비게이션 (기존과 동일) ---
def show_navigation():
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    with col1: st.markdown("# 🎬 YouTube 보물창고")
    with col2:
        if st.button("🏠 대시보드", key="nav_dash", use_container_width=True):
            st.session_state.page = "dashboard"; st.rerun()
    with col3:
        if st.button("⚙️ 순서 설정", key="nav_set", use_container_width=True):
            st.session_state.page = "settings"; st.rerun()
    with col4:
        if st.button("🔄 새로고침", key="nav_ref", use_container_width=True):
            st.cache_data.clear(); st.rerun()

# --- 대시보드 (오른쪽 사이드바 적용) ---
def show_dashboard():
    df = load_data()
    if df.empty: return
    
    if 'page_order' not in st.session_state:
        saved = load_config_from_sheet()
        st.session_state.page_order = sync_order_with_data(saved if saved else {'분류1_순서': [], '분류2_순서': {}}, df)

    분류1_list = st.session_state.page_order['분류1_순서']
    if 'selected_분류1' not in st.session_state:
        st.session_state.selected_분류1 = 분류1_list[0] if 분류1_list else None

    # [수정] 오른쪽 사이드바에 분류 버튼 배치
    with st.sidebar:
        st.markdown("### 📂 분류 선택")
        for cat in 분류1_list:
            is_active = (st.session_state.selected_분류1 == cat)
            if st.button(cat, key=f"side_{cat}", use_container_width=True, type="primary" if is_active else "secondary"):
                st.session_state.selected_분류1 = cat
                st.rerun()

    # 메인 영역에 상세 내용 표시
    if st.session_state.selected_분류1:
        show_category_detail(df, st.session_state.selected_분류1)

# --- 세부 리스트 (URL 클릭 + 모든 토탈 지표 포함) ---
def show_category_detail(df, 분류1):
    df_filtered = df[df['분류1'] == 분류1].copy()
    분류2_list = st.session_state.page_order['분류2_순서'].get(분류1, ['전체'])

    st.markdown(f"## 📊 {분류1}")
    col1, col2 = st.columns([1, 3])
    with col1: selected_분류2 = st.selectbox("🔍 분류2 선택", 분류2_list)
    
    df_display = df_filtered[df_filtered['분류2'] == selected_분류2].copy() if selected_분류2 != '전체' else df_filtered.copy()
    
    # 상단 요약 카드
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f"<div class='metric-card'><h3>{len(df_display)}</h3><p>채널 수</p></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='metric-card'><h3>{format_korean_number(df_display['구독자'].sum())}</h3><p>총 구독자</p></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='metric-card'><h3>{format_korean_number(df_display['조회수'].sum())}</h3><p>총 조회수</p></div>", unsafe_allow_html=True)
    with c4: st.markdown(f"<div class='metric-card'><h3>{format_korean_number(df_display['최근 30개 토탈'].sum())}</h3><p>최근 30개 합계</p></div>", unsafe_allow_html=True)
    
    st.markdown("---")
    s1, s2 = st.columns([2, 1])
    with s1: search = st.text_input("🔍 채널명 검색")
    with s2: sort_by = st.selectbox("정렬 기준", ['최근 30개 토탈', '최근 20개 토탈', '최근 10개 토탈', '최근 5개 토탈', '구독자'])
    
    if search: df_display = df_display[df_display['채널명'].str.contains(search, case=False, na=False)]
    df_display = df_display.sort_values(by=[sort_by, '채널명'], ascending=[False, True])
    
    # 표시 컬럼 (요청하신 모든 토탈 지표 포함)
    display_cols = ['채널명', 'URL', '분류2', '구독자', '최근 5개 토탈', '최근 10개 토탈', '최근 20개 토탈', '최근 30개 토탈']
    df_fmt = df_display[display_cols].copy()
    
    # 숫자 포맷 적용 (URL 제외)
    num_fmt_cols = ['구독자', '최근 5개 토탈', '최근 10개 토탈', '최근 20개 토탈', '최근 30개 토탈']
    for c in num_fmt_cols:
        df_fmt[c] = df_fmt[c].apply(format_korean_number)

    # [기존 기능] URL 클릭 가능하게 설정
    st.dataframe(
        df_fmt,
        use_container_width=True,
        height=600,
        column_config={
            "URL": st.column_config.LinkColumn("채널 링크", display_text="바로가기"),
            "채널명": st.column_config.TextColumn("채널명", width="medium")
        },
        hide_index=True
    )

# --- [기존 기능 완벽 복구] 순서 설정 (엑셀 스타일) ---
def show_settings():
    st.markdown("## ⚙️ 순서 설정")
    df = load_data()
    if df.empty: return
    
    if 'page_order' not in st.session_state:
        saved = load_config_from_sheet()
        st.session_state.page_order = sync_order_with_data(saved if saved else {'분류1_순서': [], '분류2_순서': {}}, df)

    tab1, tab2, tab3 = st.tabs(["📂 분류1 순서", "📁 분류2 순서", "💾 저장"])

    with tab1:
        st.info("💡 카드를 드래그하여 순서를 변경하세요. 왼쪽의 번호는 고정됩니다.")
        current_list = st.session_state.page_order['분류1_순서']
        chunked = chunk_list(current_list, 5) 
        sortable_data = [{'header': '', 'items': c} for c in chunked]
        sorted_data = sort_items(sortable_data, multi_containers=True, direction='vertical', key='sort_cat1_final')
        new_order = [item for container in sorted_data for item in container['items']]
        if new_order != current_list:
            st.session_state.page_order['분류1_순서'] = new_order
            st.rerun()

    with tab2:
        col_sel, col_sort = st.columns([1, 3])
        with col_sel:
            st.markdown("##### 대분류 선택")
            selected_cat1 = st.radio("목록", st.session_state.page_order['분류1_순서'])
        with col_sort:
            st.markdown(f"##### '{selected_cat1}'의 분류2 순서")
            current_sub = st.session_state.page_order['분류2_순서'].get(selected_cat1, ['전체'])
            chunked_sub = chunk_list(current_sub, 4)
            sorted_sub = sort_items([{'header': '', 'items': c} for c in chunked_sub], multi_containers=True, key=f'sort_sub_{selected_cat1}')
            new_sub_order = [item for container in sorted_sub for item in container['items']]
            if new_sub_order != current_sub:
                st.session_state.page_order['분류2_순서'][selected_cat1] = new_sub_order
                st.rerun()

    with tab3:
        if st.button("💾 구글 시트에 저장하기", type="primary", use_container_width=True):
            if save_config_to_sheet(st.session_state.page_order):
                st.success("✅ 저장 완료!"); st.cache_data.clear()
            else: st.error("❌ 저장 실패")

def main():
    if 'page' not in st.session_state: st.session_state.page = "dashboard"
    show_navigation()
    st.markdown("---")
    if st.session_state.page == "dashboard": show_dashboard()
    elif st.session_state.page == "settings": show_settings()

if __name__ == "__main__":
    main()
