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
    
    /* 카드 스타일 (순서 설정용) */
    .order-card {
        background: white;
        border: 2px solid #e0e0e0;
        border-radius: 15px;
        padding: 1.5rem;
        margin: 0.5rem;
        transition: all 0.3s ease;
        cursor: move;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .order-card:hover {
        border-color: #667eea;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        transform: translateY(-2px);
    }
    
    .order-card-header {
        display: flex;
        align-items: center;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #f0f0f0;
    }
    
    .order-card-number {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        font-size: 18px;
        margin-right: 1rem;
    }
    
    .order-card-title {
        font-size: 1.3rem;
        font-weight: bold;
        color: #333;
        flex: 1;
    }
    
    .order-card-count {
        color: #667eea;
        font-size: 0.9rem;
        font-weight: 600;
    }
    
    .order-card-content {
        margin: 1rem 0;
    }
    
    .order-card-subtitle {
        font-size: 0.85rem;
        color: #666;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    
    .order-card-items {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
    }
    
    .order-card-item {
        background: #f8f9fa;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.85rem;
        color: #555;
        border: 1px solid #e0e0e0;
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
    
    /* 그리드 레이아웃 */
    .grid-container {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1rem;
        margin: 1rem 0;
    }
    
    @media (max-width: 1400px) {
        .grid-container {
            grid-template-columns: repeat(3, 1fr);
        }
    }
    
    @media (max-width: 1000px) {
        .grid-container {
            grid-template-columns: repeat(2, 1fr);
        }
    }
    
    @media (max-width: 600px) {
        .grid-container {
            grid-template-columns: 1fr;
        }
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

# 설정 페이지 - 카드 레이아웃
def show_settings():
    """순서 설정 페이지 - 카드 그리드 방식"""
    st.markdown("## ⚙️ 순서 설정")
    
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
    
    # 통계 표시
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>{len(st.session_state.page_order['분류1_순서'])}</h3>
            <p>총 분류1</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        total_cat2 = sum(len(v) - 1 for v in st.session_state.page_order['분류2_순서'].values())  # '전체' 제외
        st.markdown(f"""
        <div class="metric-card">
            <h3>{total_cat2}</h3>
            <p>총 분류2</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3>{len(df)}</h3>
            <p>총 채널</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <h3>드래그</h3>
            <p>순서 변경</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 분류1 카드 그리드
    st.markdown("### 📂 분류1 순서 (전체 보기)")
    st.info("💡 팁: 각 카드의 버튼으로 순서를 변경하거나, [편집]을 클릭해 분류2 순서를 조정하세요.")
    
    # 4열 그리드로 카드 배치
    cards_per_row = 4
    분류1_list = st.session_state.page_order['분류1_순서']
    num_rows = (len(분류1_list) + cards_per_row - 1) // cards_per_row
    
    for row in range(num_rows):
        cols = st.columns(cards_per_row)
        start_idx = row * cards_per_row
        end_idx = min(start_idx + cards_per_row, len(분류1_list))
        
        for idx, col in enumerate(cols):
            if start_idx + idx < end_idx:
                cat_idx = start_idx + idx
                cat = 분류1_list[cat_idx]
                
                # 해당 분류의 채널 수 계산
                df_cat = df[df['분류1'] == cat]
                channel_count = len(df_cat)
                
                # 분류2 목록
                if cat in st.session_state.page_order['분류2_순서']:
                    cat2_list = st.session_state.page_order['분류2_순서'][cat]
                else:
                    cat2_list = ['전체']
                
                with col:
                    # 카드 생성
                    with st.container():
                        st.markdown(f"""
                        <div class="order-card">
                            <div class="order-card-header">
                                <div class="order-card-number">☰ {cat_idx + 1}</div>
                                <div class="order-card-title">{cat}</div>
                            </div>
                            <div class="order-card-count">채널 {channel_count}개</div>
                            <div class="order-card-content">
                                <div class="order-card-subtitle">📁 분류2 ({len(cat2_list)}개)</div>
                                <div class="order-card-items">
                                    {''.join([f'<span class="order-card-item">• {c2}</span>' for c2 in cat2_list[:5]])}
                                    {f'<span class="order-card-item">...외 {len(cat2_list)-5}개</span>' if len(cat2_list) > 5 else ''}
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # 버튼 영역
                        btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
                        
                        with btn_col1:
                            if cat_idx > 0:
                                if st.button("⬆️", key=f"up_{cat}_{row}", help="위로"):
                                    order = st.session_state.page_order['분류1_순서']
                                    order[cat_idx], order[cat_idx-1] = order[cat_idx-1], order[cat_idx]
                                    st.rerun()
                        
                        with btn_col2:
                            if cat_idx < len(분류1_list) - 1:
                                if st.button("⬇️", key=f"down_{cat}_{row}", help="아래로"):
                                    order = st.session_state.page_order['분류1_순서']
                                    order[cat_idx], order[cat_idx+1] = order[cat_idx+1], order[cat_idx]
                                    st.rerun()
                        
                        with btn_col3:
                            if st.button("📝", key=f"edit_{cat}_{row}", help="분류2 편집"):
                                st.session_state.editing_category = cat
                                st.rerun()
                        
                        with btn_col4:
                            if st.button("🔝", key=f"top_{cat}_{row}", help="맨 위로"):
                                order = st.session_state.page_order['분류1_순서']
                                order.insert(0, order.pop(cat_idx))
                                st.rerun()
    
    st.markdown("---")
    
    # 분류2 편집 모달
    if 'editing_category' in st.session_state and st.session_state.editing_category:
        show_category2_editor(df, st.session_state.editing_category)
    
    # 하단 버튼
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("💾 순서 저장", use_container_width=True):
            st.success("✅ 순서가 저장되었습니다!")
            st.balloons()
    
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
    
    with col3:
        # 순서 내보내기
        order_json = json.dumps(st.session_state.page_order, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 순서 내보내기",
            data=order_json,
            file_name=f"youtube_order_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col4:
        if st.button("❌ 편집 닫기", use_container_width=True):
            if 'editing_category' in st.session_state:
                del st.session_state.editing_category
                st.rerun()

# 분류2 편집기
def show_category2_editor(df, 분류1):
    """분류2 순서 편집 모달"""
    st.markdown("---")
    st.markdown(f"### 📁 '{분류1}'의 분류2 순서 편집")
    
    if 분류1 not in st.session_state.page_order['분류2_순서']:
        st.warning(f"'{분류1}'의 분류2 정보가 없습니다.")
        return
    
    분류2_list = st.session_state.page_order['분류2_순서'][분류1]
    
    # 리스트 형태로 표시
    for idx, cat2 in enumerate(분류2_list):
        col1, col2, col3, col4, col5 = st.columns([0.5, 3, 1, 1, 1])
        
        with col1:
            st.markdown(f"**{idx + 1}**")
        
        with col2:
            st.markdown(f"📌 {cat2}")
        
        with col3:
            if idx > 0:
                if st.button("⬆️", key=f"up2_{분류1}_{cat2}"):
                    order = st.session_state.page_order['분류2_순서'][분류1]
                    order[idx], order[idx-1] = order[idx-1], order[idx]
                    st.rerun()
        
        with col4:
            if idx < len(분류2_list) - 1:
                if st.button("⬇️", key=f"down2_{분류1}_{cat2}"):
                    order = st.session_state.page_order['분류2_순서'][분류1]
                    order[idx], order[idx+1] = order[idx+1], order[idx]
                    st.rerun()
        
        with col5:
            if st.button("🔝", key=f"top2_{분류1}_{cat2}"):
                order = st.session_state.page_order['분류2_순서'][분류1]
                order.insert(0, order.pop(idx))
                st.rerun()
    
    # 닫기 버튼
    if st.button("✅ 편집 완료", use_container_width=True):
        del st.session_state.editing_category
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
