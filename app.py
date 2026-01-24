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

# 커스텀 CSS (엑셀/표 스타일 - 번호 고정, 내용 이동)
st.markdown("""
<style>
    /* 1. 카운터 초기화 */
    .stApp { counter-reset: item-rank; }
    div[data-testid="stTabContent"] { counter-reset: item-rank; }

    /* 2. Sortable 아이템 스타일 (카드 전체) */
    .sortable-item {
        background-color: white !important;  /* 흰색 배경 */
        color: #333 !important;              /* 검은 글씨 */
        border: 1px solid #ccc !important;   /* 회색 테두리 */
        border-radius: 4px !important;
        padding: 0 !important;               /* 내부 패딩 제거 (번호박스 꽉 채우기) */
        margin-bottom: 8px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
        font-size: 15px !important;
        font-weight: 500 !important;
        cursor: grab !important;
        
        /* Flex 레이아웃으로 [번호|내용] 배치 */
        display: flex !important;
        align-items: center !important;
        height: 42px !important;
        overflow: hidden !important;
        
        /* 카운터 증가 */
        counter-increment: item-rank;
    }
    
    /* 3. 번호 박스 (왼쪽 회색 영역) */
    .sortable-item::before {
        content: counter(item-rank);         /* 1, 2, 3... 자동 생성 */
        background-color: #eee !important;   /* 회색 배경 */
        color: #555 !important;
        font-weight: bold !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 45px !important;              /* 너비 고정 */
        height: 100% !important;             /* 높이 꽉 채우기 */
        border-right: 1px solid #ccc !important;
        margin-right: 12px !important;
        flex-shrink: 0 !important;           /* 찌그러짐 방지 */
    }
    
    /* 호버 효과 */
    .sortable-item:hover {
        border-color: #667eea !important;
        background-color: #f8f9fa !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
    }
    .sortable-item:hover::before {
        background-color: #e0e0e0 !important;
        color: #333 !important;
        border-right-color: #667eea !important;
    }

    /* 헤더 숨기기 */
    .sortable-container-header { display: none !important; }
    
    /* 기존 스타일 유지 */
    .nav-button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.75rem 1.5rem;
        border-radius: 10px;
        text-decoration: none;
        font-weight: bold;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-card h3 { font-size: 2rem; margin: 0; font-weight: bold; }
    .category-btn {
        padding: 0.75rem 1.5rem;
        border: 2px solid #667eea;
        border-radius: 25px;
        background: white;
        color: #667eea;
        font-weight: bold;
        cursor: pointer;
        text-align: center;
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
            if config_json:
                return json.loads(config_json)
        except gspread.WorksheetNotFound:
            return None
    except Exception:
        return None
    return None

def save_config_to_sheet(order_data):
    try:
        client = get_gspread_client()
        doc = client.open("유튜브보물창고_테스트")
        try:
            worksheet = doc.worksheet("config")
        except gspread.WorksheetNotFound:
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
    live_cat1 = set(df['분류1'].dropna().unique())
    
    current_cat1_order = saved_order.get('분류1_순서', [])
    new_cat1_order = [c for c in current_cat1_order if c in live_cat1]
    
    for c in sorted(list(live_cat1)):
        if c not in new_cat1_order:
            new_cat1_order.append(c)
            
    saved_order['분류1_순서'] = new_cat1_order
    
    if '분류2_순서' not in saved_order:
        saved_order['분류2_순서'] = {}
        
    for cat1 in new_cat1_order:
        live_cat2 = set(df[df['분류1'] == cat1]['분류2'].dropna().unique())
        live_cat2.add('전체')
        
        current_cat2_order = saved_order['분류2_순서'].get(cat1, ['전체'])
        new_cat2_order = [c for c in current_cat2_order if c in live_cat2]
        
        for c in sorted(list(live_cat2)):
            if c not in new_cat2_order:
                new_cat2_order.append(c)
                
        saved_order['분류2_순서'][cat1] = new_cat2_order
        
    saved_order['분류2_순서'] = {k:v for k,v in saved_order['분류2_순서'].items() if k in new_cat1_order}
    return saved_order

# -------------------------------------------------------------
# UI 컴포넌트
# -------------------------------------------------------------
def show_navigation():
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    with col1: st.markdown("# 🎬 YouTube 보물창고")
    with col2:
        if st.button("🏠 대시보드", key="nav_dashboard"):
            st.session_state.page = "dashboard"
            st.rerun()
    with col3:
        if st.button("⚙️ 순서 설정", key="nav_settings"):
            st.session_state.page = "settings"
            st.rerun()
    with col4:
        if st.button("🔄 새로고침", key="nav_refresh"):
            st.cache_data.clear()
            st.rerun()

def show_dashboard():
    df = load_data()
    if df.empty: return
    
    if 'page_order' not in st.session_state:
        saved_order = load_config_from_sheet()
        if saved_order:
            st.session_state.page_order = sync_order_with_data(saved_order, df)
        else:
            st.session_state.page_order = sync_order_with_data({'분류1_순서': [], '분류2_순서': {}}, df)

    분류1_list = st.session_state.page_order['분류1_순서']
    
    if 'selected_분류1' not in st.session_state:
        st.session_state.selected_분류1 = 분류1_list[0] if 분류1_list else None
    
    st.markdown("### 📂 분류 선택")
    buttons_per_row = 6
    num_rows = (len(분류1_list) + buttons_per_row - 1) // buttons_per_row
    
    for row in range(num_rows):
        cols = st.columns(buttons_per_row)
        start_idx = row * buttons_per_row
        end_idx = min(start_idx + buttons_per_row, len(분류1_list))
        
        for idx, col in enumerate(cols):
            if start_idx + idx < end_idx:
                cat = 분류1_list[start_idx + idx]
                with col:
                    is_active = (st.session_state.selected_분류1 == cat)
                    if st.button(cat, key=f"btn_{cat}_{row}_{idx}", use_container_width=True, type="primary" if is_active else "secondary"):
                        st.session_state.selected_분류1 = cat
                        st.rerun()
    
    st.markdown("---")
    if st.session_state.selected_분류1:
        show_category_detail(df, st.session_state.selected_분류1)

def show_category_detail(df, 분류1):
    df_filtered = df[df['분류1'] == 분류1].copy()
    if df_filtered.empty: return

    분류2_list = ['전체']
    if 'page_order' in st.session_state and '분류2_순서' in st.session_state.page_order and 분류1 in st.session_state.page_order['분류2_순서']:
        분류2_list = st.session_state.page_order['분류2_순서'][분류1]
    else:
        분류2_list += sorted(df_filtered['분류2'].dropna().unique().tolist())

    st.markdown(f"## 📊 {분류1}")
    col1, col2 = st.columns([1, 3])
    with col1: selected_분류2 = st.selectbox("🔍 분류2 선택", 분류2_list, key=f"분류2_{분류1}")
    
    df_display = df_filtered[df_filtered['분류2'] == selected_분류2].copy() if selected_분류2 != '전체' else df_filtered.copy()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.markdown(f"<div class='metric-card'><h3>{len(df_display)}</h3><p>총 채널 수</p></div>", unsafe_allow_html=True)
    with col2: st.markdown(f"<div class='metric-card'><h3>{format_korean_number(df_display['구독자'].sum())}</h3><p>총 구독자</p></div>", unsafe_allow_html=True)
    with col3: st.markdown(f"<div class='metric-card'><h3>{format_korean_number(df_display['조회수'].sum())}</h3><p>총 조회수</p></div>", unsafe_allow_html=True)
    with col4: st.markdown(f"<div class='metric-card'><h3>{format_korean_number(df_display['최근 30개 토탈'].sum())}</h3><p>최근 30개 토탈</p></div>", unsafe_allow_html=True)
    
    st.markdown("---")
    col1, col2 = st.columns([2, 1])
    with col1: search_query = st.text_input("🔍 채널명 검색", key=f"search_{분류1}")
    with col2: sort_by = st.selectbox("정렬 기준", ['최근 30개 토탈', '최근 20개 토탈', '최근 10개 토탈', '구독자', '조회수'], key=f"sort_{분류1}")
    
    if search_query: df_display = df_display[df_display['채널명'].str.contains(search_query, case=False, na=False)]
    df_display = df_display.sort_values(by=[sort_by, '채널명'], ascending=[False, True])
    
    display_columns = [col for col in ['채널명', 'URL', '국가', '분류2', '구독자', '동영상', '조회수', '최근 30개 토탈'] if col in df_display.columns]
    df_fmt = df_display[display_columns].copy()
    for col in df_fmt.columns:
        if df_fmt[col].dtype in ['int64', 'float64']: df_fmt[col] = df_fmt[col].apply(format_korean_number)
        
    st.markdown(f"### 📋 채널 리스트 (총 {len(df_display)}개)")
    st.dataframe(df_fmt, use_container_width=True, height=500)

# -------------------------------------------------------------
# [수정] 순서 설정 (엑셀/표 스타일 적용)
# -------------------------------------------------------------
def show_settings():
    st.markdown("## ⚙️ 순서 설정")
    df = load_data()
    if df.empty: return
    
    if 'page_order' not in st.session_state:
        with st.spinner("설정 불러오는 중..."):
            saved_order = load_config_from_sheet()
            if saved_order:
                st.session_state.page_order = sync_order_with_data(saved_order, df)
                st.toast("✅ 설정 로드 완료!")
            else:
                st.session_state.page_order = sync_order_with_data({'분류1_순서': [], '분류2_순서': {}}, df)

    tab1, tab2, tab3 = st.tabs(["📂 분류1 순서", "📁 분류2 순서", "💾 저장"])

    # --- 탭 1: 분류1 ---
    with tab1:
        st.info("💡 카드를 드래그하여 순서를 변경하세요. 번호는 고정되어 있습니다.")
        
        current_list = st.session_state.page_order['분류1_순서']
        
        # 5열 그리드
        chunked_list = chunk_list(current_list, 5) 
        sortable_data = [{'header': '', 'items': chunk} for chunk in chunked_list]
        
        # key를 변경하여 컴포넌트 강제 리로드 (스타일 즉시 적용)
        sorted_data = sort_items(
            sortable_data,
            multi_containers=True,
            direction='vertical',
            key='sortable_cat1_excel_v4'
        )
        
        new_order = [item for container in sorted_data for item in container['items']]
        
        if new_order != current_list:
            st.session_state.page_order['분류1_순서'] = new_order
            st.rerun()

    # --- 탭 2: 분류2 ---
    with tab2:
        col_sel, col_sort = st.columns([1, 3])
        
        with col_sel:
            st.markdown("##### 대분류 선택")
            selected_cat1 = st.radio("목록", st.session_state.page_order['분류1_순서'], key="cat2_sel")
            
        with col_sort:
            st.markdown(f"##### '{selected_cat1}'의 분류2 순서")
            
            if selected_cat1 not in st.session_state.page_order['분류2_순서']:
                 st.session_state.page_order = sync_order_with_data(st.session_state.page_order, df)
            
            current_sub = st.session_state.page_order['분류2_순서'].get(selected_cat1, ['전체'])
            
            # 4열 그리드
            chunked_sub = chunk_list(current_sub, 4) 
            sortable_sub_data = [{'header': '', 'items': chunk} for chunk in chunked_sub]
            
            # key를 변경하여 컴포넌트 강제 리로드
            sorted_sub_data = sort_items(
                sortable_sub_data,
                multi_containers=True,
                direction='vertical',
                key=f'sortable_cat2_{selected_cat1}_excel_v4'
            )
            
            new_sub_order = [item for container in sorted_sub_data for item in container['items']]
            
            if new_sub_order != current_sub:
                st.session_state.page_order['분류2_순서'][selected_cat1] = new_sub_order
                st.rerun()

    # --- 탭 3: 저장 ---
    with tab3:
        st.markdown("### 💾 설정 저장")
        st.info("변경된 순서를 구글 시트에 영구적으로 저장합니다.")
        
        if st.button("💾 구글 시트에 저장하기", type="primary", use_container_width=True):
            with st.spinner("저장 중..."):
                success = save_config_to_sheet(st.session_state.page_order)
                if success:
                    st.success("✅ 저장이 완료되었습니다!")
                    st.cache_data.clear()
                else:
                    st.error("❌ 저장 실패")
        
        st.markdown("---")
        if st.button("🔄 기본 순서로 초기화 (알파벳순)", use_container_width=True):
            st.session_state.page_order = sync_order_with_data({'분류1_순서': [], '분류2_순서': {}}, df)
            st.rerun()

def main():
    if 'page' not in st.session_state: st.session_state.page = "dashboard"
    show_navigation()
    st.markdown("---")
    
    if 'page_order' not in st.session_state:
        df = load_data()
        saved_order = load_config_from_sheet()
        if saved_order:
            st.session_state.page_order = sync_order_with_data(saved_order, df)
        else:
            st.session_state.page_order = sync_order_with_data({'분류1_순서': [], '분류2_순서': {}}, df)

    if st.session_state.page == "dashboard": show_dashboard()
    elif st.session_state.page == "settings": show_settings()
    st.markdown("---")
    st.markdown(f"*Update: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

if __name__ == "__main__":
    main()
