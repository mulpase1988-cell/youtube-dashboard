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
</style>
""", unsafe_allow_html=True)

# 구글 시트 연결
def get_gspread_client():
    credentials_dict = dict(st.secrets["gcp_service_account"])
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
    return gspread.authorize(credentials)

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
        else: return f"{num:,}"
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

@st.cache_data(ttl=600)
def load_data():
    try:
        client = get_gspread_client()
        sheet = client.open("유튜브보물창고_테스트").sheet1
        data = sheet.get_all_records()
        if not data: return pd.DataFrame()
        df = pd.DataFrame(data)
        numeric_columns = ['구독자', '동영상', '조회수', '최근 5개 토탈', '최근 10개 토탈', '최근 20개 토탈', '최근 30개 토탈']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"데이터 로드 실패: {str(e)}")
        return pd.DataFrame()

# [개선된 저장 함수] 데이터가 지워지는 것을 방지하기 위해 안전장치 강화
def save_data_to_google_sheet(full_df):
    if full_df.empty:
        st.error("저장할 데이터가 비어있습니다. 작업을 중단합니다.")
        return False
    
    try:
        with st.spinner('구글 시트에 데이터를 안전하게 저장 중입니다...'):
            client = get_gspread_client()
            sheet = client.open("유튜브보물창고_테스트").sheet1
            
            # 모든 데이터를 문자열로 변환하고 NaN 처리 (gspread 에러 방지)
            df_to_save = full_df.copy()
            # 숫자로 된 컬럼들은 나중에 시트에서 숫자로 인식되게 하려면 문자열로 보내는 게 가장 안전함
            data_list = [df_to_save.columns.values.tolist()] + df_to_save.astype(str).replace(['nan', 'None'], '').values.tolist()
            
            # 데이터 업데이트 시 시트를 완전히 비우고 새로 씀 (덮어쓰기 오류 방지)
            sheet.clear()
            sheet.update('A1', data_list)
            return True
    except Exception as e:
        st.error(f"구글 시트 저장 중 치명적 오류 발생: {e}")
        return False

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
    if 'raw_data' not in st.session_state or st.session_state.raw_data.empty:
        st.session_state.raw_data = load_data()
    
    df = st.session_state.raw_data
    if df.empty:
        st.warning("데이터가 없습니다. 구글 시트를 확인하거나 새로고침 하세요.")
        return
    
    # 설정 로드
    if 'page_order' not in st.session_state:
        # 설정 로드 함수들은 이전과 동일하게 유지
        from oauth2client.service_account import ServiceAccountCredentials
        def load_config():
            try:
                client = get_gspread_client()
                doc = client.open("유튜브보물창고_테스트")
                ws = doc.worksheet("config")
                return json.loads(ws.acell('A1').value)
            except: return None
        
        saved = load_config()
        # sync_order_with_data는 이전 코드와 동일하다고 가정
        def sync_order(saved_order, df):
            if not saved_order: saved_order = {'분류1_순서': [], '분류2_순서': {}, '채널_순서': {}}
            live_cat1 = sorted(list(set(df['분류1'].dropna().unique())))
            saved_order['분류1_순서'] = [c for c in saved_order.get('분류1_순서', []) if c in live_cat1]
            for c in live_cat1:
                if c not in saved_order['분류1_순서']: saved_order['분류1_순서'].append(c)
            return saved_order
            
        st.session_state.page_order = sync_order(saved, df)

    cat1_list = st.session_state.page_order['분류1_순서']
    if 'selected_분류1' not in st.session_state: st.session_state.selected_분류1 = cat1_list[0] if cat1_list else None
    
    with st.sidebar:
        st.markdown("## 📂 분류 선택")
        for cat in cat1_list:
            if st.button(cat, key=f"side_{cat}", use_container_width=True, type="primary" if st.session_state.selected_분류1 == cat else "secondary"):
                st.session_state.selected_분류1 = cat
                st.rerun()
    
    if st.session_state.selected_분류1:
        show_category_detail(df, st.session_state.selected_분류1)

def show_category_detail(df, 분류1):
    col_t, col_sw = st.columns([3, 1])
    with col_t: st.markdown(f"## 📊 {분류1}")
    with col_sw: edit_mode = st.toggle("✏️ 데이터 수정 모드", key=f"edit_toggle_{분류1}")

    df_filtered = df[df['분류1'] == 분류1].copy()
    
    # [생략된 분류2 버튼, 검색, 정렬 로직은 이전과 동일...]
    # 중요: 수정 모드 로직 개선
    display_columns = ['채널명', '분류2', '메모', '운영기간', '동영상', '조회수', '최근 5개 토탈', '최근 10개 토탈', '최근 20개 토탈', '최근 30개 토탈', '키워드', 'URL']
    
    if edit_mode:
        st.info("💡 수정 후 하단의 저장 버튼을 꼭 눌러주세요.")
        # 에디터 표시
        edited_df = st.data_editor(
            df_filtered[display_columns],
            use_container_width=True,
            num_rows="fixed", # 안전을 위해 행 추가/삭제 방지
            key=f"editor_{분류1}",
            hide_index=True
        )
        
        if st.button("💾 이 카테고리 변경사항 저장", type="primary"):
            # 수정한 데이터를 원본 데이터프레임에 매핑 (채널명 기준)
            for _, row in edited_df.iterrows():
                channel = row['채널명']
                idx = st.session_state.raw_data.index[st.session_state.raw_data['채널명'] == channel]
                if not idx.empty:
                    for col in display_columns:
                        st.session_state.raw_data.at[idx[0], col] = row[col]
            
            # 구글 시트에 최종 저장
            if save_data_to_google_sheet(st.session_state.raw_data):
                st.success("변경사항이 구글 시트에 안전하게 저장되었습니다.")
                st.cache_data.clear()
                st.rerun()
    else:
        # 보기 모드 (포맷팅 적용)
        df_show = df_filtered[display_columns].copy()
        num_cols = ['동영상', '조회수', '최근 5개 토탈', '최근 10개 토탈', '최근 20개 토탈', '최근 30개 토탈']
        for c in num_cols: df_show[c] = df_show[c].apply(format_korean_number)
        
        st.dataframe(df_show, use_container_width=True, height=600, hide_index=True, column_config={
            "URL": st.column_config.LinkColumn("링크", display_text="보러가기")
        })

def main():
    if 'page' not in st.session_state: st.session_state.page = "dashboard"
    show_navigation()
    st.markdown("---")
    if st.session_state.page == "dashboard": show_dashboard()
    # 설정 페이지 함수는 기존 그대로 유지하시면 됩니다.

if __name__ == "__main__":
    main()
