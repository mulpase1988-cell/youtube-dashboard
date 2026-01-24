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

# --- 유틸리티 함수 (소수점 제거 버전) ---
def format_korean_number(num):
    """숫자를 한국어 단위(억, 만) 정수로 변환"""
    if pd.isna(num) or num == 0: return "0"
    try:
        num = int(float(str(num).replace(',', '')))
        if num >= 100000000:
            return f"{num // 100000000}억"
        elif num >= 10000:
            return f"{num // 10000}만"
        else:
            return f"{num:,}"
    except:
        return str(num)

# --- 구글 시트 연결 ---
def get_gspread_client():
    credentials_dict = dict(st.secrets["gcp_service_account"])
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
    return gspread.authorize(credentials)

@st.cache_data(ttl=600)
def load_data():
    try:
        client = get_gspread_client()
        doc = client.open("유튜브보물창고_테스트")
        sheet = doc.sheet1
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        df['gs_row_index'] = range(2, len(df) + 2)
        
        numeric_columns = ['구독자', '동영상', '조회수', '최근 5개 토탈', 
                          '최근 10개 토탈', '최근 20개 토탈', '최근 30개 토탈']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0).astype(int)
        
        try:
            cat_sheet = doc.worksheet("분류관리")
            cat_data = cat_sheet.get_all_records()
            cat_df = pd.DataFrame(cat_data)
        except:
            cat_df = pd.DataFrame(columns=['분류1', '분류2'])
            
        return df, cat_df
    except Exception as e:
        st.error(f"데이터 로드 실패: {str(e)}")
        return pd.DataFrame(), pd.DataFrame()

def update_gs_rows(edited_df, original_df):
    try:
        client = get_gspread_client()
        sheet = client.open("유튜브보물창고_테스트").sheet1
        headers = sheet.row_values(1)
        col_map = {name: i+1 for i, name in enumerate(headers)}
        
        count = 0
        for idx, row in edited_df.iterrows():
            orig_row = original_df[original_df['gs_row_index'] == row['gs_row_index']].iloc[0]
            fields_to_check = ['분류1', '분류2', '메모']
            for field in fields_to_check:
                if str(row[field]) != str(orig_row[field]):
                    sheet.update_cell(int(row['gs_row_index']), col_map[field], str(row[field]))
                    count += 1
        return count
    except Exception as e:
        st.error(f"업데이트 오류: {e}")
        return -1

def save_categories_to_sheet(cat_df):
    try:
        client = get_gspread_client()
        doc = client.open("유튜브보물창고_테스트")
        try: worksheet = doc.worksheet("분류관리")
        except: worksheet = doc.add_worksheet(title="분류관리", rows=100, cols=5)
        worksheet.clear()
        data_to_save = [cat_df.columns.values.tolist()] + cat_df.values.tolist()
        worksheet.update('A1', data_to_save)
        return True
    except: return False

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

def sync_order_with_data(saved_order, df, cat_df):
    live_cat1 = set(cat_df['분류1'].dropna().unique()) if not cat_df.empty else set(df['분류1'].dropna().unique())
    current_cat1_order = saved_order.get('분류1_순서', [])
    new_cat1_order = [c for c in current_cat1_order if c in live_cat1]
    for c in sorted(list(live_cat1)):
        if c not in new_cat1_order: new_cat1_order.append(c)
    saved_order['분류1_순서'] = new_cat1_order
    
    if '분류2_순서' not in saved_order: saved_order['분류2_순서'] = {}
    for cat1 in new_cat1_order:
        if not cat_df.empty:
            live_cat2 = set(cat_df[cat_df['분류1'] == cat1]['분류2'].dropna().unique())
        else:
            live_cat2 = set(df[df['분류1'] == cat1]['분류2'].dropna().unique())
        live_cat2.add('전체')
        current_cat2_order = saved_order['분류2_순서'].get(cat1, ['전체'])
        new_cat2_order = [c for c in current_cat2_order if c in live_cat2]
        for c in sorted(list(live_cat2)):
            if c not in new_cat2_order: new_cat2_order.append(c)
        saved_order['분류2_순서'][cat1] = new_cat2_order
    return saved_order

