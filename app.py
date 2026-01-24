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

# 커스텀 CSS (번호 고정 + 빨간 버튼 디자인)
st.markdown("""
<style>
    /* 1. 카운터 초기화 (번호 생성용) */
    .stApp { counter-reset: item-rank; }
    div[data-testid="stTabContent"] { counter-reset: item-rank; }

    /* 2. Sortable 아이템 컨테이너 (투명하게 설정) */
    .sortable-item {
        background-color: transparent !important;
        border: none !important;
        padding: 0 !important;
        margin-bottom: 5px !important;
        display: flex !important;
        align-items: center !important;
        cursor: grab !important;
        counter-increment: item-rank; /* 아이템마다 번호 증가 */
        box-shadow: none !important;
    }

    /* 3. 왼쪽 번호 영역 (엑셀 셀 스타일) */
    .sortable-item::before {
        content: counter(item-rank); /* 자동 번호 부여 */
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 45px !important;
        height: 40px !important;
        background-color: white !important;
        color: #333 !important;
        font-weight: bold !important;
        font-size: 16px !important;
        border: 1px solid #ccc !important; /* 엑셀 격자 스타일 */
        margin-right: 15px !important; /* 번호와 버튼 사이 간격 */
        flex-shrink: 0 !important;
    }

    /* 4. 오른쪽 내용 영역 (빨간색 버튼 스타일) */
    .sortable-item > div:last-child {
        background-color: #ff4b4b !important; /* 빨간색 배경 */
        color: white !important;
        border-radius: 8px !important; /* 둥근 모서리 */
        padding: 0 15px !important;
        height: 40px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 100% !important;
        font-weight: 500 !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
    }

    /* 호버 효과 */
    .sortable-item:hover > div:last-child {
        background-color: #ff3333 !important;
        transform: translateY(-1px);
    }

    /* 헤더 및 불필요한 요소 제거 */
    .sortable-container-header { display: none !important; }
    div[data-testid="stVerticalBlock"] > div > div > div > div.stMarkdown { margin-bottom: 0px !important; }
</style>
""", unsafe_allow_html=True)

# --- 이하 데이터 로드 및 저장 로직은 기존과 동일 ---

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
        except: worksheet = doc.add_worksheet(title="config", rows=10, cols=10)
        json_str = json.dumps(order_data, ensure_ascii=False)
        worksheet.update_acell('A1', json_str)
        return True
    except: return False

def sync_order_with_data(saved_order, df):
    live_cat1 = sorted(list(df['분류1'].dropna().unique()))
    current_cat1_order = saved_order.get('분류1_순서', [])
    new_cat1_order = [c for c in current_cat1_order if c in live_cat1]
    for c in live_cat1:
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

# --- 메인 UI 영역 ---

def show_navigation():
    col1, col2, col3 = st.columns([4, 1, 1])
    with col1: st.markdown("## ⚙️ 순서 설정")
    with col2:
        if st.button("🏠 대시보드"): st.session_state.page = "dashboard"; st.rerun()
    with col3:
        if st.button("🔄 새로고침"): st.cache_data.clear(); st.rerun()

def show_settings():
    df = load_data()
    if df.empty: return
    
    if 'page_order' not in st.session_state:
        saved_order = load_config_from_sheet()
        st.session_state.page_order = sync_order_with_data(saved_order or {'분류1_순서': [], '분류2_순서': {}}, df)

    tab1, tab2, tab3 = st.tabs(["📂 분류1 순서", "📁 분류2 순서", "💾 저장"])

    with tab1:
        st.info("💡 카테고리 버튼을 드래그하여 순서를 변경하세요. 번호는 고정되어 있습니다.")
        current_list = st.session_state.page_order['분류1_순서']
        # 이미처럼 5열로 배치
        chunked_list = chunk_list(current_list, 5) 
        sortable_data = [{'header': '', 'items': chunk} for chunk in chunked_list]
        
        sorted_data = sort_items(sortable_data, multi_containers=True, direction='vertical', key='sort_cat1_v5')
        new_order = [item for container in sorted_data for item in container['items']]
        
        if new_order != current_list:
            st.session_state.page_order['분류1_순서'] = new_order
            st.rerun()

    with tab2:
        selected_cat1 = st.selectbox("대분류 선택", st.session_state.page_order['분류1_순서'])
        current_sub = st.session_state.page_order['분류2_순서'].get(selected_cat1, ['전체'])
        
        chunked_sub = chunk_list(current_sub, 4)
        sorted_sub_data = sort_items([{'header': '', 'items': c} for c in chunked_sub], multi_containers=True, key=f'sort_cat2_{selected_cat1}')
        
        new_sub_order = [item for container in sorted_sub_data for item in container['items']]
        if new_sub_order != current_sub:
            st.session_state.page_order['분류2_순서'][selected_cat1] = new_sub_order
            st.rerun()

    with tab3:
        if st.button("💾 구글 시트에 최종 저장", type="primary", use_container_width=True):
            if save_config_to_sheet(st.session_state.page_order):
                st.success("✅ 저장이 완료되었습니다!")
            else: st.error("❌ 저장 실패")

def main():
    if 'page' not in st.session_state: st.session_state.page = "settings"
    show_navigation()
    if st.session_state.page == "settings": show_settings()

if __name__ == "__main__":
    main()
