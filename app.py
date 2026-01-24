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
    .sortable-item:hover::before {
        background-color: #e0e0e0 !important;
        color: #333 !important;
        border-right-color: #667eea !important;
    }

    /* 헤더 숨기기 */
    .sortable-container-header { display: none !important; }
    
    /* 네비게이션 버튼 */
    .nav-button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.75rem 1.5rem;
        border-radius: 10px;
        text-decoration: none;
        font-weight: bold;
    }
    
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
        text-align: left;
    }
    table th {
        padding: 12px;
        font-weight: bold;
        border: 1px solid #ddd;
        text-align: center;
    }
    table td {
        padding: 10px;
        border: 1px solid #ddd;
        text-align: center;
    }
    table tbody tr:nth-child(even) {
        background-color: #f9f9f9;
    }
    table tbody tr:hover {
        background-color: #f0f0ff;
    }
    
    /* URL 링크 스타일 */
    table a {
        color: #1E90FF !important;
        font-weight: 600 !important;
        text-decoration: none !important;
    }
    table a:hover {
        color: #0066CC !important;
        text-decoration: underline !important;
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
    
    # 사이드바에 분류 선택
    with st.sidebar:
        st.markdown("### 📂 분류 선택")
        
        for cat in 분류1_list:
            is_active = (st.session_state.selected_분류1 == cat)
            if st.button(
                cat, 
                key=f"sidebar_btn_{cat}", 
                use_container_width=True,
                type="primary" if is_active else "secondary"
            ):
                st.session_state.selected_분류1 = cat
                st.rerun()
    
    # 선택된 분류1 데이터 표시
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
    with col1: 
        selected_분류2 = st.selectbox("🔍 분류2 선택", 분류2_list, key=f"분류2_{분류1}")
    
    df_display = df_filtered[df_filtered['분류2'] == selected_분류2].copy() if selected_분류2 != '전체' else df_filtered.copy()
    
    # 검색 및 정렬
    col1, col2 = st.columns([2, 1])
    with col1: 
        search_query = st.text_input("🔍 채널명 검색", key=f"search_{분류1}")
    with col2: 
        sort_by = st.selectbox(
            "정렬 기준", 
            ['최근 30개 토탈', '최근 20개 토탈', '최근 10개 토탈', '최근 5개 토탈', '조회수'],
            key=f"sort_{분류1}"
        )
    
    if search_query: 
        df_display = df_display[df_display['채널명'].str.contains(search_query, case=False, na=False)]
    
    df_display = df_display.sort_values(by=[sort_by, '채널명'], ascending=[False, True])
    
    # 테이블 컬럼 설정
    display_columns = [
        col for col in [
            '채널명', 'URL', '국가', '분류2', 
            '동영상', '조회수',
            '최근 5개 토탈', '최근 10개 토탈', '최근 20개 토탈', '최근 30개 토탈'
        ] 
        if col in df_display.columns
    ]
    
    df_fmt = df_display[display_columns].copy()
    
    # 숫자 포맷팅 (URL 제외)
    for col in df_fmt.columns:
        if col != 'URL' and df_fmt[col].dtype in ['int64', 'float64']: 
            df_fmt[col] = df_fmt[col].apply(format_korean_number)
    
    # URL을 파란색 '보기' 링크로 변환
    if 'URL' in df_fmt.columns:
        df_fmt['URL'] = df_fmt['URL'].apply(
            lambda x: f'<a href="{x}" target="_blank" style="color: #1E90FF; font-weight: 600; text-decoration: none;">보기</a>' 
            if pd.notna(x) and x != '' else ''
        )
    
    # ========== 페이지네이션 ==========
    total_rows = len(df_fmt)
    
    # 페이지 크기 선택 (상단에 배치)
    col1, col2, col3 = st.columns([1, 2, 2])
    with col1:
        rows_per_page = st.selectbox(
            "페이지당 표시",
            options=[50, 100, 200, 500],
            index=0,
            key=f"rows_per_page_{분류1}"
        )
    
    total_pages = (total_rows + rows_per_page - 1) // rows_per_page
    
    # 페이지 번호 초기화
    page_key = f"page_{분류1}_{selected_분류2}"
    if page_key not in st.session_state:
        st.session_state[page_key] = 1
    
    # 페이지 크기 변경 시 1페이지로 리셋
    page_size_key = f"prev_page_size_{분류1}"
    if page_size_key not in st.session_state:
        st.session_state[page_size_key] = rows_per_page
    
    if st.session_state[page_size_key] != rows_per_page:
        st.session_state[page_key] = 1
        st.session_state[page_size_key] = rows_per_page
    
    current_page = st.session_state[page_key]
    
    # 페이지가 범위를 벗어나면 조정
    if current_page > total_pages:
        current_page = total_pages
        st.session_state[page_key] = total_pages
    
    # 페이지 범위 계산
    start_idx = (current_page - 1) * rows_per_page
    end_idx = min(start_idx + rows_per_page, total_rows)
    
    df_page = df_fmt.iloc[start_idx:end_idx]
    
    # 헤더와 페이지 정보
    st.markdown(f"### 📋 채널 리스트 (총 {total_rows}개 | {current_page}/{total_pages} 페이지)")
    
    # 테이블 표시
    st.markdown(
        df_page.to_html(escape=False, index=False),
        unsafe_allow_html=True
    )
    
    # 페이지네이션 컨트롤
    st.markdown("---")
    
    col1, col2, col3, col4, col5, col6 = st.columns([1, 1, 1.5, 1, 1, 1])
    
    with col1:
        if st.button("⏮️ 처음", key=f"first_{분류1}", disabled=(current_page == 1)):
            st.session_state[page_key] = 1
            st.rerun()
    
    with col2:
        if st.button("◀️ 이전", key=f"prev_{분류1}", disabled=(current_page == 1)):
            st.session_state[page_key] = max(1, current_page - 1)
            st.rerun()
    
    with col3:
        # 페이지 번호 입력
        col_input1, col_input2 = st.columns([2, 1])
        with col_input1:
            new_page = st.number_input(
                "페이지 이동",
                min_value=1,
                max_value=total_pages,
                value=current_page,
                step=1,
                key=f"page_input_{분류1}",
                label_visibility="collapsed"
            )
        with col_input2:
            if st.button("이동", key=f"go_{분류1}"):
                if new_page != current_page:
                    st.session_state[page_key] = new_page
                    st.rerun()
    
    with col4:
        if st.button("▶️ 다음", key=f"next_{분류1}", disabled=(current_page == total_pages)):
            st.session_state[page_key] = min(total_pages, current_page + 1)
            st.rerun()
    
    with col5:
        if st.button("⏭️ 마지막", key=f"last_{분류1}", disabled=(current_page == total_pages)):
            st.session_state[page_key] = total_pages
            st.rerun()
    
    with col6:
        # CSV 다운로드 (현재 페이지)
        csv = df_page.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 CSV",
            data=csv,
            file_name=f"youtube_{분류1}_page{current_page}.csv",
            mime="text/csv",
            key=f"download_{분류1}"
        )
    
    # 현재 표시 범위 정보
    st.info(f"📄 {start_idx + 1}~{end_idx}번째 채널 표시 중 (전체 {total_rows}개 | 페이지당 {rows_per_page}개)")

