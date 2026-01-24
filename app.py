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
    initial_sidebar_state="expanded"
)

# 커스텀 CSS (기존 유지)
st.markdown("""
<style>
    button[key="logo_home"] {
        border: none !important;
        background: transparent !important;
        font-size: 2.5rem !important;
        font-weight: 800 !important;
        padding: 0 !important;
        color: #31333F !important;
        text-align: left !important;
        box-shadow: none !important;
        display: flex !important;
        align-items: center !important;
    }
    button[key="logo_home"]:hover { color: #FF0000 !important; background: transparent !important; }
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
</style>
""", unsafe_allow_html=True)

# 숫자 포맷 함수
def format_korean_number(num):
    if pd.isna(num) or num == 0: return "0"
    try:
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
    except: return str(num)

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

# 구글 시트 연결 및 데이터 로드
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

# [추가] 수정한 데이터를 구글 시트에 저장하는 함수
def save_data_to_google_sheet(full_df):
    try:
        client = get_gspread_client()
        sheet = client.open("유튜브보물창고_테스트").sheet1
        # 데이터프레임을 리스트 형태로 변환 (헤더 포함)
        data_to_save = [full_df.columns.values.tolist()] + full_df.fillna("").values.tolist()
        sheet.update('A1', data_to_save)
        return True
    except Exception as e:
        st.error(f"구글 시트 저장 중 오류 발생: {e}")
        return False

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
        json_str = json.dumps(order_data, ensure_ascii=False)
        worksheet.update_acell('A1', json_str)
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
    if '채널_순서' not in saved_order: saved_order['채널_순서'] = {}
    return saved_order

# 네비게이션
def show_navigation():
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    with col1:
        if st.button("🎬 YouTube 보물창고", key="logo_home", use_container_width=False):
            st.session_state.page = "dashboard"
            st.rerun()
    with col2:
        if st.button("🏠 대시보드", use_container_width=True):
            st.session_state.page = "dashboard"
            st.rerun()
    with col3:
        if st.button("⚙️ 순서 설정", use_container_width=True):
            st.session_state.page = "settings"
            st.rerun()
    with col4:
        if st.button("🔄 새로고침", use_container_width=True):
            st.cache_data.clear()
            if 'raw_data' in st.session_state: del st.session_state.raw_data
            st.rerun()

def show_dashboard():
    # 데이터 로드 및 세션 상태 저장
    if 'raw_data' not in st.session_state:
        st.session_state.raw_data = load_data()
    
    df = st.session_state.raw_data
    if df.empty: return
    
    if 'page_order' not in st.session_state:
        saved_order = load_config_from_sheet()
        st.session_state.page_order = sync_order_with_data(saved_order if saved_order else {'분류1_순서': [], '분류2_순서': {}, '채널_순서': {}}, df)

    분류1_list = st.session_state.page_order['분류1_순서']
    if 'selected_분류1' not in st.session_state:
        st.session_state.selected_분류1 = 분류1_list[0] if 분류1_list else None
    
    with st.sidebar:
        st.markdown("## 📂 분류 선택")
        for cat in 분류1_list:
            is_active = (st.session_state.selected_분류1 == cat)
            if st.button(cat, key=f"side_{cat}", use_container_width=True, type="primary" if is_active else "secondary"):
                st.session_state.selected_분류1 = cat
                st.rerun()
    
    if st.session_state.selected_분류1:
        show_category_detail(df, st.session_state.selected_분류1)

