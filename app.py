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

# 커스텀 CSS
st.markdown("""
<style>
    /* 1. 카운터 초기화 */
    .stApp { counter-reset: item-rank; }
    div[data-testid="stTabContent"] { counter-reset: item-rank; }

    /* 2. Sortable 아이템 스타일 */
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
    
    /* 3. 번호 박스 */
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
    
    /* 호버 효과 */
    .sortable-item:hover {
        border-color: #667eea !important;
        background-color: #f8f9fa !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
    }

    /* 헤더 숨기기 */
    .sortable-container-header { display: none !important; }
    
    /* 테이블 스타일 */
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 1rem 0;
        font-size: 14px;
    }
    table thead tr {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    table th {
        padding: 12px;
        font-weight: bold;
        border: 1px solid #ddd;
        text-align: center;
        white-space: nowrap;
    }
    table td {
        padding: 10px;
        border: 1px solid #ddd;
        text-align: center;
    }
    table tbody tr:nth-child(even) { background-color: #f9f9f9; }
    table tbody tr:hover { background-color: #f0f0ff; }
    
    /* URL 링크 스타일 */
    table a {
        color: #1E90FF !important;
        font-weight: 600 !important;
        text-decoration: none !important;
    }
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
# 구글 시트 연결 및 설정 관리
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
        
        numeric_columns = ['구독자', '동영상', '조회수', '최근 5개 토탈', 
                          '최근 10개 토탈', '최근 20개 토탈', '최근 30개 토탈']
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
        try:
            worksheet = doc.worksheet("config")
            config_json = worksheet.acell('A1').value
            if config_json: return json.loads(config_json)
        except: return None
    except: return None

def save_config_to_sheet(order_data):
    try:
        client = get_gspread_client()
        doc = client.open("유튜브보물창고_테스트")
        try:
            worksheet = doc.worksheet("config")
        except:
            worksheet = doc.add_worksheet(title="config", rows=10, cols=10)
        
        json_str = json.dumps(order_data, ensure_ascii=False)
        worksheet.update_acell('A1', json_str)
        return True
    except Exception as e:
        st.error(f"설정 저장 실패: {str(e)}")
        return False

# -------------------------------------------------------------
# 데이터 동기화 함수
# -------------------------------------------------------------
def sync_order_with_data(saved_order, df):
    # 1. 분류1 동기화
    live_cat1 = set(df['분류1'].dropna().unique())
    current_cat1_order = saved_order.get('분류1_순서', [])
    new_cat1_order = [c for c in current_cat1_order if c in live_cat1]
    for c in sorted(list(live_cat1)):
        if c not in new_cat1_order: new_cat1_order.append(c)
    saved_order['분류1_순서'] = new_cat1_order
    
    # 2. 분류2 동기화
    if '분류2_순서' not in saved_order: saved_order['분류2_순서'] = {}
    for cat1 in new_cat1_order:
        live_cat2 = set(df[df['분류1'] == cat1]['분류2'].dropna().unique())
        live_cat2.add('전체')
        current_cat2_order = saved_order['분류2_순서'].get(cat1, ['전체'])
        new_cat2_order = [c for c in current_cat2_order if c in live_cat2]
        for c in sorted(list(live_cat2)):
            if c not in new_cat2_order: new_cat2_order.append(c)
        saved_order['분류2_순서'][cat1] = new_cat2_order
    
    # 3. 컬럼 순서 동기화 (헤더 드래그 기능용)
    default_columns = ['채널명', 'URL', '국가', '분류2', '구독자', '동영상', '조회수', 
                       '최근 5개 토탈', '최근 10개 토탈', '최근 20개 토탈', '최근 30개 토탈']
    if '컬럼_순서' not in saved_order:
        saved_order['컬럼_순서'] = default_columns
    else:
        # 실제 데이터에 있는 컬럼만 유지하고 새로운 컬럼이 있다면 추가
        live_cols = [col for col in default_columns if col in df.columns or col == 'URL']
        saved_cols = [c for c in saved_order['컬럼_순서'] if c in live_cols]
        for c in live_cols:
            if c not in saved_cols: saved_cols.append(c)
        saved_order['컬럼_순서'] = saved_cols

    if '채널_순서' not in saved_order: saved_order['채널_순서'] = {}
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
        st.session_state.page_order = sync_order_with_data(saved_order or {}, df)

    분류1_list = st.session_state.page_order['분류1_순서']
    if 'selected_분류1' not in st.session_state:
        st.session_state.selected_분류1 = 분류1_list[0] if 분류1_list else None
    
    with st.sidebar:
        st.markdown("### 📂 분류 선택")
        for cat in 분류1_list:
            if st.button(cat, key=f"sb_{cat}", use_container_width=True, 
                         type="primary" if st.session_state.selected_분류1 == cat else "secondary"):
                st.session_state.selected_분류1 = cat; st.rerun()
    
    if st.session_state.selected_분류1:
        show_category_detail(df, st.session_state.selected_분류1)

def show_category_detail(df, 분류1):
    df_filtered = df[df['분류1'] == 분류1].copy()
    분류2_list = st.session_state.page_order['분류2_순서'].get(분류1, ['전체'])

    st.markdown(f"## 📊 {분류1}")
    col1, col2 = st.columns([1, 3])
    with col1: selected_분류2 = st.selectbox("🔍 분류2 선택", 분류2_list, key=f"sel2_{분류1}")
    
    df_display = df_filtered[df_filtered['분류2'] == selected_분류2].copy() if selected_분류2 != '전체' else df_filtered.copy()
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1: search_query = st.text_input("🔍 채널명 검색", key=f"sh_{분류1}")
    with col2: sort_by = st.selectbox("정렬 기준", ['최근 30개 토탈', '최근 20개 토탈', '최근 10개 토탈', '구독자', '사용자 지정'], key=f"st_{분류1}")
    with col3: view_mode = st.selectbox("표시 방식", ['테이블', '드래그'], key=f"vm_{분류1}")
    
    if search_query: df_display = df_display[df_display['채널명'].str.contains(search_query, case=False, na=False)]
    
    # 정렬 처리
    if sort_by == '사용자 지정':
        order_key = f"{분류1}_{selected_분류2}"
        if '채널_순서' in st.session_state.page_order and order_key in st.session_state.page_order['채널_순서']:
            s_order = st.session_state.page_order['채널_순서'][order_key]
            df_display['temp_rank'] = df_display['채널명'].apply(lambda x: s_order.index(x) if x in s_order else 9999)
            df_display = df_display.sort_values('temp_rank').drop('temp_rank', axis=1)
    else:
        df_display = df_display.sort_values(by=[sort_by, '채널명'], ascending=[False, True])

    # [수정] 설정된 컬럼 순서 적용
    col_order = st.session_state.page_order.get('컬럼_순서', [])
    display_columns = [c for c in col_order if c in df_display.columns]
    df_fmt = df_display[display_columns].copy()

    if view_mode == '드래그':
        st.markdown("### 🎯 채널 순서 변경")
        channel_items = [f"{r['채널명']} | 최근30: {format_korean_number(r.get('최근 30개 토탈',0))}" for _, r in df_display.iterrows()]
        sorted_c = sort_items([{'header': '', 'items': chunk} for chunk in chunk_list(channel_items, 3)], multi_containers=True, key=f"sort_c_{분류1}_{selected_분류2}")
        new_c_order = [i.split(' | ')[0] for c in sorted_c for i in c['items']]
        if st.button("💾 순서 저장", type="primary"):
            st.session_state.page_order['채널_순서'][f"{분류1}_{selected_분류2}"] = new_c_order
            save_config_to_sheet(st.session_state.page_order); st.rerun()
        return

    # 테이블 모드 포맷팅
    for col in df_fmt.columns:
        if col != 'URL' and df_fmt[col].dtype in ['int64', 'float64']: 
            df_fmt[col] = df_fmt[col].apply(format_korean_number)
    if 'URL' in df_fmt.columns:
        df_fmt['URL'] = df_fmt['URL'].apply(lambda x: f'<a href="{x}" target="_blank">보기</a>' if pd.notna(x) else '')

    # 페이지네이션 및 테이블 출력
    rows_per_page = st.selectbox("표시 개수", [50, 100, 200], key=f"rpp_{분류1}")
    total_pages = max((len(df_fmt) - 1) // rows_per_page + 1, 1)
    curr_p = st.number_input("페이지", 1, total_pages, 1, key=f"p_{분류1}")
    
    start_idx = (curr_p - 1) * rows_per_page
    st.markdown(df_fmt.iloc[start_idx:start_idx+rows_per_page].to_html(escape=False, index=False), unsafe_allow_html=True)

# -------------------------------------------------------------
# 순서 설정 (컬럼 순서 탭 추가)
# -------------------------------------------------------------
def show_settings():
    st.markdown("## ⚙️ 순서 설정")
    df = load_data()
    if df.empty: return
    
    if 'page_order' not in st.session_state:
        saved_order = load_config_from_sheet()
        st.session_state.page_order = sync_order_with_data(saved_order or {}, df)

    tab1, tab2, tab3, tab4 = st.tabs(["📂 분류1 순서", "📁 분류2 순서", "📋 컬럼(헤더) 순서", "💾 저장"])

    with tab1:
        cur = st.session_state.page_order['분류1_순서']
        res = sort_items([{'header': '', 'items': c} for c in chunk_list(cur, 5)], multi_containers=True, key="s_cat1")
        new = [i for c in res for i in c['items']]
        if new != cur: st.session_state.page_order['분류1_순서'] = new; st.rerun()

    with tab2:
        sel1 = st.radio("대분류 선택", st.session_state.page_order['분류1_순서'], horizontal=True)
        cur2 = st.session_state.page_order['분류2_순서'].get(sel1, ['전체'])
        res2 = sort_items([{'header': '', 'items': c} for c in chunk_list(cur2, 4)], multi_containers=True, key=f"s_cat2_{sel1}")
        new2 = [i for c in res2 for i in c['items']]
        if new2 != cur2: st.session_state.page_order['분류2_순서'][sel1] = new2; st.rerun()

    with tab3:
        st.info("💡 대시보드 테이블의 헤더 순서를 드래그하여 변경하세요. (왼쪽이 테이블의 앞쪽)")
        cur_cols = st.session_state.page_order.get('컬럼_순서', [])
        res_cols = sort_items([{'header': '', 'items': c} for c in chunk_list(cur_cols, 3)], multi_containers=True, key="s_cols")
        new_cols = [i for c in res_cols for i in c['items']]
        if new_cols != cur_cols: st.session_state.page_order['컬럼_순서'] = new_cols; st.rerun()

    with tab4:
        if st.button("💾 모든 설정 구글 시트에 저장", type="primary", use_container_width=True):
            if save_config_to_sheet(st.session_state.page_order):
                st.success("✅ 저장 완료!"); st.cache_data.clear()
        if st.button("🔄 설정 초기화", use_container_width=True):
            st.session_state.page_order = sync_order_with_data({}, df); st.rerun()

def main():
    if 'page' not in st.session_state: st.session_state.page = "dashboard"
    show_navigation()
    if st.session_state.page == "dashboard": show_dashboard()
    else: show_settings()
    st.markdown(f"--- \n *Update: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

if __name__ == "__main__":
    main()
