import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json
from datetime import datetime
from streamlit_sortables import sort_items
import math

# 페이지 설정
st.set_page_config(
    page_title="YouTube 보물창고",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS (다크 모드 + 테이블 스타일 + 페이지네이션)
st.markdown("""
<style>
    /* 기본 색상 변수 */
    :root {
        --dark-bg: #0f172a;
        --card-bg: #1a2647;
        --row-hover: #2a3a5a;
        --border-color: rgba(255,255,255,0.08);
        --text-primary: #ffffff;
        --text-secondary: #a0aec0;
        --accent-blue: #667eea;
        --accent-red: #ef4444;
        --accent-green: #10b981;
    }
    
    /* 전체 앱 배경 */
    .stApp {
        background-color: #0f172a !important;
        color: #ffffff !important;
    }
    
    /* 로고 버튼 */
    button[key="logo_home"] {
        border: none !important;
        background: transparent !important;
        font-size: 2.5rem !important;
        font-weight: 800 !important;
        padding: 0 !important;
        color: #31333F !important;
        text-align: left !important;
        box-shadow: none !important;
    }
    
    button[key="logo_home"]:hover {
        color: #FF0000 !important;
        background: transparent !important;
    }
    
    /* 순서 설정 스타일 */
    .sortable-item {
        background-color: #1a2647 !important;
        color: #fff !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 4px !important;
        padding: 0 !important;
        margin-bottom: 8px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.3) !important;
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
        background-color: #0f172a !important;
        color: #a0aec0 !important;
        font-weight: bold !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 45px !important;
        height: 100% !important;
        border-right: 1px solid rgba(255,255,255,0.1) !important;
        margin-right: 12px !important;
        flex-shrink: 0 !important;
    }
    
    .sortable-item:hover {
        border-color: #667eea !important;
        background-color: #2a3a5a !important;
        box-shadow: 0 4px 6px rgba(102,126,234,0.2) !important;
    }
    
    .sortable-container-header {
        display: none !important;
    }
    
    /* ======================== 갤러리 테이블 스타일 ======================== */
    
    .gallery-table-wrapper {
        background-color: #1a2647 !important;
        border-radius: 12px !important;
        overflow: hidden !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3) !important;
        margin-top: 16px !important;
        margin-bottom: 16px !important;
    }
    
    /* 테이블 헤더 */
    .gallery-table-header {
        display: grid !important;
        grid-template-columns: 2.5fr 1fr 1.8fr 0.8fr 1.2fr 0.6fr !important;
        gap: 0 !important;
        background: linear-gradient(135deg, #0f172a 0%, #1a2647 100%) !important;
        border-bottom: 2px solid rgba(255,255,255,0.12) !important;
        padding: 16px 16px !important;
        color: #a0aec0 !important;
        font-size: 12px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.8px !important;
        position: sticky !important;
        top: 0 !important;
        z-index: 10 !important;
    }
    
    .gallery-table-header > div {
        padding: 0 8px !important;
        display: flex !important;
        align-items: center !important;
    }
    
    /* 테이블 행 */
    .gallery-table-row {
        display: grid !important;
        grid-template-columns: 2.5fr 1fr 1.8fr 0.8fr 1.2fr 0.6fr !important;
        gap: 0 !important;
        border-bottom: 1px solid rgba(255,255,255,0.05) !important;
        padding: 14px 16px !important;
        align-items: center !important;
        transition: background-color 0.2s ease, border-color 0.2s ease !important;
    }
    
    .gallery-table-row:hover {
        background-color: rgba(102,126,234,0.08) !important;
        border-bottom-color: rgba(102,126,234,0.2) !important;
    }
    
    .gallery-table-row:last-child {
        border-bottom: none !important;
    }
    
    .gallery-table-cell {
        padding: 0 8px !important;
        display: flex !important;
        align-items: center !important;
    }
    
    /* ======================== 채널 정보 셀 ======================== */
    
    .channel-info-cell {
        display: flex !important;
        align-items: center !important;
        gap: 12px !important;
    }
    
    .channel-avatar {
        width: 48px !important;
        height: 48px !important;
        border-radius: 8px !important;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 22px !important;
        flex-shrink: 0 !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        box-shadow: 0 2px 8px rgba(102,126,234,0.15) !important;
    }
    
    .channel-text {
        display: flex !important;
        flex-direction: column !important;
        gap: 2px !important;
        min-width: 0 !important;
    }
    
    .channel-name-text {
        font-size: 14px !important;
        font-weight: 700 !important;
        color: #ffffff !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }
    
    .channel-handle-text {
        font-size: 11px !important;
        color: #a0aec0 !important;
    }
    
    .channel-tags {
        display: flex !important;
        gap: 4px !important;
        flex-wrap: wrap !important;
        margin-top: 4px !important;
    }
    
    .channel-tag {
        background-color: rgba(102,126,234,0.2) !important;
        border: 1px solid rgba(102,126,234,0.4) !important;
        border-radius: 4px !important;
        padding: 2px 6px !important;
        font-size: 9px !important;
        color: #a8b8ff !important;
        white-space: nowrap !important;
    }
    
    /* ======================== 구독자 셀 ======================== */
    
    .subscriber-cell {
        display: flex !important;
        flex-direction: column !important;
        gap: 2px !important;
    }
    
    .subscriber-number {
        font-size: 16px !important;
        font-weight: 800 !important;
        color: #ffffff !important;
        letter-spacing: -0.5px !important;
    }
    
    .subscriber-label {
        font-size: 10px !important;
        color: #a0aec0 !important;
        font-weight: 500 !important;
    }
    
    /* ======================== 최근 업로드 썸네일 ======================== */
    
    .thumbnails-cell {
        display: flex !important;
        gap: 6px !important;
        overflow-x: auto !important;
        scroll-behavior: smooth !important;
        padding: 0 4px !important;
    }
    
    .thumbnails-cell::-webkit-scrollbar {
        height: 4px !important;
    }
    
    .thumbnails-cell::-webkit-scrollbar-track {
        background: rgba(255,255,255,0.05) !important;
        border-radius: 2px !important;
    }
    
    .thumbnails-cell::-webkit-scrollbar-thumb {
        background: rgba(102,126,234,0.4) !important;
        border-radius: 2px !important;
    }
    
    .thumbnails-cell::-webkit-scrollbar-thumb:hover {
        background: rgba(102,126,234,0.6) !important;
    }
    
    .thumbnail-item {
        width: 56px !important;
        height: 56px !important;
        border-radius: 6px !important;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        flex-shrink: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 20px !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
        position: relative !important;
        overflow: hidden !important;
    }
    
    .thumbnail-item::before {
        content: '' !important;
        position: absolute !important;
        top: 0 !important;
        left: 0 !important;
        right: 0 !important;
        bottom: 0 !important;
        background: rgba(0,0,0,0) !important;
        transition: background 0.2s ease !important;
    }
    
    .thumbnail-item:hover {
        transform: scale(1.08) !important;
        border-color: rgba(102,126,234,0.6) !important;
        box-shadow: 0 4px 12px rgba(102,126,234,0.3) !important;
    }
    
    .thumbnail-item:hover::before {
        background: rgba(0,0,0,0.1) !important;
    }
    
    /* ======================== 영상 수 셀 ======================== */
    
    .video-count-cell {
        display: flex !important;
        flex-direction: column !important;
        gap: 2px !important;
        text-align: center !important;
    }
    
    .video-count-number {
        font-size: 18px !important;
        font-weight: 800 !important;
        color: #ffffff !important;
    }
    
    .video-count-label {
        font-size: 10px !important;
        color: #a0aec0 !important;
    }
    
    /* ======================== 일일 증감 셀 ======================== */
    
    .daily-change-cell {
        display: flex !important;
        flex-direction: column !important;
        gap: 2px !important;
    }
    
    .change-value {
        font-size: 14px !important;
        font-weight: 700 !important;
        letter-spacing: -0.5px !important;
    }
    
    .change-positive {
        color: #ef4444 !important;
    }
    
    .change-negative {
        color: #10b981 !important;
    }
    
    .change-label {
        font-size: 10px !important;
        color: #a0aec0 !important;
        font-weight: 500 !important;
    }
    
    /* ======================== 액션 버튼 셀 ======================== */
    
    .action-cell {
        display: flex !important;
        gap: 6px !important;
        justify-content: center !important;
    }
    
    .action-btn {
        width: 32px !important;
        height: 32px !important;
        border-radius: 6px !important;
        background-color: rgba(102,126,234,0.15) !important;
        border: 1px solid rgba(102,126,234,0.3) !important;
        color: #a8b8ff !important;
        font-size: 14px !important;
        cursor: pointer !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        transition: all 0.2s ease !important;
        padding: 0 !important;
    }
    
    .action-btn:hover {
        background-color: rgba(102,126,234,0.3) !important;
        border-color: rgba(102,126,234,0.6) !important;
        transform: scale(1.1) translateY(-1px) !important;
        box-shadow: 0 4px 8px rgba(102,126,234,0.2) !important;
    }
    
    /* ======================== 필터 UI ======================== */
    
    .filter-container {
        background-color: rgba(26,38,71,0.5) !important;
        border: 1px solid rgba(255,255,255,0.05) !important;
        border-radius: 8px !important;
        padding: 12px !important;
        margin-bottom: 16px !important;
    }
    
    /* ======================== 페이지네이션 ======================== */
    
    .pagination-container {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        gap: 8px !important;
        margin-top: 24px !important;
        margin-bottom: 24px !important;
        flex-wrap: wrap !important;
    }
    
    .pagination-info {
        background-color: rgba(26,38,71,0.5) !important;
        border: 1px solid rgba(255,255,255,0.05) !important;
        border-radius: 6px !important;
        padding: 8px 12px !important;
        color: #a0aec0 !important;
        font-size: 12px !important;
        font-weight: 600 !important;
    }
    
    .pagination-stats {
        background-color: rgba(102,126,234,0.1) !important;
        border: 1px solid rgba(102,126,234,0.3) !important;
        border-radius: 6px !important;
        padding: 8px 12px !important;
        color: #a8b8ff !important;
        font-size: 12px !important;
        font-weight: 600 !important;
    }
    
    /* 데이터 에디터 */
    div[data-testid="stDataFrame"] {
        width: 100% !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 유틸리티 함수 ---

def format_korean_number(num):
    """숫자를 '1.5억', '5300만' 등의 한글 포맷 문자열로 변환"""
    if pd.isna(num) or num == 0: return "0"
    try:
        num = int(float(str(num).replace(',', '')))
        if num >= 100000000: return f"{num // 100000000}억"
        elif num >= 10000: return f"{num // 10000}만"
        else: return f"{num:,}"
    except: return str(num)

def format_korean_number_with_icon(num):
    """최근 토탈 전용 포맷팅: 숫자 크기에 따라 이모지 추가"""
    if pd.isna(num) or num == 0: return "0"
    try:
        val = int(float(str(num).replace(',', '')))
        
        if val >= 100000000: text = f"{val // 100000000}억"
        elif val >= 10000: text = f"{val // 10000}만"
        else: text = f"{val:,}"
        
        if val >= 10000000:
            return f"💎 {text}"
        elif val >= 1000000:
            return f"🔥 {text}"
        elif val >= 300000:
            return f"🔺 {text}"
        else:
            return text
    except: return str(num)

def add_status_dot(date_str, ten_day_count):
    """10일 기준 값에 따라 상태 점(Dot)을 추가"""
    if not date_str or pd.isna(date_str) or str(date_str).strip() == "": 
        return ""
    
    try:
        clean_date = str(date_str).split(' ')[0].replace('.', '-').replace('/', '-')
        
        try:
            count = int(float(str(ten_day_count).replace(',', ''))) if not pd.isna(ten_day_count) else 0
        except:
            count = 0
        
        if count >= 5:
            return f"{clean_date} 🟢"
        elif count >= 2:
            return f"{clean_date} 🔵"
        else:
            return f"{clean_date} ❌"
    except:
        return str(date_str)

def get_placeholder_icon(category):
    """카테고리별 플레이스홀더 아이콘"""
    icons = {
        '음악': '🎵',
        '게임': '🎮',
        '요리': '👨‍🍳',
        '교육': '📚',
        '뷰티': '💄',
        '여행': '✈️',
        '테크': '💻',
        '스포츠': '⚽',
        '엔터': '🎬',
        '먹방': '🍜',
    }
    return icons.get(category, '📺')

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
        
        numeric_columns = [
            '구독자', '동영상', '조회수', 
            '최근 5개 토탈', '최근 10개 토탈', '최근 20개 토탈', '최근 30개 토탈', '10일기준',
            '5일조회수합계', '10일조회수합계', '15일조회수합계'
        ]
        
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
    col1, col2, col3, col4, col5, col6, col7 = st.columns([2.5, 1, 1, 1, 1, 1, 1])
    with col1:
        if st.button("🎬 YouTube 보물창고", key="logo_home", use_container_width=False):
            st.session_state.page = "dashboard"
            st.rerun()
    with col2:
        if st.button("🏠 대시보드", use_container_width=True):
            st.session_state.page = "dashboard"
            st.rerun()
    with col3:
        if st.button("🎨 갤러리", use_container_width=True):
            st.session_state.page = "gallery"
            st.rerun()
    with col4:
        if st.button("📁 카테고리설정", use_container_width=True):
            st.session_state.page = "category_mgmt"
            st.rerun()
    with col5:
        if st.button("⚙️ 순서 설정", use_container_width=True):
            st.session_state.page = "settings"
            st.rerun()
    with col6:
        if st.button("💾 백업하기", use_container_width=True):
            success, target = run_backup()
            if success:
                st.toast(f"✅ '{target}' 시트에 백업 완료!", icon="💾")
            else:
                st.error(f"백업 실패: {target}")
    with col7:
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

# [최적화된] 갤러리 페이지 - 페이지네이션 + 성능 개선
def show_gallery():
    """다크 모드 테이블 형식의 갤러리 뷰 (한 페이지에 20개씩, 최적화됨)"""
    st.markdown("## 🎨 채널 갤러리")
    df, cat_df = load_data()
    if df.empty: 
        st.warning("데이터를 불러올 수 없습니다.")
        return
    
    if 'page_order' not in st.session_state:
        saved_order = load_config_from_sheet()
        st.session_state.page_order = sync_order_with_data(
            saved_order if saved_order else {'분류1_순서': [], '분류2_순서': {}, '채널_순서': {}}, 
            df, cat_df
        )

    분류1_list = st.session_state.page_order['분류1_순서']
    
    # 페이지네이션 상태 초기화
    if 'gallery_current_page' not in st.session_state:
        st.session_state.gallery_current_page = 1
    if 'gallery_items_per_page' not in st.session_state:
        st.session_state.gallery_items_per_page = 20
    
    # 필터 UI
    st.markdown('<div class="filter-container">', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        search_query = st.text_input("🔍 채널명 검색", key="gallery_search", placeholder="채널명을 입력하세요")
    with col2:
        selected_cat1 = st.selectbox("카테고리", ["전체"] + 분류1_list, key="gallery_cat", label_visibility="collapsed")
    with col3:
        sort_option = st.selectbox("정렬", ["15일합계 ↓", "구독자 ↓", "조회수 ↓", "동영상 ↓"], key="gallery_sort", label_visibility="collapsed")
    with col4:
        items_per_page = st.selectbox("한 페이지", [10, 20, 30, 50], key="gallery_items", label_visibility="collapsed", index=1)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 데이터 필터링 및 정렬 (최적화)
    df_filtered = df.copy()
    
    if selected_cat1 != "전체":
        df_filtered = df_filtered[df_filtered['분류1'] == selected_cat1]
    
    if search_query:
        df_filtered = df_filtered[df_filtered['채널명'].str.contains(search_query, case=False, na=False)]
    
    # 정렬
    if "15일합계" in sort_option:
        df_filtered = df_filtered.sort_values('15일조회수합계', ascending=False)
    elif "구독자" in sort_option:
        df_filtered = df_filtered.sort_values('구독자', ascending=False)
    elif "조회수" in sort_option:
        df_filtered = df_filtered.sort_values('조회수', ascending=False)
    elif "동영상" in sort_option:
        df_filtered = df_filtered.sort_values('동영상', ascending=False)
    
    # 페이지네이션 계산
    total_items = len(df_filtered)
    total_pages = max(1, math.ceil(total_items / items_per_page))
    
    # 현재 페이지 검증
    current_page = st.session_state.gallery_current_page
    if current_page > total_pages:
        current_page = total_pages
        st.session_state.gallery_current_page = current_page
    
    # 현재 페이지의 데이터만 추출 (성능 최적화)
    start_idx = (current_page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    df_page = df_filtered.iloc[start_idx:end_idx]
    
    # 통계 정보 표시
    stat_html = f"""
    <div class="pagination-stats">
        📊 총 {total_items:,}개 | 페이지 {current_page}/{total_pages} | 표시 중: {start_idx+1}~{min(end_idx, total_items)}
    </div>
    """
    st.markdown(stat_html, unsafe_allow_html=True)
    
    # 데이터가 있으면 테이블 렌더링 (20개 또는 설정값만 렌더링)
    if len(df_page) > 0:
        render_gallery_table(df_page)
    else:
        st.info("표시할 데이터가 없습니다.")
    
    # 페이지네이션 컨트롤 (상단)
    st.markdown("---")
    render_pagination_controls(current_page, total_pages)

def render_pagination_controls(current_page, total_pages):
    """페이지네이션 컨트롤 렌더링"""
    if total_pages <= 1:
        return
    
    col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
    
    with col1:
        if st.button("⬅️ 처음", use_container_width=True, key="page_first"):
            st.session_state.gallery_current_page = 1
            st.rerun()
    
    with col2:
        if st.button("◀ 이전", use_container_width=True, key="page_prev"):
            if st.session_state.gallery_current_page > 1:
                st.session_state.gallery_current_page -= 1
                st.rerun()
    
    with col3:
        # 페이지 번호 입력
        selected_page = st.number_input(
            "페이지 선택",
            min_value=1,
            max_value=total_pages,
            value=st.session_state.gallery_current_page,
            key="page_input",
            label_visibility="collapsed"
        )
        if selected_page != st.session_state.gallery_current_page:
            st.session_state.gallery_current_page = selected_page
            st.rerun()
    
    with col4:
        if st.button("다음 ▶", use_container_width=True, key="page_next"):
            if st.session_state.gallery_current_page < total_pages:
                st.session_state.gallery_current_page += 1
                st.rerun()
    
    with col5:
        if st.button("마지막 ➡️", use_container_width=True, key="page_last"):
            st.session_state.gallery_current_page = total_pages
            st.rerun()

def render_gallery_table(df):
    """갤러리 테이블 렌더링 (최적화: 필요한 데이터만 처리)"""
    # 테이블 헤더
    header_html = """
    <div class="gallery-table-wrapper">
        <div class="gallery-table-header">
            <div>채널 정보</div>
            <div>구독자 수</div>
            <div>최근 콘텐츠</div>
            <div>영상 수</div>
            <div>일일 증감</div>
            <div>액션</div>
        </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)
    
    # 테이블 행 렌더링 (현재 페이지 데이터만)
    for idx, (_, row) in enumerate(df.iterrows()):
        render_gallery_row(row, idx)
    
    st.markdown("</div>", unsafe_allow_html=True)

def render_gallery_row(row, idx):
    """갤러리 테이블 행 렌더링 (성능 최적화)"""
    channel_name = row.get('채널명', 'N/A')
    category = row.get('분류1', '')
    genre = row.get('분류2', '')
    url = row.get('URL', '')
    subscribers = int(row.get('구독자', 0))
    videos = int(row.get('동영상', 0))
    change_val = int(row.get('15일조회수합계', 0))
    
    # 아이콘 선택
    icon = get_placeholder_icon(category)
    
    # 변화량 색상
    change_color = "change-positive" if change_val >= 0 else "change-negative"
    change_symbol = "+" if change_val >= 0 else ""
    
    # 썸네일 HTML 생성
    thumbnails_html = """
    <div class="thumbnails-cell">
        <div class="thumbnail-item">📹</div>
        <div class="thumbnail-item">📹</div>
        <div class="thumbnail-item">📹</div>
        <div class="thumbnail-item">📹</div>
        <div class="thumbnail-item">📹</div>
    </div>
    """
    
    # 행 HTML (최소한의 HTML로 최적화)
    row_html = f"""
    <div class="gallery-table-row">
        <div class="gallery-table-cell channel-info-cell">
            <div class="channel-avatar">{icon}</div>
            <div class="channel-text">
                <div class="channel-name-text">{channel_name}</div>
                <div class="channel-handle-text">@{channel_name.lower()}</div>
                <div class="channel-tags">
                    <span class="channel-tag">{category}</span>
                    <span class="channel-tag">{genre}</span>
                </div>
            </div>
        </div>
        <div class="gallery-table-cell subscriber-cell">
            <div class="subscriber-number">{format_korean_number(subscribers)}</div>
            <div class="subscriber-label">구독자</div>
        </div>
        <div class="gallery-table-cell">{thumbnails_html}</div>
        <div class="gallery-table-cell video-count-cell">
            <div class="video-count-number">{videos}</div>
            <div class="video-count-label">개</div>
        </div>
        <div class="gallery-table-cell daily-change-cell">
            <div class="change-value {change_color}">{change_symbol}{format_korean_number(change_val)}</div>
            <div class="change-label">최근 15일</div>
        </div>
        <div class="gallery-table-cell action-cell">
            <div class="action-btn" title="상세보기">📊</div>
            <div class="action-btn" title="즐겨찾기">❤️</div>
        </div>
    </div>
    """
    
    st.markdown(row_html, unsafe_allow_html=True)

# --- 대시보드 페이지 ---
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
        sort_options = ['15일합계', '최근 30개 토탈', '최근 20개 토탈', '최근 10개 토탈', '최근 5개 토탈', '조회수', '사용자 지정']
        sort_by = st.selectbox("정렬 기준", sort_options, index=0, key=f"sort_{분류1}")
    
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
        if sort_by == '15일합계':
            df_display = df_display.sort_values(by=['15일조회수합계', '채널명'], ascending=[False, True])
        else:
            df_display = df_display.sort_values(by=[sort_by, '채널명'], ascending=[False, True])
    
    display_columns = [
        '국가', '동영상', '조회수', '채널명', '분류1', '분류2',
        '템플릿', '메모', '키워드', '운영기간', 'URL', 
        '5일조회수합계', '10일조회수합계', '15일조회수합계', 'gs_row_index'
    ]
    
    df_to_edit = df_display[[c for c in display_columns if c in df_display.columns]].copy()

    new_cols = ['5일조회수합계', '10일조회수합계', '15일조회수합계']
    for col in new_cols:
        if col in df_to_edit.columns:
            df_to_edit[col] = df_to_edit[col].apply(format_korean_number_with_icon)

    all_cat1_options = sorted(list(cat_df['분류1'].unique())) if not cat_df.empty else sorted(list(df['분류1'].unique()))
    
    if 분류1 == "전체":
         allowed_cat2_options = sorted(list(cat_df['분류2'].unique())) if not cat_df.empty else sorted(list(df['분류2'].unique()))
    else:
         allowed_cat2_options = sorted(list(cat_df[cat_df['분류1'] == 분류1]['분류2'].unique()))

    if 분류1 != "전체":
        st.markdown(f"### 📋 채널 리스트 (총 {len(df_display)}개)")
    
    column_config = {
        "URL": st.column_config.LinkColumn("링크", display_text="보기", width="small"),
        "5일조회수합계": st.column_config.TextColumn("5일합계", disabled=True, width="small"),
        "10일조회수합계": st.column_config.TextColumn("10일합계", disabled=True, width="small"),
        "15일조회수합계": st.column_config.TextColumn("15일합계", disabled=True, width="small"),
        "gs_row_index": None,
        "국가": st.column_config.TextColumn("국가", width="small"),
        "동영상": st.column_config.NumberColumn("동영상", width="small"),
        "조회수": st.column_config.TextColumn("조회수", disabled=True, width="small"),
        "채널명": st.column_config.TextColumn("채널명", width="medium"),
        "분류1": st.column_config.SelectboxColumn("카테고리", options=all_cat1_options, required=True, width="small"),
        "분류2": st.column_config.SelectboxColumn("장르", options=allowed_cat2_options, required=True, width="small"),
        "키워드": st.column_config.TextColumn("키워드", width="medium"),
        "템플릿": st.column_config.TextColumn("템플릿", width="small"),
        "메모": st.column_config.TextColumn("메모", width="medium"),
        "운영기간": st.column_config.TextColumn("운영기간", width="small"),
    }
    
    text_cols_safe = ['채널명', '분류1', '분류2', '키워드', '템플릿', '메모', '운영기간',
                 '조회수', 'URL', '국가', '5일조회수합계', '10일조회수합계', '15일조회수합계']
    
    for col in text_cols_safe:
        if col in df_to_edit.columns:
            df_to_edit[col] = df_to_edit[col].fillna("").astype(str)

    if '동영상' in df_to_edit.columns:
        df_to_edit['동영상'] = pd.to_numeric(df_to_edit['동영상'], errors='coerce').fillna(0)
    
    edited_df = st.data_editor(
        df_to_edit,
        use_container_width=True,
        height=600,
        column_config=column_config,
        hide_index=True,
        key=f"editor_{분류1}_{selected_분류2}"
    )

    with ctrl_col3:
        st.write("") 
        if st.button("💾 변경사항 시트에 저장", type="primary", use_container_width=True):
            with st.spinner("구글 시트 업데이트 중..."):
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
    
    if 'page_order' not in st.session_state:
        saved_order = load_config_from_sheet()
        st.session_state.page_order = sync_order_with_data(
            saved_order if saved_order else {'분류1_순서': [], '분류2_순서': {}, '채널_순서': {}}, 
            df, cat_df
        )
    
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
    if 'page' not in st.session_state: 
        st.session_state.page = "dashboard"
    
    show_navigation()
    st.markdown("---")
    
    if st.session_state.page == "dashboard":
        show_dashboard()
    elif st.session_state.page == "gallery":
        show_gallery()
    elif st.session_state.page == "category_mgmt":
        show_category_management()
    elif st.session_state.page == "settings":
        show_settings()
        
    st.markdown(f"<p style='text-align:right; color:gray;'>Update: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
