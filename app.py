import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json
from datetime import datetime
from streamlit_sortables import sort_items

# 페이지 설정
st.set_page_config(
    page_title="YouTube 보물창고",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 커스텀 CSS (기존 유지)
st.markdown("""
<style>
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
    .sortable-item:hover {
        border-color: #667eea !important;
        background-color: #f8f9fa !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
    }
    .sortable-container-header { display: none !important; }
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

# 숫자 포맷 함수
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

# 리스트 청크 함수
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
# 구글 시트 연결
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
        
        # 수치형 컬럼 변환
        numeric_columns = ['구독자', '동영상', '조회수', '최근 5개 토탈', 
                          '최근 10개 토탈', '최근 20개 토탈', '최근 30개 토탈']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"데이터 로드 실패: {str(e)}")
        return pd.DataFrame()

# 설정 관리 함수들 (생략 - 기존과 동일)
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
# UI 컴포넌트
# -------------------------------------------------------------
def show_navigation():
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    with col1: st.markdown("# 🎬 YouTube 보물창고")
    with col2:
        if st.button("🏠 대시보드", key="nav_dashboard"):
            st.session_state.page = "dashboard"; st.rerun()
    with col3:
        if st.button("⚙️ 순서 설정", key="nav_settings"):
            st.session_state.page = "settings"; st.rerun()
    with col4:
        if st.button("🔄 새로고침", key="nav_refresh"):
            st.cache_data.clear(); st.rerun()

def show_dashboard():
    df = load_data()
    if df.empty: return
    
    if 'page_order' not in st.session_state:
        saved_order = load_config_from_sheet()
        st.session_state.page_order = sync_order_with_data(saved_order if saved_order else {'분류1_순서': [], '분류2_순서': {}}, df)

    분류1_list = st.session_state.page_order['분류1_순서']
    if 'selected_분류1' not in st.session_state:
        st.session_state.selected_분류1 = 분류1_list[0] if 분류1_list else None
    
    st.markdown("### 📂 분류 선택")
    buttons_per_row = 6
    for i in range(0, len(분류1_list), buttons_per_row):
        cols = st.columns(buttons_per_row)
        for j, cat in enumerate(분류1_list[i:i+buttons_per_row]):
            is_active = (st.session_state.selected_분류1 == cat)
            if cols[j].button(cat, key=f"btn_{cat}", use_container_width=True, type="primary" if is_active else "secondary"):
                st.session_state.selected_분류1 = cat
                st.rerun()
    
    st.markdown("---")
    if st.session_state.selected_분류1:
        show_category_detail(df, st.session_state.selected_분류1)

# -------------------------------------------------------------
# [수정된 부분] 데이터 상세 보기 (URL 클릭 및 추가 컬럼)
# -------------------------------------------------------------
def show_category_detail(df, 분류1):
    df_filtered = df[df['분류1'] == 분류1].copy()
    if df_filtered.empty: return

    분류2_list = ['전체']
    if 'page_order' in st.session_state and 분류1 in st.session_state.page_order['분류2_순서']:
        분류2_list = st.session_state.page_order['분류2_순서'][분류1]
    
    col1, col2 = st.columns([1, 3])
    with col1: selected_분류2 = st.selectbox("🔍 분류2 선택", 분류2_list, key=f"분류2_{분류1}")
    
    df_display = df_filtered[df_filtered['분류2'] == selected_분류2].copy() if selected_분류2 != '전체' else df_filtered.copy()
    
    # 상단 지표
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f"<div class='metric-card'><h3>{len(df_display)}</h3><p>총 채널 수</p></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='metric-card'><h3>{format_korean_number(df_display['구독자'].sum())}</h3><p>총 구독자</p></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='metric-card'><h3>{format_korean_number(df_display['조회수'].sum())}</h3><p>총 조회수</p></div>", unsafe_allow_html=True)
    with c4: st.markdown(f"<div class='metric-card'><h3>{format_korean_number(df_display['최근 30개 토탈'].sum())}</h3><p>최근 30개 합계</p></div>", unsafe_allow_html=True)
    
    st.markdown("---")
    col_s1, col_s2 = st.columns([2, 1])
    with col_s1: search_query = st.text_input("🔍 채널명 검색", key=f"search_{분류1}")
    with col_s2: sort_by = st.selectbox("정렬 기준", ['최근 30개 토탈', '최근 20개 토탈', '최근 10개 토탈', '최근 5개 토탈', '구독자', '조회수'], key=f"sort_{분류1}")
    
    if search_query: df_display = df_display[df_display['채널명'].str.contains(search_query, case=False, na=False)]
    df_display = df_display.sort_values(by=[sort_by, '채널명'], ascending=[False, True])
    
    # [수정] 표시할 컬럼 확장
    display_columns = [
        '채널명', 'URL', '분류2', '구독자', '동영상', 
        '최근 5개 토탈', '최근 10개 토탈', '최근 20개 토탈', '최근 30개 토탈'
    ]
    df_fmt = df_display[[c for c in display_columns if c in df_display.columns]].copy()
    
    # 수치 포맷팅 (URL 제외)
    for col in df_fmt.columns:
        if col != 'URL' and df_fmt[col].dtype in ['int64', 'float64']:
            df_fmt[col] = df_fmt[col].apply(format_korean_number)
        
    st.markdown(f"### 📋 채널 리스트 (총 {len(df_display)}개)")
    
    # [수정] st.dataframe의 column_config를 사용하여 URL을 클릭 가능하게 설정
    st.dataframe(
        df_fmt,
        use_container_width=True,
        height=600,
        column_config={
            "URL": st.column_config.LinkColumn(
                "채널 링크", 
                help="클릭하면 해당 채널로 이동합니다",
                display_text="바로가기"  # 표에 표시될 텍스트 (URL 대신 '바로가기'로 표시됨)
            ),
            "채널명": st.column_config.TextColumn("채널명", width="medium"),
            "구독자": st.column_config.TextColumn("구독자", width="small"),
            "최근 5개 토탈": st.column_config.TextColumn("최근5개", width="small"),
            "최근 10개 토탈": st.column_config.TextColumn("최근10개", width="small"),
            "최근 20개 토탈": st.column_config.TextColumn("최근20개", width="small"),
            "최근 30개 토탈": st.column_config.TextColumn("최근30개", width="small"),
        },
        hide_index=True
    )

# 순서 설정 페이지 (기존과 동일)
def show_settings():
    st.markdown("## ⚙️ 순서 설정")
    df = load_data()
    if df.empty: return
    
    if 'page_order' not in st.session_state:
        saved_order = load_config_from_sheet()
        st.session_state.page_order = sync_order_with_data(saved_order if saved_order else {'분류1_순서': [], '분류2_순서': {}}, df)

    tab1, tab2, tab3 = st.tabs(["📂 분류1 순서", "📁 분류2 순서", "💾 저장"])

    with tab1:
        st.info("💡 카드를 드래그하여 순서를 변경하세요.")
        current_list = st.session_state.page_order['분류1_순서']
        chunked_list = chunk_list(current_list, 5) 
        sortable_data = [{'header': '', 'items': chunk} for chunk in chunked_list]
        sorted_data = sort_items(sortable_data, multi_containers=True, direction='vertical', key='sortable_cat1_v5')
        new_order = [item for container in sorted_data for item in container['items']]
        if new_order != current_list:
            st.session_state.page_order['분류1_순서'] = new_order
            st.rerun()

    with tab2:
        col_sel, col_sort = st.columns([1, 3])
        with col_sel:
            selected_cat1 = st.radio("대분류 선택", st.session_state.page_order['분류1_순서'])
        with col_sort:
            current_sub = st.session_state.page_order['분류2_순서'].get(selected_cat1, ['전체'])
            chunked_sub = chunk_list(current_sub, 4) 
            sorted_sub_data = sort_items([{'header': '', 'items': c} for c in chunked_sub], multi_containers=True, key=f'sort_sub_{selected_cat1}_v5')
            new_sub_order = [item for container in sorted_sub_data for item in container['items']]
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
    st.markdown(f"*Update: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

if __name__ == "__main__":
    main()
