import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json
from datetime import datetime

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
    .main {
        padding: 0rem 1rem;
    }
    
    /* 네비게이션 버튼 스타일 */
    .nav-button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.75rem 1.5rem;
        border: none;
        border-radius: 10px;
        font-size: 16px;
        font-weight: bold;
        cursor: pointer;
        margin: 0 0.5rem;
        transition: all 0.3s ease;
        display: inline-block;
        text-decoration: none;
    }
    
    .nav-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
    }
    
    /* 메트릭 카드 스타일 */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        text-align: center;
        margin-bottom: 1rem;
    }
    
    .metric-card h3 {
        font-size: 2rem;
        margin: 0;
        font-weight: bold;
    }
    
    .metric-card p {
        font-size: 0.9rem;
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
    }
    
    /* 분류 버튼 컨테이너 */
    .category-buttons {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin: 1rem 0;
        padding: 1rem;
        background: #f8f9fa;
        border-radius: 10px;
    }
    
    /* 분류 버튼 스타일 */
    .category-btn {
        padding: 0.75rem 1.5rem;
        border: 2px solid #667eea;
        border-radius: 25px;
        background: white;
        color: #667eea;
        font-weight: bold;
        cursor: pointer;
        transition: all 0.3s ease;
        flex: 0 0 auto;
        min-width: 150px;
        text-align: center;
    }
    
    .category-btn:hover {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        transform: translateY(-2px);
        box-shadow: 0 4px 10px rgba(102, 126, 234, 0.3);
    }
    
    .category-btn.active {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        border-color: #f5576c;
    }
    
    /* 테이블 스타일 */
    .dataframe {
        font-size: 14px;
    }
    
    .dataframe thead th {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: bold;
        padding: 12px;
        text-align: center;
    }
    
    .dataframe tbody td {
        padding: 10px;
        border-bottom: 1px solid #e0e0e0;
    }
    
    /* 드래그 아이템 스타일 */
    .drag-item {
        background: white;
        border: 2px solid #667eea;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        cursor: move;
        transition: all 0.3s ease;
    }
    
    .drag-item:hover {
        background: #f8f9fa;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# 한국식 숫자 포맷 함수
def format_korean_number(num):
    """숫자를 한국식으로 포맷 (예: 1,500,000 → 150만)"""
    if pd.isna(num) or num == 0:
        return "0"
    
    num = int(num)
    
    if num >= 100000000:  # 1억 이상
        eok = num // 100000000
        man = (num % 100000000) // 10000
        if man > 0:
            return f"{eok}.{man//1000}억"
        return f"{eok}억"
    elif num >= 10000:  # 1만 이상
        man = num // 10000
        cheon = (num % 10000) // 1000
        if cheon > 0:
            return f"{man}.{cheon}만"
        return f"{man}만"
    else:
        return f"{num:,}"

# 구글 시트 연결
@st.cache_data(ttl=600)
def load_data():
    """구글 시트에서 데이터 로드"""
    try:
        # Secrets에서 서비스 계정 정보 가져오기
        credentials_dict = dict(st.secrets["gcp_service_account"])
        
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            credentials_dict, scope)
        client = gspread.authorize(credentials)
        
        # 시트 열기
        sheet = client.open("유튜브보물창고_테스트").sheet1
        
        # 데이터 가져오기
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        # 숫자 컬럼 변환
        numeric_columns = ['구독자', '동영상', '조회수', '최근 5개 토탈', 
                          '최근 10개 토탈', '최근 20개 토탈', '최근 30개 토탈']
        
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0).astype(int)
        
        return df
    
    except Exception as e:
        st.error(f"데이터 로드 실패: {str(e)}")
        return pd.DataFrame()

# 페이지 네비게이션
def show_navigation():
    """상단 네비게이션 바"""
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    
    with col1:
        st.markdown("# 🎬 YouTube 보물창고")
    
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

# 대시보드 페이지
def show_dashboard():
    """메인 대시보드 페이지"""
    df = load_data()
    
    if df.empty:
        st.warning("데이터를 불러올 수 없습니다.")
        return
    
    # 분류1 목록 가져오기
    분류1_list = []
    if 'page_order' in st.session_state and '분류1_순서' in st.session_state.page_order:
        분류1_list = st.session_state.page_order['분류1_순서']
    else:
        분류1_list = sorted(df['분류1'].dropna().unique().tolist())
    
    # 세션 상태 초기화
    if 'selected_분류1' not in st.session_state:
        st.session_state.selected_분류1 = 분류1_list[0] if 분류1_list else None
    
    # 분류1 버튼 표시
    st.markdown("### 📂 분류 선택")
    
    # 한 줄에 6개씩 배치
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
                    button_class = "active" if is_active else ""
                    
                    if st.button(
                        cat,
                        key=f"btn_{cat}_{row}_{idx}",
                        use_container_width=True,
                        type="primary" if is_active else "secondary"
                    ):
                        st.session_state.selected_분류1 = cat
                        st.rerun()
    
    st.markdown("---")
    
    # 선택된 분류1 데이터 표시
    if st.session_state.selected_분류1:
        show_category_detail(df, st.session_state.selected_분류1)

