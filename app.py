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

# --- 커스텀 CSS (기존 유지) ---
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
    .cat-helper { 
        background-color: #f0f2f6; 
        padding: 10px; 
        border-radius: 5px; 
        border-left: 5px solid #ff4b4b;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# --- 구글 시트 연결 및 데이터 로드 (기존 유지) ---
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
        df['gs_row_index'] = range(2, len(df) + 2)
        numeric_columns = ['구독자', '동영상', '조회수', '최근 5개 토탈', '최근 10개 토탈', '최근 20개 토탈', '최근 30개 토탈']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"데이터 로드 실패: {str(e)}")
        return pd.DataFrame()

def update_gs_rows(edited_df, original_df):
    try:
        client = get_gspread_client()
        sheet = client.open("유튜브보물창고_테스트").sheet1
        headers = sheet.row_values(1)
        col_map = {name: i+1 for i, name in enumerate(headers)}
        count = 0
        for idx, row in edited_df.iterrows():
            orig_row = original_df[original_df['gs_row_index'] == row['gs_row_index']].iloc[0]
            for field in ['분류1', '분류2', '메모']:
                if str(row[field]) != str(orig_row[field]):
                    sheet.update_cell(int(row['gs_row_index']), col_map[field], str(row[field]))
                    count += 1
        return count
    except Exception as e:
        st.error(f"업데이트 오류: {e}")
        return -1

# --- 설정 및 동기화 (기존 유지) ---
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
    return saved_order

# --- 화면 구성 함수 ---
def show_navigation():
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    with col1:
        if st.button("🎬 YouTube 보물창고", key="logo_home"):
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
            st.rerun()

def show_dashboard():
    df = load_data()
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
    # 분류 관계 매핑 생성
    cat_relationship = df.groupby('분류1')['분류2'].unique().apply(list).to_dict()
    
    df_filtered = df[df['분류1'] == 분류1].copy()
    분류2_list = st.session_state.page_order['분류2_순서'].get(분류1, ['전체'])
    
    st.markdown(f"## 📊 {분류1}")
    
    # 분류2 선택 버튼들
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

    # --- 🛠️ 분류 수정 가이드 및 추가 도구 (개선된 부분) ---
    with st.expander("🛠️ 분류 체계 관리 (신규 분류 추가 및 관계 확인)"):
        st.markdown(f"**현재 `{분류1}`에 속한 유효한 분류2:** " + ", ".join([f"`{c}`" for c in cat_relationship.get(분류1, [])]))
        
        st.markdown("---")
        st.info("💡 아래에서 새로운 분류 관계를 정의하면 표의 선택 옵션에 즉시 나타납니다.")
        c1, c2, c3 = st.columns([2, 2, 1])
        
        # 신규 분류1 입력 또는 선택
        existing_cat1 = sorted(list(cat_relationship.keys()))
        input_cat1 = c1.selectbox("분류1 선택/입력", ["+ 직접 입력"] + existing_cat1)
        if input_cat1 == "+ 직접 입력":
            final_cat1 = c1.text_input("새 분류1 명칭", key="new_c1")
        else:
            final_cat1 = input_cat1
            
        # 신규 분류2 입력 또는 선택 (분류1에 종속적)
        rel_cat2 = cat_relationship.get(final_cat1, []) if final_cat1 in cat_relationship else []
        input_cat2 = c2.selectbox(f"'{final_cat1}'의 분류2 선택/입력", ["+ 직접 입력"] + sorted(rel_cat2))
        if input_cat2 == "+ 직접 입력":
            final_cat2 = c2.text_input("새 분류2 명칭", key="new_c2")
        else:
            final_cat2 = input_cat2
            
        if c3.button("분류 체계 반영", use_container_width=True):
            if final_cat1 and final_cat2:
                if 'extra_cats' not in st.session_state: st.session_state.extra_cats = []
                st.session_state.extra_cats.append({'분류1': final_cat1, '분류2': final_cat2})
                st.success(f"매핑 추가됨: {final_cat1} > {final_cat2}")
                st.rerun()

    # 검색 및 정렬 (기존 유지)
    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([2, 1, 1])
    with ctrl_col1:
        search_query = st.text_input("🔍 채널명 검색", key=f"search_{분류1}")
    with ctrl_col2:
        sort_by = st.selectbox("정렬 기준", ['최근 30개 토탈', '최근 20개 토탈', '최근 10개 토탈', '최근 5개 토탈', '조회수', '사용자 지정'], key=f"sort_{분류1}")
    
    if search_query: 
        df_display = df_display[df_display['채널명'].str.contains(search_query, case=False, na=False)]
    
    if sort_by == '사용자 지정':
        channel_order_key = f"{분류1}_{selected_분류2}"
        if '채널_순서' in st.session_state.page_order and channel_order_key in st.session_state.page_order['채널_순서']:
            saved_order = st.session_state.page_order['채널_순서'][channel_order_key]
            current_names = df_display['채널명'].tolist()
            ordered = [n for n in saved_order if n in current_names]
            ordered += [n for n in current_names if n not in ordered]
            df_display = df_display.set_index('채널명').loc[ordered].reset_index()
    else:
        df_display = df_display.sort_values(by=[sort_by, '채널명'], ascending=[False, True])
    
    # 데이터 에디터 옵션 준비
    all_cat1 = sorted(list(set(df['분류1'].unique().tolist() + [x['분류1'] for x in st.session_state.get('extra_cats', [])])))
    all_cat2 = sorted(list(set(df['분류2'].unique().tolist() + [x['분류2'] for x in st.session_state.get('extra_cats', [])])))

    # 현재 분류1에 속하는 분류2를 드롭다운 리스트 상단으로 올리기 (사용자 편의성)
    current_belonging_cat2 = sorted(cat_relationship.get(분류1, []))
    other_cat2 = [c for c in all_cat2 if c not in current_belonging_cat2]
    prioritized_cat2 = current_belonging_cat2 + other_cat2

    st.markdown(f"### 📋 채널 리스트 (총 {len(df_display)}개)")
    st.caption(f"※ 분류2 수정 시 `{분류1}`에 해당하는 항목({', '.join(current_belonging_cat2)})을 우선 선택하세요.")
    
    display_columns = ['채널명', '분류1', '분류2', '메모', '운영기간', '동영상', '조회수', '최근 5개 토탈', '최근 10개 토탈', '최근 20개 토탈', '최근 30개 토탈', 'URL', 'gs_row_index']
    df_to_edit = df_display[[c for c in display_columns if c in df_display.columns]].copy()

    edited_df = st.data_editor(
        df_to_edit,
        use_container_width=True,
        height=600,
        column_config={
            "URL": st.column_config.LinkColumn("링크", display_text="보러가기"),
            "gs_row_index": None,
            "채널명": st.column_config.TextColumn(disabled=True),
            "분류1": st.column_config.SelectboxColumn("분류1", options=all_cat1, required=True),
            "분류2": st.column_config.SelectboxColumn("분류2", options=prioritized_cat2, required=True),
            "메모": st.column_config.TextColumn("메모", width="large"),
        },
        hide_index=True,
        key=f"editor_{분류1}_{selected_분류2}"
    )

    with ctrl_col3:
        st.write("") 
        if st.button("💾 변경사항 시트에 저장", type="primary", use_container_width=True):
            # 저장 전 검증 (선택 사항: 분류1-분류2 매핑 확인 로직을 넣을 수 있음)
            with st.spinner("구글 시트 업데이트 중..."):
                update_count = update_gs_rows(edited_df, df_to_edit)
                if update_count > 0:
                    st.success(f"✅ {update_count}개 수정 완료!")
                    st.cache_data.clear()
                    if 'extra_cats' in st.session_state: st.session_state.extra_cats = []
                    st.rerun()
                elif update_count == 0:
                    st.info("변경사항 없음")
                else:
                    st.error("저장 실패")

