import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json
from datetime import datetime
from streamlit_sortables import sort_items

# 1. 페이지 설정
st.set_page_config(
    page_title="YouTube 보물창고 관리자",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. 커스텀 CSS (사진의 디자인을 그대로 구현)
st.markdown("""
<style>
    /* 전체 배경색 및 폰트 */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }

    /* 엑셀 스타일 순서 설정 레이아웃 */
    /* 카운터 초기화: 아이템이 담기는 컨테이너 기준 */
    div[data-testid="stVerticalBlock"] > div {
        counter-reset: excel-rank;
    }

    /* 드래그 가능한 아이템 전체 행(Row) 스타일 */
    .sortable-item {
        background-color: transparent !important;
        border: none !important;
        padding: 0 !important;
        margin-bottom: 0 !important; /* 칸 사이 간격 제거 (표 느낌) */
        display: flex !important;
        align-items: center !important;
        height: 48px !important;
        cursor: grab !important;
    }

    /* 왼쪽 번호 박스 (디자인 고정 영역) */
    .sortable-item::before {
        counter-increment: excel-rank;
        content: counter(excel-rank);
        
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        min-width: 60px !important;
        height: 100% !important;
        background-color: #ffffff !important;
        color: #333 !important;
        font-weight: 700 !important;
        font-size: 18px !important;
        border: 1px solid #d1d1d1 !important; /* 회색 격자 테두리 */
        margin-right: 20px !important;
        box-sizing: border-box !important;
    }

    /* 오른쪽 빨간색 버튼 (드래그 되는 알맹이 영역) */
    .sortable-item > div {
        flex-grow: 1;
        background-color: #FF4B4B !important; /* 사진 속 빨간색 */
        color: white !important;
        padding: 10px 20px !important;
        border-radius: 6px !important;
        font-weight: bold !important;
        text-align: center !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1) !important;
        border: 1px solid #e03e3e !important;
        max-width: 300px;
    }

    /* 호버/드래그 시 효과 */
    .sortable-item:hover > div {
        background-color: #ff3333 !important;
        transform: scale(1.02);
        transition: 0.2s;
    }

    /* 대시보드 메트릭 카드 스타일 */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-card h3 { font-size: 2rem; margin: 0; font-weight: bold; color: white; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 및 구글 시트 함수
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
        return df
    except Exception as e:
        st.error(f"데이터 로드 실패: {str(e)}")
        return pd.DataFrame()

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
        except: worksheet = doc.add_worksheet(title="config", rows=5, cols=5)
        worksheet.update_acell('A1', json.dumps(order_data, ensure_ascii=False))
        return True
    except: return False

def sync_order_with_data(saved_order, df):
    live_cat1 = sorted(list(df['분류1'].dropna().unique()))
    current_order = saved_order.get('분류1_순서', [])
    new_order = [c for c in current_order if c in live_cat1]
    for c in live_cat1:
        if c not in new_order: new_order.append(c)
    
    cat2_dict = saved_order.get('분류2_순서', {})
    for c1 in new_order:
        live_cat2 = sorted(list(df[df['분류1'] == c1]['분류2'].dropna().unique()))
        if '전체' not in live_cat2: live_cat2.insert(0, '전체')
        curr_c2 = cat2_dict.get(c1, [])
        new_c2 = [c for c in curr_c2 if c in live_cat2]
        for c in live_cat2:
            if c not in new_c2: new_c2.append(c)
        cat2_dict[c1] = new_c2
    
    return {'분류1_순서': new_order, '분류2_순서': cat2_dict}

# 4. UI 컴포넌트
def show_navigation():
    col1, col2, col3 = st.columns([4, 1, 1])
    with col1: st.title("🎬 YouTube 보물창고")
    with col2:
        if st.button("🏠 대시보드", use_container_width=True): 
            st.session_state.page = "dashboard"
            st.rerun()
    with col3:
        if st.button("⚙️ 순서 설정", use_container_width=True): 
            st.session_state.page = "settings"
            st.rerun()

def show_dashboard():
    df = load_data()
    if df.empty: return
    
    # 설정 로드
    if 'page_order' not in st.session_state:
        saved = load_config_from_sheet()
        st.session_state.page_order = sync_order_with_data(saved if saved else {}, df)

    분류1_list = st.session_state.page_order['분류1_순서']
    if 'sel_c1' not in st.session_state: st.session_state.sel_c1 = 분류1_list[0] if 분류1_list else None
    
    # 상단 대분류 버튼
    cols = st.columns(6)
    for idx, cat in enumerate(분류1_list):
        with cols[idx % 6]:
            if st.button(cat, key=f"nav_{cat}", use_container_width=True, 
                         type="primary" if st.session_state.sel_c1 == cat else "secondary"):
                st.session_state.sel_c1 = cat
                st.rerun()
    
    st.divider()
    
    # 상세 내용
    c1 = st.session_state.sel_c1
    if c1:
        df_c1 = df[df['분류1'] == c1]
        c2_list = st.session_state.page_order['분류2_순서'].get(c1, ['전체'])
        
        col_a, col_b = st.columns([1, 4])
        with col_a: sel_c2 = st.selectbox("소분류", c2_list)
        
        display_df = df_c1 if sel_c2 == '전체' else df_c1[df_c1['분류2'] == sel_c2]
        
        m1, m2, m3 = st.columns(3)
        m1.markdown(f"<div class='metric-card'><h3>{len(display_df)}</h3><p>채널 수</p></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='metric-card'><h3>{display_df['구독자'].sum():,}</h3><p>총 구독자</p></div>", unsafe_allow_html=True)
        m3.markdown(f"<div class='metric-card'><h3>{display_df['조회수'].sum():,}</h3><p>총 조회수</p></div>", unsafe_allow_html=True)
        
        st.dataframe(display_df, use_container_width=True)

# 5. 설정 페이지 (요청하신 디자인 핵심)
def show_settings():
    st.header("⚙️ 카테고리 순서 설정")
    df = load_data()
    
    if 'page_order' not in st.session_state:
        saved = load_config_from_sheet()
        st.session_state.page_order = sync_order_with_data(saved if saved else {}, df)

    tab1, tab2, tab3 = st.tabs(["📂 분류1 순서", "📁 분류2 순서", "💾 저장하기"])

    with tab1:
        st.markdown("#### 분류1 (대분류) 순서 조정")
        st.info("💡 오른쪽 빨간색 카드를 드래그하세요. 왼쪽 번호는 고정되어 표시됩니다.")
        
        # 디자인을 위해 중앙 정렬된 컬럼 생성
        _, col_mid, _ = st.columns([1, 2, 1])
        with col_mid:
            items = st.session_state.page_order['분류1_순서']
            # 단일 컨테이너 모드
            sorted_items = sort_items([{'header': '', 'items': items}], direction='vertical', key='sort_c1_v1')
            new_order = sorted_items[0]['items']
            
            if new_order != items:
                st.session_state.page_order['분류1_순서'] = new_order
                st.rerun()

    with tab2:
        st.markdown("#### 분류2 (소분류) 순서 조정")
        selected_c1 = st.selectbox("대분류 선택", st.session_state.page_order['분류1_순서'], key="set_c2_sel")
        
        _, col_mid, _ = st.columns([1, 2, 1])
        with col_mid:
            sub_items = st.session_state.page_order['분류2_순서'].get(selected_c1, [])
            sorted_sub = sort_items([{'header': f'[{selected_c1}] 순서', 'items': sub_items}], direction='vertical', key=f'sort_{selected_c1}')
            new_sub_order = sorted_sub[0]['items']
            
            if new_sub_order != sub_items:
                st.session_state.page_order['분류2_순서'][selected_c1] = new_sub_order
                st.rerun()

    with tab3:
        st.markdown("#### 💾 설정 완료")
        if st.button("구글 시트에 최종 저장", type="primary", use_container_width=True):
            if save_config_to_sheet(st.session_state.page_order):
                st.success("성공적으로 저장되었습니다!")
            else:
                st.error("저장 중 오류가 발생했습니다.")

def main():
    if 'page' not in st.session_state: st.session_state.page = "dashboard"
    show_navigation()
    st.divider()
    if st.session_state.page == "dashboard": show_dashboard()
    else: show_settings()

if __name__ == "__main__":
    main()