# 분류별 상세 페이지
def show_category_detail(df, 분류1):
    """특정 분류1의 상세 정보 표시"""
    # 분류1 필터링
    df_filtered = df[df['분류1'] == 분류1].copy()
    
    if df_filtered.empty:
        st.warning(f"'{분류1}' 분류에 데이터가 없습니다.")
        return
    
    # 분류2 목록 가져오기
    분류2_list = []
    if 'page_order' in st.session_state and '분류2_순서' in st.session_state.page_order:
        if 분류1 in st.session_state.page_order['분류2_순서']:
            분류2_list = st.session_state.page_order['분류2_순서'][분류1]
        else:
            분류2_list = ['전체'] + sorted(df_filtered['분류2'].dropna().unique().tolist())
    else:
        분류2_list = ['전체'] + sorted(df_filtered['분류2'].dropna().unique().tolist())
    
    # 헤더
    st.markdown(f"## 📊 {분류1}")
    
    # 분류2 필터
    col1, col2 = st.columns([1, 3])
    
    with col1:
        selected_분류2 = st.selectbox(
            "🔍 분류2 선택",
            분류2_list,
            key=f"분류2_{분류1}"
        )
    
    # 분류2 필터링
    if selected_분류2 != '전체':
        df_display = df_filtered[df_filtered['분류2'] == selected_분류2].copy()
    else:
        df_display = df_filtered.copy()
    
    # 통계 카드
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>{len(df_display)}</h3>
            <p>총 채널 수</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        total_subs = df_display['구독자'].sum()
        st.markdown(f"""
        <div class="metric-card">
            <h3>{format_korean_number(total_subs)}</h3>
            <p>총 구독자</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        total_views = df_display['조회수'].sum()
        st.markdown(f"""
        <div class="metric-card">
            <h3>{format_korean_number(total_views)}</h3>
            <p>총 조회수</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        total_recent = df_display['최근 30개 토탈'].sum()
        st.markdown(f"""
        <div class="metric-card">
            <h3>{format_korean_number(total_recent)}</h3>
            <p>최근 30개 토탈</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 검색 및 정렬
    col1, col2 = st.columns([2, 1])
    
    with col1:
        search_query = st.text_input("🔍 채널명 검색", key=f"search_{분류1}_{selected_분류2}")
    
    with col2:
        sort_by = st.selectbox(
            "정렬 기준",
            ['최근 30개 토탈', '최근 20개 토탈', '최근 10개 토탈', '최근 5개 토탈', '구독자', '조회수'],
            key=f"sort_{분류1}_{selected_분류2}"
        )
    
    # 검색 필터링
    if search_query:
        df_display = df_display[df_display['채널명'].str.contains(search_query, case=False, na=False)]
    
    # 정렬
    df_display = df_display.sort_values(by=[sort_by, '채널명'], ascending=[False, True])
    
    # 표시할 컬럼 선택
    display_columns = ['채널명', 'URL', '국가', '분류2', '구독자', '동영상', '조회수',
                       '운영기간', '최초업로드', '최근업로드',
                       '최근 5개 토탈', '최근 10개 토탈', '최근 20개 토탈', '최근 30개 토탈']
    
    # 존재하는 컬럼만 선택
    display_columns = [col for col in display_columns if col in df_display.columns]
    
    df_display_formatted = df_display[display_columns].copy()
    
    # 숫자 컬럼 포맷팅
    for col in ['구독자', '동영상', '조회수', '최근 5개 토탈', '최근 10개 토탈', '최근 20개 토탈', '최근 30개 토탈']:
        if col in df_display_formatted.columns:
            df_display_formatted[col] = df_display_formatted[col].apply(format_korean_number)
    
    # 테이블 표시
    st.markdown(f"### 📋 채널 리스트 (총 {len(df_display)}개)")
    st.dataframe(
        df_display_formatted,
        use_container_width=True,
        height=500
    )
    
    # CSV 다운로드
    csv = df_display.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 CSV 다운로드",
        data=csv,
        file_name=f"youtube_{분류1}_{selected_분류2}_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

# 설정 페이지
def show_settings():
    """순서 설정 페이지"""
    st.markdown("## ⚙️ 순서 설정")
    st.markdown("---")
    
    df = load_data()
    
    if df.empty:
        st.warning("데이터를 불러올 수 없습니다.")
        return
    
    # 세션 상태 초기화
    if 'page_order' not in st.session_state:
        st.session_state.page_order = {
            '분류1_순서': sorted(df['분류1'].dropna().unique().tolist()),
            '분류2_순서': {}
        }
        
        # 분류2 초기 순서 설정
        for cat1 in st.session_state.page_order['분류1_순서']:
            df_cat = df[df['분류1'] == cat1]
            st.session_state.page_order['분류2_순서'][cat1] = ['전체'] + sorted(df_cat['분류2'].dropna().unique().tolist())
    
    # 분류1 순서 설정
    st.markdown("### 📂 분류1 순서")
    st.info("⚠️ 드래그 앤 드롭은 현재 Streamlit에서 지원되지 않습니다. 대신 버튼을 사용해 순서를 변경하세요.")
    
    for idx, cat in enumerate(st.session_state.page_order['분류1_순서']):
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        
        with col1:
            st.markdown(f"**{idx + 1}. {cat}**")
        
        with col2:
            if idx > 0:
                if st.button("⬆️", key=f"up1_{cat}"):
                    order = st.session_state.page_order['분류1_순서']
                    order[idx], order[idx-1] = order[idx-1], order[idx]
                    st.rerun()
        
        with col3:
            if idx < len(st.session_state.page_order['분류1_순서']) - 1:
                if st.button("⬇️", key=f"down1_{cat}"):
                    order = st.session_state.page_order['분류1_순서']
                    order[idx], order[idx+1] = order[idx+1], order[idx]
                    st.rerun()
        
        with col4:
            if st.button("🔝", key=f"top1_{cat}"):
                order = st.session_state.page_order['분류1_순서']
                order.insert(0, order.pop(idx))
                st.rerun()
    
    st.markdown("---")
    
    # 분류2 순서 설정
    st.markdown("### 📁 분류2 순서")
    
    selected_cat1 = st.selectbox(
        "분류1 선택",
        st.session_state.page_order['분류1_순서'],
        key="settings_cat1_select"
    )
    
    if selected_cat1 and selected_cat1 in st.session_state.page_order['분류2_순서']:
        st.markdown(f"#### {selected_cat1}의 분류2 순서")
        
        for idx, cat in enumerate(st.session_state.page_order['분류2_순서'][selected_cat1]):
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            
            with col1:
                st.markdown(f"**{idx + 1}. {cat}**")
            
            with col2:
                if idx > 0:
                    if st.button("⬆️", key=f"up2_{cat}"):
                        order = st.session_state.page_order['분류2_순서'][selected_cat1]
                        order[idx], order[idx-1] = order[idx-1], order[idx]
                        st.rerun()
            
            with col3:
                if idx < len(st.session_state.page_order['분류2_순서'][selected_cat1]) - 1:
                    if st.button("⬇️", key=f"down2_{cat}"):
                        order = st.session_state.page_order['분류2_순서'][selected_cat1]
                        order[idx], order[idx+1] = order[idx+1], order[idx]
                        st.rerun()
            
            with col4:
                if st.button("🔝", key=f"top2_{cat}"):
                    order = st.session_state.page_order['분류2_순서'][selected_cat1]
                    order.insert(0, order.pop(idx))
                    st.rerun()
    
    st.markdown("---")
    
    # 저장/초기화 버튼
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💾 순서 저장", use_container_width=True):
            st.success("✅ 순서가 저장되었습니다!")
    
    with col2:
        if st.button("🔄 초기화", use_container_width=True):
            st.session_state.page_order = {
                '분류1_순서': sorted(df['분류1'].dropna().unique().tolist()),
                '분류2_순서': {}
            }
            
            for cat1 in st.session_state.page_order['분류1_순서']:
                df_cat = df[df['분류1'] == cat1]
                st.session_state.page_order['분류2_순서'][cat1] = ['전체'] + sorted(df_cat['분류2'].dropna().unique().tolist())
            
            st.success("✅ 초기 순서로 복원되었습니다!")
            st.rerun()

# 메인 앱
def main():
    # 세션 상태 초기화
    if 'page' not in st.session_state:
        st.session_state.page = "dashboard"
    
    # 네비게이션 표시
    show_navigation()
    st.markdown("---")
    
    # 페이지 라우팅
    if st.session_state.page == "dashboard":
        show_dashboard()
    elif st.session_state.page == "settings":
        show_settings()
    
    # 푸터
    st.markdown("---")
    st.markdown(f"*마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

if __name__ == "__main__":
    main()
