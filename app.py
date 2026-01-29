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

# 커스텀 CSS
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
    /* 순서 설정용 스타일 */
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
    
    /* 데이터 에디터 너비 최적화 */
    div[data-testid="stDataFrame"] {
        width: 100%;
    }
    /* ▼▼▼▼▼ [추가된 부분] 채널명 링크 색상 변경 ▼▼▼▼▼ */
    div[data-testid="stDataFrame"] a {
        color: #FFFFFF !important;  /* 평상시 색상: 흰색 (다크모드에 잘 보임) */
        /* 다른 색상 추천: 
           #FFD700 (노랑), #00FF00 (연두), #FF9999 (연한 빨강), #ADD8E6 (연한 파랑) 
        */
        text-decoration: none !important;
    }
    div[data-testid="stDataFrame"] a:hover {
        color: #FF4B4B !important; /* 마우스 올렸을 때: 빨강 */
        text-decoration: underline !important;
    }
    /* ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲ */
</style>
""", unsafe_allow_html=True)

# --- 유틸리티 함수 ---

def format_korean_number(num):
    """숫자를 '1.5억', '5300만' 등의 한글 포맷 문자열로 변환 (이모지 없음)"""
    if pd.isna(num) or num == 0: return "0"
    try:
        num = int(float(str(num).replace(',', '')))
        if num >= 100000000: return f"{num // 100000000}억"
        elif num >= 10000: return f"{num // 10000}만"
        else: return f"{num:,}"
    except: return str(num)

def format_korean_number_with_icon(num):
    """
    최근 토탈 전용 포맷팅: 숫자 크기에 따라 이모지 추가
    """
    if pd.isna(num) or num == 0: return "0"
    try:
        val = int(float(str(num).replace(',', '')))
        
        # 기본 한글 포맷팅
        if val >= 100000000: text = f"{val // 100000000}억"
        elif val >= 10000: text = f"{val // 10000}만"
        else: text = f"{val:,}"
        
        # 이모지 로직
        if val >= 10000000:   # 1,000만 이상
            return f"💎 {text}"
        elif val >= 1000000:  # 100만 이상
            return f"🔥 {text}"
        elif val >= 300000:   # 30만 이상
            return f"🔺 {text}"
        else:
            return text
    except: return str(num)

def add_status_dot(date_str):
    """
    날짜 문자열을 받아 최신성에 따라 상태 점(Dot)을 추가
    """
    if not date_str or pd.isna(date_str) or str(date_str).strip() == "": return ""
    try:
        clean_date = str(date_str).split(' ')[0].replace('.', '-').replace('/', '-')
        dt = datetime.strptime(clean_date, "%Y-%m-%d")
        diff = (datetime.now() - dt).days
        
        if diff <= 30:      # 1개월 이내
            return f"{clean_date} 🟢"
        elif diff <= 180:   # 6개월 이내 (1~6개월)
            return f"{clean_date} 🔵"
        else:               # 6개월 경과
            return f"{clean_date} ❌" 
    except:
        return str(date_str)

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
        
        rename_map = {
            '최근 업로드': '최근업로드',
            '최근 업로드일': '최근업로드',
            '최근영상': '최근업로드',
            '최근 영상': '최근업로드',
            '업로드일': '최근업로드',
            '마지막 업로드': '최근업로드'
        }
        df = df.rename(columns=rename_map)

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

# --- 백업 기능 ---
def run_backup():
    try:
        client = get_gspread_client()
        doc = client.open("유튜브보물창고_테스트")
        source_sheet = doc.sheet1
        
        day = datetime.now().day
        target_name = "백업_홀수" if day % 2 != 0 else "백업_짝수"
        
        all_values = source_sheet.get_all_values()
        
        try:
            target_sheet = doc.worksheet(target_name)
        except gspread.exceptions.WorksheetNotFound:
            target_sheet = doc.add_worksheet(title=target_name, rows=len(all_values)+100, cols=len(all_values[0])+5)
        
        target_sheet.clear()
        target_sheet.update('A1', all_values)
        
        return True, target_name
    except Exception as e:
        return False, str(e)

def update_gs_rows(edited_df, original_df):
    try:
        client = get_gspread_client()
        sheet = client.open("유튜브보물창고_테스트").sheet1
        headers = sheet.row_values(1)
        col_map = {name: i+1 for i, name in enumerate(headers)}
        
        count = 0
        for idx, row in edited_df.iterrows():
            orig_row = original_df[original_df['gs_row_index'] == row['gs_row_index']].iloc[0]
            fields_to_check = ['분류1', '분류2', '키워드', '템플릿', '메모']
            
            for field in fields_to_check:
                if field in row and str(row[field]) != str(orig_row[field]):
                    if field in col_map:
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
    col1, col2, col3, col4, col5, col6 = st.columns([2.5, 1, 1, 1, 1, 1])
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
        if st.button("💾 백업하기", use_container_width=True):
            success, target = run_backup()
            if success:
                st.toast(f"✅ '{target}' 시트에 백업 완료!", icon="💾")
            else:
                st.error(f"백업 실패: {target}")
    with col6:
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
    
    with st.sidebar:
        st.markdown("## 🌍 국가 필터")
        if '국가' in df.columns:
            country_options = ["전체"] + sorted([c for c in df['국가'].unique() if c])
            selected_country = st.selectbox("조회할 국가를 선택하세요", country_options, key="global_country_filter")
            if selected_country != "전체":
                df = df[df['국가'] == selected_country]
        else:
            st.warning("시트에 '국가' 컬럼이 없습니다.")

        st.markdown("---")
        st.markdown("## 📂 카테고리")
        
        total_count = len(df)
        if 'selected_분류1' not in st.session_state:
            st.session_state.selected_분류1 = "전체"

        is_all_active = (st.session_state.selected_분류1 == "전체")
        if st.button(f"전체 ({total_count})", key="side_all", use_container_width=True, type="primary" if is_all_active else "secondary"):
            st.session_state.selected_분류1 = "전체"
            st.rerun()
        
        if not st.session_state.selected_분류1:
             st.session_state.selected_분류1 = 분류1_list[0] if 분류1_list else "전체"

        for cat in 분류1_list:
            count = len(df[df['분류1'] == cat])
            display_text = f"{cat} ({count})"
            is_active = (st.session_state.selected_분류1 == cat)
            if st.button(display_text, key=f"side_{cat}", use_container_width=True, type="primary" if is_active else "secondary"):
                st.session_state.selected_분류1 = cat
                st.rerun()
    
    if st.session_state.selected_분류1:
        show_category_detail(df, cat_df, st.session_state.selected_분류1)

def show_category_detail(df, cat_df, 분류1):
    if 분류1 == "전체":
        df_filtered = df.copy()
        st.markdown(f"## 📊 전체 ({len(df_filtered)}개)")
    else:
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

    if 분류1 != "전체":
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
    else:
        selected_분류2 = '전체'
        st.session_state[f'selected_분류2_전체'] = '전체'

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
    
    # ------------------[디자인 및 데이터 포맷팅 로직]------------------
    
    # [변경] URL 컬럼을 표시 리스트에서 제거 (채널명 클릭으로 대체하기 위함)
    display_columns = [
        '국가', 
        '동영상', 
        '조회수', 
        '채널명', 
        '분류1',   
        '분류2',   
        '템플릿',  
        '메모', 
        '키워드',
        '운영기간', 
        '최근업로드',
        '최근 5개 토탈', 
        '최근 10개 토탈', 
        '최근 20개 토탈', 
        '최근 30개 토탈', 
        'gs_row_index'
        # 'URL' -> 제거됨
    ]
    
    # URL 데이터가 필요하므로 임시로 가져옴
    cols_to_fetch = [c for c in display_columns if c in df_display.columns]
    if 'URL' not in cols_to_fetch and 'URL' in df_display.columns:
        cols_to_fetch.append('URL')

    df_to_edit = df_display[cols_to_fetch].copy()

    # 1. 날짜에 상태 점(Dot) 추가
    if '최근업로드' in df_to_edit.columns:
        df_to_edit['최근업로드'] = df_to_edit['최근업로드'].apply(add_status_dot)

    # 2. '조회수' 컬럼 포맷팅
    if '조회수' in df_to_edit.columns:
        df_to_edit['조회수'] = df_to_edit['조회수'].apply(format_korean_number)

    # 3. '최근 X개 토탈' 컬럼 포맷팅
    icon_cols = ['최근 5개 토탈', '최근 10개 토탈', '최근 20개 토탈', '최근 30개 토탈']
    for col in icon_cols:
        if col in df_to_edit.columns:
            df_to_edit[col] = df_to_edit[col].apply(format_korean_number_with_icon)
            
    # [변경] 채널명을 클릭 가능하게 만들기 위해 데이터 교체
    # '채널명' 컬럼에 실제로는 URL 데이터를 넣고, LinkColumn으로 표시합니다.
    # 이렇게 하면 DataEditor 상에서 '채널명'이 클릭 가능한 링크가 됩니다.
    if 'URL' in df_to_edit.columns and '채널명' in df_to_edit.columns:
        df_to_edit['채널명'] = df_to_edit['URL']
        # URL 컬럼은 이제 필요 없으므로 DataFrame에서 제거 (화면 표시용)
        df_to_edit = df_to_edit.drop(columns=['URL'])

    all_cat1_options = sorted(list(cat_df['분류1'].unique())) if not cat_df.empty else sorted(list(df['분류1'].unique()))
    
    if 분류1 == "전체":
         allowed_cat2_options = sorted(list(cat_df['분류2'].unique())) if not cat_df.empty else sorted(list(df['분류2'].unique()))
    else:
         allowed_cat2_options = sorted(list(cat_df[cat_df['분류1'] == 분류1]['분류2'].unique()))

    if 분류1 != "전체":
        st.markdown(f"### 📋 채널 리스트 (총 {len(df_display)}개)")
    
    # 4. Data Editor 설정
    edited_df = st.data_editor(
        df_to_edit,
        use_container_width=True,
        height=600,
        column_config={
            # [변경] URL 컬럼 설정 제거 및 채널명 설정을 LinkColumn으로 변경
            # display_text 정규식을 사용하여 URL에서 @핸들 또는 채널ID만 추출하여 보여줌
            "채널명": st.column_config.LinkColumn(
                "채널명", 
                display_text=r"youtube\.com/(?:@|c/|channel/)?([^/?&]+)", 
                width="medium"
            ),
            
            "gs_row_index": None,
            "국가": st.column_config.TextColumn("국가", width="small"),
            "동영상": st.column_config.NumberColumn("동영상", width="small"),
            "조회수": st.column_config.TextColumn("조회수", disabled=True, width="small"),
            
            "분류1": st.column_config.SelectboxColumn("카테고리", options=all_cat1_options, required=True, width="small"),
            "분류2": st.column_config.SelectboxColumn("장르", options=allowed_cat2_options, required=True, width="small"),
            
            "키워드": st.column_config.TextColumn("키워드", width="medium"),
            "템플릿": st.column_config.TextColumn("템플릿", width="small"),
            "메모": st.column_config.TextColumn("메모", width="medium"),
            "운영기간": st.column_config.TextColumn("운영기간", width="small"),

            "최근업로드": st.column_config.TextColumn("최근업로드", disabled=True, width="small"),
            
            "최근 5개 토탈": st.column_config.TextColumn("최근 5개", disabled=True, width="small"),
            "최근 10개 토탈": st.column_config.TextColumn("최근 10개", disabled=True, width="small"),
            "최근 20개 토탈": st.column_config.TextColumn("최근 20개", disabled=True, width="small"),
            "최근 30개 토탈": st.column_config.TextColumn("최근 30개", disabled=True, width="small"),
        },
        hide_index=True,
        key=f"editor_{분류1}_{selected_분류2}"
    )

    with ctrl_col3:
        st.write("") 
        if st.button("💾 변경사항 시트에 저장", type="primary", use_container_width=True):
            with st.spinner("구글 시트 업데이트 중..."):
                # update_gs_rows 함수는 원본(df_display)과 비교하므로
                # df_to_edit의 '채널명'이 URL로 바뀌어 있어도 '분류','메모' 등의 수정사항 저장에는 문제없음
                update_count = update_gs_rows(edited_df, df_display)
                if update_count >= 0:
                    st.success(f"✅ {update_count}개의 항목이 수정되었습니다.")
                    st.cache_data.clear()
                    st.rerun()

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