def show_category_detail(df, 분류1):
    분류2_list = st.session_state.page_order['분류2_순서'].get(분류1, ['전체'])
    
    col_title, col_edit_toggle = st.columns([3, 1])
    with col_title: st.markdown(f"## 📊 {분류1}")
    with col_edit_toggle:
        edit_mode = st.toggle("✏️ 데이터 수정 모드", key=f"edit_mode_{분류1}")

    if f'selected_분류2_{분류1}' not in st.session_state:
        st.session_state[f'selected_분류2_{분류1}'] = '전체'
    
    # 분류2 버튼
    buttons_per_row = 8
    num_rows = (len(분류2_list) + buttons_per_row - 1) // buttons_per_row
    for row in range(num_rows):
        cols = st.columns(buttons_per_row)
        for idx, col in enumerate(cols):
            item_idx = row * buttons_per_row + idx
            if item_idx < len(분류2_list):
                cat2 = 분류2_list[item_idx]
                is_active = (st.session_state[f'selected_분류2_{분류1}'] == cat2)
                if col.button(cat2, key=f"cat2_{분류1}_{cat2}", use_container_width=True, type="primary" if is_active else "secondary"):
                    st.session_state[f'selected_분류2_{분류1}'] = cat2
                    st.rerun()
    
    selected_분류2 = st.session_state[f'selected_분류2_{분류1}']
    
    # 검색 및 정렬
    col_search, col_sort = st.columns([3, 1])
    with col_search: search_query = st.text_input("🔍 채널명 검색", key=f"search_{분류1}")
    with col_sort: sort_by = st.selectbox("정렬 기준", ['최근 30개 토탈', '최근 20개 토탈', '최근 10개 토탈', '최근 5개 토탈', '조회수', '사용자 지정'], key=f"sort_{분류1}")
    
    # 필터링 로직
    df_filtered = df[df['분류1'] == 분류1].copy()
    if selected_분류2 != '전체':
        df_filtered = df_filtered[df_filtered['분류2'] == selected_분류2]
    if search_query: 
        df_filtered = df_filtered[df_filtered['채널명'].str.contains(search_query, case=False, na=False)]
    
    # 정렬 로직
    channel_order_key = f"{분류1}_{selected_분류2}"
    if sort_by == '사용자 지정':
        if '채널_순서' in st.session_state.page_order and channel_order_key in st.session_state.page_order['채널_순서']:
            saved_order = st.session_state.page_order['채널_순서'][channel_order_key]
            current_names = df_filtered['채널명'].tolist()
            ordered = [n for n in saved_order if n in current_names]
            ordered += [n for n in current_names if n not in ordered]
            df_filtered = df_filtered.set_index('채널명').loc[ordered].reset_index()
    else:
        df_filtered = df_filtered.sort_values(by=[sort_by, '채널명'], ascending=[False, True])
    
    display_columns = ['채널명', '분류2', '메모', '운영기간', '동영상', '조회수', '최근 5개 토탈', '최근 10개 토탈', '최근 20개 토탈', '최근 30개 토탈', '키워드', 'URL']
    
    st.markdown(f"### 📋 채널 리스트 (총 {len(df_filtered)}개)")

    if edit_mode:
        st.warning("⚠️ 수정 모드입니다. 셀을 더블클릭하여 수정 후 아래 [💾 변경사항 저장] 버튼을 누르세요.")
        # 수정 모드에서는 숫자 포맷을 하지 않음 (raw 데이터 유지)
        edited_df = st.data_editor(
            df_filtered[display_columns],
            use_container_width=True,
            num_rows="dynamic",
            key=f"editor_{분류1}_{selected_분류2}",
            hide_index=True
        )
        
        if st.button("💾 변경사항 구글 시트에 최종 저장", type="primary", use_container_width=True):
            # 수정된 내용을 원본 df에 반영
            for idx, row in edited_df.iterrows():
                channel_name = row['채널명']
                st.session_state.raw_data.loc[st.session_state.raw_data['채널명'] == channel_name, display_columns] = row
            
            if save_data_to_google_sheet(st.session_state.raw_data):
                st.success("✅ 구글 시트 업데이트 완료!")
                st.cache_data.clear()
                st.rerun()
    else:
        # 보기 모드 (숫자 포맷팅 적용)
        df_display = df_filtered[display_columns].copy()
        numeric_cols = ['동영상', '조회수', '최근 5개 토탈', '최근 10개 토탈', '최근 20개 토탈', '최근 30개 토탈']
        for col in numeric_cols:
            if col in df_display.columns:
                df_display[col] = df_display[col].apply(format_korean_number)
        
        st.dataframe(
            df_display,
            use_container_width=True,
            height=600,
            column_config={
                "URL": st.column_config.LinkColumn("링크", display_text="보러가기"),
                "키워드": st.column_config.TextColumn("키워드"),
                "메모": st.column_config.TextColumn("메모"),
                "운영기간": st.column_config.TextColumn("운영기간")
            },
            hide_index=True
        )

# [설정 부분은 기존과 동일]
def show_settings():
    st.markdown("## ⚙️ 순서 설정")
    if 'raw_data' not in st.session_state: st.session_state.raw_data = load_data()
    df = st.session_state.raw_data
    if df.empty: return
    tab1, tab2, tab3 = st.tabs(["📂 분류1 순서", "📁 분류2 순서", "💾 저장"])
    with tab1:
        st.info("💡 카드를 드래그하여 순서를 변경하세요.")
        current_list = st.session_state.page_order['분류1_순서']
        chunked = chunk_list(current_list, 5) 
        sortable_data = [{'header': '', 'items': chunk} for chunk in chunked]
        sorted_data = sort_items(sortable_data, multi_containers=True, direction='vertical', key='sort_cat1_v5')
        new_order = [item for container in sorted_data for item in container['items']]
        if new_order != current_list:
            st.session_state.page_order['분류1_순서'] = new_order
            st.rerun()
    with tab2:
        col_sel, col_sort = st.columns([1, 3])
        with col_sel: selected_cat1 = st.radio("대분류", st.session_state.page_order['분류1_순서'], key="set_cat2_sel")
        with col_sort:
            current_sub = st.session_state.page_order['분류2_순서'].get(selected_cat1, ['전체'])
            chunked_sub = chunk_list(current_sub, 4) 
            sortable_sub = [{'header': '', 'items': chunk} for chunk in chunked_sub]
            sorted_sub = sort_items(sortable_sub, multi_containers=True, direction='vertical', key=f'sort_cat2_{selected_cat1}_v5')
            new_sub = [item for container in sorted_sub for item in container['items']]
            if new_sub != current_sub:
                st.session_state.page_order['분류2_순서'][selected_cat1] = new_sub
                st.rerun()
    with tab3:
        if st.button("💾 설정(순서) 구글 시트에 저장", type="primary", use_container_width=True):
            if save_config_to_sheet(st.session_state.page_order):
                st.success("✅ 설정 저장 완료!")
        if st.button("🗑️ 모든 채널 개별 순서 초기화", use_container_width=True):
            st.session_state.page_order['채널_순서'] = {}
            st.rerun()

def main():
    if 'page' not in st.session_state: st.session_state.page = "dashboard"
    show_navigation()
    st.markdown("---")
    if st.session_state.page == "dashboard": show_dashboard()
    else: show_settings()
    st.markdown(f"<p style='text-align:right; color:gray;'>Update: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
