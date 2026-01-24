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
    initial_sidebar_state="expanded" # 사이드바를 기본적으로 열어둠
)

# -------------------------------------------------------------
# 커스텀 CSS (오른쪽 사이드바 및 버튼 스타일)
# -------------------------------------------------------------
st.markdown("""
<style>
    /* 1. 사이드바를 오른쪽으로 이동 */
    [data-testid="stSidebar"] {
        left: auto !important;
        right: 0 !important;
        border-left: 1px solid #e6e9ef;
        border-right: none !important;
    }
    [data-testid="stSidebarNav"] {
        display: none;
    }
    /* 사이드바 열림/닫힘 애니메이션 조절 */
    section[data-testid="stSidebar"] > div {
        padding-top: 2rem;
    }

    /* 2. 분류 버튼 스타일 (사이드바용) */
    .stButton > button {
        width: 100%;
        margin-bottom: 5px;
        border-radius: 8px;
    }

    /* 3. 기존 스타일 유지 */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.2rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .metric-card h3 { font-size: 1.5rem; margin: 0; font-weight: bold; }
    
    /* 4. 정렬 아이템 스타일 (번호 고정형) */
    .sortable-item {
        background-color: white !important;
        color: #333 !important;
        border: 1px solid #ccc !important;
        border-radius: 4px !important;
        padding: 0 !important;
        margin-bottom: 8px !important;
        display: flex !important;
        align-items: center !important;
        height: 42px !important;
        counter-increment: item-rank;
    }
    .sortable-item::before {
        content: counter(item-rank);
        background-color: #eee !important;
        width: 45px !important;
        height: 100% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        border-right: 1px solid #ccc !important;
        margin-right: 12px !important;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# 유틸리티 함수 (숫자 포맷팅 등 - 기존과 동일)
# -------------------------------------------------------------
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
    else: return f"{num:,}"

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
        cols = ['구독자', '동영상', '조회수', '최근 5개 토탈', '최근 10개 토탈', '최근 20개 토탈', '최근 30개 토탈']
        for col in cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"데이터 로드 실패: {str(e)}"); return pd.DataFrame()

# -------------------------------------------------------------
# 설정 관리 (순서 동기화 등)
# -------------------------------------------------------------
def load_config_from_sheet():
    try:
        client = get_gspread_client()
        worksheet = client.open("유튜브보물창고_테스트").worksheet("config")
        return json.loads(worksheet.acell('A1').value)
    except: return None

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
# 메인 UI 컴포넌트
# -------------------------------------------------------------
def show_navigation():
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    with col1: st.markdown("# 🎬 YouTube 보물창고")
    with col2:
        if st.button("🏠 대시보드", key="nav_dashboard", use_container_width=True):
            st.session_state.page = "dashboard"; st.rerun()
    with col3:
        if st.button("⚙️ 순서 설정", key="nav_settings", use_container_width=True):
            st.session_state.page = "settings"; st.rerun()
    with col4:
        if st.button("🔄 새로고침", key="nav_refresh", use_container_width=True):
            st.cache_data.clear(); st.rerun()

def show_dashboard():
    df = load_data()
    if df.empty: return
    
    # 순서 데이터 로드
    if 'page_order' not in st.session_state:
        saved_order = load_config_from_sheet()
        st.session_state.page_order = sync_order_with_data(saved_order if saved_order else {'분류1_순서': [], '분류2_순서': {}}, df)

    분류1_list = st.session_state.page_order['분류1_순서']
    if 'selected_분류1' not in st.session_state:
        st.session_state.selected_분류1 = 분류1_list[0] if 분류1_list else None

    # --- [오른쪽 사이드바] 분류 선택 창 ---
    with st.sidebar:
        st.markdown("### 📂 분류 선택")
        # 2열 그리드로 버튼 배치
        for i in range(0, len(분류1_list), 2):
            cols = st.columns(2)
            for j in range(2):
                if i + j < len(분류1_list):
                    cat = 분류1_list[i+j]
                    is_active = (st.session_state.selected_분류1 == cat)
                    if cols[j].button(cat, key=f"side_{cat}", type="primary" if is_active else "secondary"):
                        st.session_state.selected_분류1 = cat
                        st.rerun()

    # --- [메인 영역] 상세 내용 ---
    if st.session_state.selected_분류1:
        show_category_detail(df, st.session_state.selected_분류1)

def show_category_detail(df, 분류1):
    df_filtered = df[df['분류1'] == 분류1].copy()
    if df_filtered.empty: return

    분류2_list = st.session_state.page_order['분류2_순서'].get(분류1, ['전체'])
    
    st.markdown(f"## 📊 {분류1}")
    col1, col2 = st.columns([1, 3])
    with col1: selected_분류2 = st.selectbox("🔍 분류2 선택", 분류2_list, key=f"sel2_{분류1}")
    
    df_display = df_filtered[df_filtered['분류2'] == selected_분류2].copy() if selected_분류2 != '전체' else df_filtered.copy()
    
    # 상단 카드
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f"<div class='metric-card'><h3>{len(df_display)}</h3><p>채널 수</p></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='metric-card'><h3>{format_korean_number(df_display['구독자'].sum())}</h3><p>총 구독자</p></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='metric-card'><h3>{format_korean_number(df_display['조회수'].sum())}</h3><p>총 조회수</p></div>", unsafe_allow_html=True)
    with c4: st.markdown(f"<div class='metric-card'><h3>{format_korean_number(df_display['최근 30개 토탈'].sum())}</h3><p>최근 30개 합계</p></div>", unsafe_allow_html=True)
    
    st.markdown("---")
    s1, s2 = st.columns([2, 1])
    with s1: search = st.text_input("🔍 채널명 검색", key=f"s_{분류1}")
    with s2: sort_by = st.selectbox("정렬 기준", ['최근 30개 토탈', '최근 20개 토탈', '최근 10개 토탈', '최근 5개 토탈', '구독자'], key=f"sort_{분류1}")
    
    if search: df_display = df_display[df_display['채널명'].str.contains(search, case=False, na=False)]
    df_display = df_display.sort_values(by=[sort_by, '채널명'], ascending=[False, True])
    
    # 테이블 표시 (URL 클릭 기능 및 추가 지표 포함)
    display_cols = ['채널명', 'URL', '분류2', '구독자', '최근 5개 토탈', '최근 10개 토탈', '최근 20개 토탈', '최근 30개 토탈']
    df_fmt = df_display[display_cols].copy()
    
    # 숫자 포맷팅
    for c in ['구독자', '최근 5개 토탈', '최근 10개 토탈', '최근 20개 토탈', '최근 30개 토탈']:
        df_fmt[c] = df_fmt[c].apply(format_korean_number)

    st.dataframe(
        df_fmt,
        use_container_width=True,
        height=600,
        column_config={
            "URL": st.column_config.LinkColumn("채널 링크", display_text="바로가기"),
            "채널명": st.column_config.TextColumn("채널명", width="medium")
        },
        hide_index=True
    )

# 순서 설정 페이지 (기존 유지)
def show_settings():
    st.markdown("## ⚙️ 순서 설정")
    # ... (기존 설정 코드와 동일하게 작성)

def main():
    if 'page' not in st.session_state: st.session_state.page = "dashboard"
    show_navigation()
    st.markdown("---")
    if st.session_state.page == "dashboard": show_dashboard()
    elif st.session_state.page == "settings": show_settings()

if __name__ == "__main__":
    main()
