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
    /* 전역 스타일 */
    .main { padding: 0rem 1rem; }
    
    /* 네비게이션 버튼 */
    .nav-button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.75rem 1.5rem;
        border: none;
        border-radius: 10px;
        font-weight: bold;
        text-decoration: none;
    }
    
    /* 메트릭 카드 */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-card h3 { font-size: 2rem; margin: 0; font-weight: bold; }
    .metric-card p { font-size: 0.9rem; margin: 0.5rem 0 0 0; opacity: 0.9; }
    
    /* 분류 버튼 */
    .category-btn {
        padding: 0.75rem 1.5rem;
        border: 2px solid #667eea;
        border-radius: 25px;
        background: white;
        color: #667eea;
        font-weight: bold;
        cursor: pointer;
        transition: all 0.3s ease;
        text-align: center;
    }
    .category-btn:hover {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }

    /* Sortable 아이템 스타일 */
    .sortable-item {
        background-color: white !important;
        border: 1px solid #ddd !important;
        color: #333 !important;
        border-radius: 8px !important;
        padding: 10px !important;
        margin-bottom: 5px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
        font-weight: 500 !important;
        cursor: grab !important;
        text-align: center !important;
        font-size: 14px !important;
    }
    
    /* Sortable 컨테이너 헤더 숨기기 (깔끔하게 보이게) */
    .sortable-container-header {
        display: none !important;
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

# 리스트를 N개의 열로 나누는 헬퍼 함수
def chunk_list(data, num_chunks):
    if not data:
        return [[] for _ in range(num_chunks)]
    avg = len(data) / float(num_chunks)
    chunks = []
    last = 0.0
    for _ in range(num_chunks):
        next_val = last + avg
        chunks.append(data[int(last):int(next_val)])
        last = next_val
    return chunks

# 구글 시트 연결
@st.cache_data(ttl=600)
def load_data():
    try:
        credentials_dict = dict(st.secrets["gcp_service_account"])
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
        client = gspread.authorize(credentials)
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

# 네비게이션
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

# 대시보드
def show_dashboard():
    df = load_data()
    if df.empty: return
    
    분류1_list = st.session_state.page_order.get('분류1_순서', sorted(df['분류1'].dropna().unique().tolist())) if 'page_order' in st.session_state else sorted(df['분류1'].dropna().unique().tolist())
    
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

# 상세 페이지
def show_category_detail(df, 분류1):
    df_filtered = df[df['분류1'] == 분류1].copy()
    if df_filtered.empty: return

    분류2_list = ['전체']
    if 'page_order' in st.session_state and 분류1 in st.session_state.page_order['분류2_순서']:
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
# [수정됨] 순서 설정 (오류 수정: 딕셔너리 구조 적용)
# -------------------------------------------------------------
def show_settings():
    st.markdown("## ⚙️ 순서 설정")
    df = load_data()
    if df.empty: return
    
    if 'page_order' not in st.session_state:
        st.session_state.page_order = {
            '분류1_순서': sorted(df['분류1'].dropna().unique().tolist()),
            '분류2_순서': {}
        }
        for cat1 in st.session_state.page_order['분류1_순서']:
            df_cat = df[df['분류1'] == cat1]
            st.session_state.page_order['분류2_순서'][cat1] = ['전체'] + sorted(df_cat['분류2'].dropna().unique().tolist())

    tab1, tab2, tab3 = st.tabs(["📂 분류1 순서", "📁 분류2 순서", "💾 저장"])

    # --- 탭 1: 분류1 (그리드 스타일) ---
    with tab1:
        st.info("💡 카드를 드래그하여 순서를 변경하세요. (왼쪽 위 → 오른쪽 아래 순서로 저장됩니다)")
        
        current_list = st.session_state.page_order['분류1_순서']
        
        # 1. 리스트 청크 나누기
        cols_count = 5 
        chunked_list = chunk_list(current_list, cols_count)
        
        # 2. [중요] 라이브러리가 요구하는 dict 형식으로 변환 ({header:..., items:...})
        sortable_data = [
            {'header': '', 'items': chunk} 
            for chunk in chunked_list
        ]
        
        # 3. Sortable 컴포넌트 호출
        sorted_data = sort_items(
            sortable_data,
            multi_containers=True,
            direction='vertical',
            key='sortable_cat1_grid_v2'
        )
        
        # 4. 결과 복원 (Flatten)
        # sorted_data는 다시 [{'header':..., 'items':...}, ...] 형태로 돌아옴
        new_order = [item for container in sorted_data for item in container['items']]
        
        if new_order != current_list:
            st.session_state.page_order['분류1_순서'] = new_order
            st.rerun()

    # --- 탭 2: 분류2 (그리드 스타일) ---
    with tab2:
        col_sel, col_sort = st.columns([1, 3])
        
        with col_sel:
            st.markdown("##### 대분류 선택")
            selected_cat1 = st.radio("목록", st.session_state.page_order['분류1_순서'], key="cat2_sel")
            
        with col_sort:
            st.markdown(f"##### '{selected_cat1}'의 분류2 순서")
            
            if selected_cat1 not in st.session_state.page_order['분류2_순서']:
                 df_cat = df[df['분류1'] == selected_cat1]
                 st.session_state.page_order['분류2_순서'][selected_cat1] = ['전체'] + sorted(df_cat['분류2'].dropna().unique().tolist())
            
            current_sub = st.session_state.page_order['분류2_순서'][selected_cat1]
            
            # 1. 리스트 청크
            chunked_sub = chunk_list(current_sub, 4)
            
            # 2. Dict 형식 변환
            sortable_sub_data = [
                {'header': '', 'items': chunk} 
                for chunk in chunked_sub
            ]
            
            # 3. Sortable 호출
            sorted_sub_data = sort_items(
                sortable_sub_data,
                multi_containers=True,
                direction='vertical',
                key=f'sortable_cat2_{selected_cat1}_v2'
            )
            
            # 4. 결과 복원
            new_sub_order = [item for container in sorted_sub_data for item in container['items']]
            
            if new_sub_order != current_sub:
                st.session_state.page_order['분류2_순서'][selected_cat1] = new_sub_order
                st.rerun()

    with tab3:
        if st.button("💾 최종 저장", type="primary", use_container_width=True):
            st.success("저장되었습니다!")
        
        if st.button("🔄 초기화", use_container_width=True):
            st.session_state.page_order = {
                '분류1_순서': sorted(df['분류1'].dropna().unique().tolist()),
                '분류2_순서': {}
            }
            for cat1 in st.session_state.page_order['분류1_순서']:
                df_cat = df[df['분류1'] == cat1]
                st.session_state.page_order['분류2_순서'][cat1] = ['전체'] + sorted(df_cat['분류2'].dropna().unique().tolist())
            st.rerun()

def main():
    if 'page' not in st.session_state: st.session_state.page = "dashboard"
    show_navigation()
    st.markdown("---")
    if st.session_state.page == "dashboard": show_dashboard()
    elif st.session_state.page == "settings": show_settings()
    st.markdown("---")
    st.markdown(f"*Update: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

if __name__ == "__main__":
    main()