# --- 설정 화면 (기존 유지) ---
def show_settings():
    st.markdown("## ⚙️ 순서 설정")
    df = load_data()
    if df.empty: return
    tab1, tab2, tab3 = st.tabs(["📂 분류1 순서", "📁 분류2 순서", "💾 저장"])
    with tab1:
        current_list = st.session_state.page_order['분류1_순서']
        sorted_data = sort_items([{'header': '', 'items': chunk} for chunk in chunk_list(current_list, 5)], multi_containers=True, direction='vertical', key='sort_cat1_v5')
        new_order = [item for container in sorted_data for item in container['items']]
        if new_order != current_list:
            st.session_state.page_order['분류1_순서'] = new_order
            st.rerun()
    with tab2:
        selected_cat1 = st.radio("대분류", st.session_state.page_order['분류1_순서'], key="set_cat2_sel")
        current_sub = st.session_state.page_order['분류2_순서'].get(selected_cat1, ['전체'])
        sorted_sub = sort_items([{'header': '', 'items': chunk} for chunk in chunk_list(current_sub, 4)], multi_containers=True, direction='vertical', key=f'sort_cat2_{selected_cat1}_v5')
        new_sub = [item for container in sorted_sub for item in container['items']]
        if new_sub != current_sub:
            st.session_state.page_order['분류2_순서'][selected_cat1] = new_sub
            st.rerun()
    with tab3:
        if st.button("💾 구글 시트에 순서 설정 저장", type="primary", use_container_width=True):
            if save_config_to_sheet(st.session_state.page_order):
                st.success("✅ 저장 완료!")
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
    if st.session_state.page == "dashboard": show_dashboard()
    else: show_settings()
    st.markdown(f"<p style='text-align:right; color:gray;'>Update: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
