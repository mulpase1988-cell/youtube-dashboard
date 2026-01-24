import streamlit as st
import pandas as pd
from streamlit_sortables import sort_items

# --- [1] 디자인 커스텀 CSS ---
st.markdown("""
<style>
    /* 전체 컨테이너 카운터 초기화 */
    [data-testid="stVerticalBlock"] > div:has(.sortable-container) {
        counter-reset: rank-counter;
    }

    /* 드래그 항목 전체 레이아웃 */
    .sortable-item {
        display: flex !important;
        align-items: center !important;
        margin-bottom: 12px !important;
        background: transparent !important;
        border: none !important;
    }

    /* [고정 번호 영역] 엑셀 셀 느낌의 왼쪽 번호 */
    .sortable-item::before {
        counter-increment: rank-counter;
        content: counter(rank-counter);
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 50px !important;
        height: 45px !important;
        background-color: #ffffff !important;
        color: #333 !important;
        font-weight: bold !important;
        font-size: 1.1em !important;
        border: 1px solid #d1d3d4 !important; /* 엑셀 테두리 느낌 */
        margin-right: -1px !important; /* 버튼과 밀착 */
        flex-shrink: 0 !important;
        box-shadow: inset 0 0 2px rgba(0,0,0,0.05);
    }

    /* [드래그 버튼 영역] 빨간색 라운드 버튼 */
    .sortable-item > div:last-child {
        background-color: #ff4b4b !important; /* 유튜브 레드 */
        color: white !important;
        border-radius: 0 8px 8px 0 !important; /* 오른쪽만 둥글게 */
        padding: 0 20px !important;
        height: 45px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        width: 100% !important;
        font-weight: 600 !important;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1) !important;
        cursor: grab !important;
    }

    .sortable-item:active > div:last-child {
        cursor: grabbing !important;
        background-color: #d32f2f !important;
    }
</style>
""", unsafe_allow_html=True)

# --- [2] 데이터 및 로직 ---
def show_settings():
    st.title("⚙️ 순서 설정")
    
    # 예시 데이터 (실제 데이터 로드 로직으로 대체 가능)
    if '분류1_순서' not in st.session_state:
        st.session_state['분류1_순서'] = ["연예인", "예능", "cctv", "감동", "게임", "격투기", "고래"]

    st.info("💡 오른쪽 빨간색 버튼을 드래그하여 순서를 변경하세요. 번호는 고정됩니다.")

    # 드래그 앤 드롭 컴포넌트 호출
    current_items = st.session_state['분류1_순서']
    sorted_items = sort_items(current_items, direction='vertical', key='v_sort')

    # 순서 변경 시 세션 상태 업데이트 및 반영
    if sorted_items != current_items:
        st.session_state['분류1_순서'] = sorted_items
        st.rerun()

    # 저장 버튼
    if st.button("💾 순서 저장하기", type="primary"):
        st.success(f"변경된 순서: {', '.join(st.session_state['분류1_순서'])}")

if __name__ == "__main__":
    show_settings()