# --- 네비게이션 ---
def show_navigation():
    col1, col2, col3, col4, col5 = st.columns([2.5, 1, 1, 1, 1])
    with col1:
        if st.button("🎬 YouTube 보물창고", key="logo_home", use_container_width=False):
            st.session_state.page = "dashboard"
            st.rerun()
    with col2:
        if st.button("🏠 대시보드", use_container_width=True):
            st.session_state.page = "dashboard"
            st.rerun()
    with col3:
        if st.button("📁 카테고리설정", use_container_width=True):
            st.session_state.page = "category_mgmt"
            st.rerun()
    with col4:
        if st.button("⚙️ 순서 설정", use_container_width=True):
            st.session_state.page = "settings"
            st.rerun()
    with col5:
        if st.button("🔄 새로고침", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

# --- 카테고리설정 페이지 ---
def show_category_management():
    st.markdown("## 📁 카테고리설정")
    df, cat_df = load_data()
    
    st.info("💡 '자동 추출' 버튼을 누르면 채널 리스트 시트에서 현재 사용 중인 카테고리-장르 조합을 모두 가져옵니다.")
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("✨ 채널 리스트에서 카테고리 자동 추출", use_container_width=True):
            if not df.empty:
                new_cat_df = df[['분류1', '분류2']].drop_duplicates().sort_values(['분류1', '분류2'])
                new_cat_df = new_cat_df[new_cat_df['분류1'] != ""]
                if save_categories_to_sheet(new_cat_df):
                    st.success("추출 완료 및 저장되었습니다!")
                    st.cache_data.clear()
                    st.rerun()
    
    with c2:
        if st.button("💾 표의 변경사항 저장", type="primary", use_container_width=True):
            if 'temp_cat_df' in st.session_state:
                if save_categories_to_sheet(st.session_state.temp_cat_df):
                    st.success("카테고리 설정 시트가 업데이트 되었습니다.")
                    st.cache_data.clear()
                    st.rerun()

    edited_cat = st.data_editor(
        cat_df,
        use_container_width=True,
        num_rows="dynamic",
        key="cat_mgmt_editor",
        column_config={
            "분류1": st.column_config.TextColumn("카테고리", required=True),
            "분류2": st.column_config.TextColumn("장르", required=True),
        }
    )
    st.session_state.temp_cat_df = edited_cat

# --- 대시보드 및 상세 페이지 ---
def show_dashboard():
    df, cat_df = load_data()
    if df.empty: return
    
    if 'page_order' not in st.session_state:
        saved_order = load_config_from_sheet()
        st.session_state.page_order = sync_order_with_data(
            saved_order if saved_order else {'분류1_순서': [], '분류2_순서': {}, '채널_순서': {}}, 
            df, cat_df
        )

    분류1_list = st.session_state.page_order['분류1_순서']
    
    # --- 국가 필터 추가 ---
    with st.sidebar:
        st.markdown("## 🌍 국가 필터")
        if '국가' in df.columns:
            country_options = ["전체"] + sorted([c for c in df['국가'].unique() if c])
            selected_country = st.selectbox("조회할 국가를 선택하세요", country_options, key="global_country_filter")
            
            # 국가 필터 적용
            if selected_country != "전체":
                df = df[df['국가'] == selected_country]
        else:
            st.warning("시트에 '국가' 컬럼이 없습니다.")
            selected_country = "전체"

        st.markdown("---")
        st.markdown("## 📂 카테고리")
        
        if 'selected_분류1' not in st.session_state:
            st.session_state.selected_분류1 = 분류1_list[0] if 분류1_list else None
            
        for cat in 분류1_list:
            # 해당 국가에 데이터가 있는 카테고리만 표시하거나 전체 표시 (여기서는 필터링된 데이터 기반 카운트 표시)
            count = len(df[df['분류1'] == cat])
            display_text = f"{cat} ({count})"
            
            is_active = (st.session_state.selected_분류1 == cat)
            if st.button(display_text, key=f"side_{cat}", use_container_width=True, type="primary" if is_active else "secondary"):
                st.session_state.selected_분류1 = cat
                st.rerun()
    
    if st.session_state.selected_분류1:
        # 필터링된 df를 상세 페이지로 전달
        show_category_detail(df, cat_df, st.session_state.selected_분류1)

def show_category_detail(df, cat_df, 분류1):
    df_filtered = df[df['분류1'] == 분류1].copy()
    
    st.markdown(f"## 📊 {분류1}")
    
    with st.expander("➕ 새 장르 추가"):
        col_input, col_btn = st.columns([3, 1])
        with col_input:
            new_sub_cat = st.text_input(f"'{분류1}' 카테고리에 추가할 장르명 입력", key=f"input_new_{분류1}")
        with col_btn:
            st.write("") 
            if st.button("장르 추가 저장", use_container_width=True, type="primary"):
                if new_sub_cat:
                    if not ((cat_df['분류1'] == 분류1) & (cat_df['분류2'] == new_sub_cat)).any():
                        new_row = pd.DataFrame({'분류1': [분류1], '분류2': [new_sub_cat]})
                        updated_cat_df = pd.concat([cat_df, new_row], ignore_index=True)
                        if save_categories_to_sheet(updated_cat_df):
                            st.success(f"장르 '{new_sub_cat}' 추가 완료!")
                            st.cache_data.clear()
                            st.rerun()
                    else:
                        st.warning("이미 존재하는 장르입니다.")
                else:
                    st.error("장르명을 입력해주세요.")

    분류2_list = st.session_state.page_order['분류2_순서'].get(분류1, ['전체'])
    
    if f'selected_분류2_{분류1}' not in st.session_state:
        st.session_state[f'selected_분류2_{분류1}'] = '전체'
    
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
    df_display = df_filtered[df_filtered['분류2'] == selected_분류2].copy() if selected_분류2 != '전체' else df_filtered.copy()
    
    st.markdown("---")
    
    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([2, 1, 1])
    with ctrl_col1:
        search_query = st.text_input("🔍 채널명 검색", key=f"search_{분류1}")
    with ctrl_col2:
        sort_by = st.selectbox("정렬 기준", ['최근 30개 토탈', '최근 20개 토탈', '최근 10개 토탈', '최근 5개 토탈', '조회수', '사용자 지정'], key=f"sort_{분류1}")
    
    if search_query: 
        df_display = df_display[df_display['채널명'].str.contains(search_query, case=False, na=False)]
    
    channel_order_key = f"{분류1}_{selected_분류2}"
    if sort_by == '사용자 지정':
        if '채널_순서' in st.session_state.page_order and channel_order_key in st.session_state.page_order['채널_순서']:
            saved_order = st.session_state.page_order['채널_순서'][channel_order_key]
            current_names = df_display['채널명'].tolist()
            ordered = [n for n in saved_order if n in current_names]
            ordered += [n for n in current_names if n not in ordered]
            df_display = df_display.set_index('채널명').loc[ordered].reset_index()
    else:
        df_display = df_display.sort_values(by=[sort_by, '채널명'], ascending=[False, True])
    
    display_columns = [
        '채널명', '국가', '분류1', '분류2', '메모', '운영기간', 
        '동영상', '조회수', '최근 5개 토탈', '최근 10개 토탈', 
        '최근 20개 토탈', '최근 30개 토탈', 'URL', 'gs_row_index'
    ]
    df_to_edit = df_display[[c for c in display_columns if c in df_display.columns]].copy()

    # 표시 데이터 포맷팅
    format_cols = ['조회수', '최근 5개 토탈', '최근 10개 토탈', '최근 20개 토탈', '최근 30개 토탈']
    for col in format_cols:
        if col in df_to_edit.columns:
            df_to_edit[col] = df_to_edit[col].apply(format_korean_number)

    all_cat1_options = sorted(list(cat_df['분류1'].unique())) if not cat_df.empty else sorted(list(df['분류1'].unique()))
    allowed_cat2_options = sorted(list(cat_df[cat_df['분류1'] == 분류1]['분류2'].unique()))

    st.markdown(f"### 📋 채널 리스트 (총 {len(df_display)}개)")
    
    edited_df = st.data_editor(
        df_to_edit,
        use_container_width=True,
        height=600,
        column_config={
            "URL": st.column_config.LinkColumn("링크", display_text="보기"),
            "gs_row_index": None,
            "국가": st.column_config.TextColumn("국가", disabled=True),
            "분류1": st.column_config.SelectboxColumn("카테고리", options=all_cat1_options, required=True),
            "분류2": st.column_config.SelectboxColumn("장르", options=allowed_cat2_options, required=True),
            "동영상": st.column_config.NumberColumn(disabled=True),
            "조회수": st.column_config.TextColumn("조회수", disabled=True),
            "최근 5개 토탈": st.column_config.TextColumn("최근 5개 토탈", disabled=True),
            "최근 10개 토탈": st.column_config.TextColumn("최근 10개 토탈", disabled=True),
            "최근 20개 토탈": st.column_config.TextColumn("최근 20개 토탈", disabled=True),
            "최근 30개 토탈": st.column_config.TextColumn("최근 30개 토탈", disabled=True),
            "채널명": st.column_config.TextColumn(disabled=True),
            "메모": st.column_config.TextColumn("메모", width="medium"), 
        },
        hide_index=True,
        key=f"editor_{분류1}_{selected_분류2}"
    )

    with ctrl_col3:
        st.write("") 
        if st.button("💾 변경사항 시트에 저장", type="primary", use_container_width=True):
            with st.spinner("구글 시트 업데이트 중..."):
                update_count = update_gs_rows(edited_df, df_display)
                if update_count > 0:
                    st.success(f"✅ {update_count}개의 항목이 수정되었습니다.")
                    st.cache_data.clear()
                    st.rerun()
                elif update_count == 0:
                    st.info("변경사항이 없습니다.")
                else:
                    st.error("저장에 실패했습니다.")

# --- 순서 설정 페이지 ---
def show_settings():
    st.markdown("## ⚙️ 순서 설정")
    df, cat_df = load_data()
    if df.empty: return
    
    tab1, tab2, tab3 = st.tabs(["📂 카테고리 순서", "📁 장르 순서", "💾 저장"])

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
        with col_sel:
            selected_cat1 = st.radio("카테고리", st.session_state.page_order['분류1_순서'], key="set_cat2_sel")
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
        if st.button("💾 구글 시트에 순서 설정 저장", type="primary", use_container_width=True):
            if save_config_to_sheet(st.session_state.page_order):
                st.success("✅ 순서 설정 저장 완료!")
                st.cache_data.clear()

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

def main():
    if 'page' not in st.session_state: st.session_state.page = "dashboard"
    show_navigation()
    st.markdown("---")
    
    if st.session_state.page == "dashboard":
        show_dashboard()
    elif st.session_state.page == "category_mgmt":
        show_category_management()
    elif st.session_state.page == "settings":
        show_settings()
        
    st.markdown(f"<p style='text-align:right; color:gray;'>Update: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