# -------------------------------------------------------------
# 순서 설정
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

    # 탭 1: 분류1
    with tab1:
        st.info("💡 카드를 드래그하여 순서를 변경하세요.")
        
        current_list = st.session_state.page_order['분류1_순서']
        
        chunked_list = chunk_list(current_list, 5) 
        sortable_data = [{'header': '', 'items': chunk} for chunk in chunked_list]
        
        sorted_data = sort_items(
            sortable_data,
            multi_containers=True,
            direction='vertical',
            key='sortable_cat1_v5'
        )
        
        new_order = [item for container in sorted_data for item in container['items']]
        
        if new_order != current_list:
            st.session_state.page_order['분류1_순서'] = new_order
            st.rerun()

    # 탭 2: 분류2
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
            
            chunked_sub = chunk_list(current_sub, 4) 
            sortable_sub_data = [{'header': '', 'items': chunk} for chunk in chunked_sub]
            
            sorted_sub_data = sort_items(
                sortable_sub_data,
                multi_containers=True,
                direction='vertical',
                key=f'sortable_cat2_{selected_cat1}_v5'
            )
            
            new_sub_order = [item for container in sorted_sub_data for item in container['items']]
            
            if new_sub_order != current_sub:
                st.session_state.page_order['분류2_순서'][selected_cat1] = new_sub_order
                st.rerun()

    # 탭 3: 저장
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
    if 'page' not in st.session_state: 
        st.session_state.page = "dashboard"
    
    show_navigation()
    st.markdown("---")
    
    if 'page_order' not in st.session_state:
        df = load_data()
        saved_order = load_config_from_sheet()
        if saved_order:
            st.session_state.page_order = sync_order_with_data(saved_order, df)
        else:
            st.session_state.page_order = sync_order_with_data({'분류1_순서': [], '분류2_순서': {}}, df)

    if st.session_state.page == "dashboard": 
        show_dashboard()
    elif st.session_state.page == "settings": 
        show_settings()
    
    st.markdown("---")
    st.markdown(f"*Update: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

if __name__ == "__main__":
    main()
