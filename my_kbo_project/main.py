import streamlit as st

st.set_page_config(
    page_title="KBO Scouting Report 2025",
    page_icon="⚾",
)

st.write("# ⚾ 2025 KBO Scouting Report")

st.markdown(
    """
    2025 시즌 KBO 선수들의 데이터를 기반으로 한 스카우팅 리포트입니다.
    왼쪽 사이드바에서 **Pitcher Report** 또는 **Hitter Report**를 선택해주세요.
    
    ### 주요 기능
    - **Capability Radar**: 선수의 능력치를 시각화하여 보여줍니다.
    - **Identity Analysis**: 데이터를 기반으로 선수의 스타일(파워 피처, 컨택형 타자 등)을 정의합니다.
    - **Similarity Search**: 해당 선수와 가장 유사한 성적을 낸 선수를 찾아줍니다.
    """
)