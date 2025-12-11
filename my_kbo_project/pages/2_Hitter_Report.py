import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy.spatial import distance

# ---------------------------------------------------------
# 1. 페이지 및 스타일 설정
# ---------------------------------------------------------
st.set_page_config(page_title="Pro KBO Hitter Scouting Report", layout="wide")

st.markdown("""
<style>
    div[data-testid="stMetricValue"] {
        font-size: 26px;
        font-weight: bold;
    }
    .style-card {
        padding: 20px;
        border-radius: 10px;
        background-color: #f0f2f6;
        border-left: 5px solid #29b5e8;
        margin-bottom: 20px;
    }
    .dark-mode .style-card {
        background-color: #262730;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 데이터 로드 및 전처리
# ---------------------------------------------------------
@st.cache_data
def load_data():
    import os
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    
    # [수정 1] 방금 수집한 최신 파일명으로 변경
    # (파일이 같은 폴더에 있다면 parent_dir 대신 current_dir 사용)
    csv_filename = "kbo_hitter_2025_pagination_fix.csv" 
    
    # 같은 폴더 우선 검색, 없으면 상위 폴더 검색
    if os.path.exists(os.path.join(current_dir, csv_filename)):
        csv_path = os.path.join(current_dir, csv_filename)
    else:
        csv_path = os.path.join(parent_dir, csv_filename)
    
    if not os.path.exists(csv_path):
        st.error(f"데이터 파일을 찾을 수 없습니다: {csv_filename}")
        return pd.DataFrame()

    df = pd.read_csv(csv_path)
    
    # 수치형 변환
    numeric_cols = ['AVG', 'SLG', 'OBP', 'OPS', 'RISP', 'PH-BA', 'GO/AO', 'BB/K', 'P/PA', 'ISOP', 'HR', 'RBI', 'PA', 'GPA']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).replace({'-': '0'}), errors='coerce').fillna(0.0)

    # [수정 2] 동명이인 구분을 위한 '표시용 이름' 생성
    # ID가 있다면 "이주형 (67341)" 형태로 만들어 구분
    if 'ID' in df.columns:
        df['display_name'] = df.apply(lambda x: f"{x['선수명']} ({str(x['ID'])[-4:]})", axis=1)
    else:
        df['display_name'] = df['선수명']

    return df

df = load_data()

if df.empty:
    st.stop()

# ---------------------------------------------------------
# 3. 타자 스타일 판정 로직
# ---------------------------------------------------------
def determine_hitter_style(row):
    avg = row['AVG']
    isop = row['ISOP']
    bb_k = row['BB/K']
    ops = row['OPS']
    hr = row['HR']
    
    if isop >= 0.200 or hr >= 20:
        if avg >= 0.280: return "Elite Bomber", "정확도와 파괴력을 겸비한 리그 최정상급 강타자입니다.", "💣👑"
        else: return "Power Slugger", "한 방으로 경기 흐름을 뒤바꿀 수 있는 전형적인 거포입니다.", "💣"
    elif avg >= 0.310:
        if row.get('SO', 0) < row.get('BB', 0): return "Contact Master", "배트 컨트롤이 예술이며 좀처럼 삼진을 당하지 않습니다.", "🎨🪄"
        else: return "Sprinter / Hitter", "높은 타율로 팀의 공격 물꼬를 트는 안타 제조기입니다.", "🏃‍♂️🏏"
    elif bb_k >= 0.8 or row['OBP'] >= 0.380: return "Eagle Eye", "뛰어난 선구안으로 투수를 괴롭히며 꾸준히 출루합니다.", "👁️🥎"
    elif row['RISP'] >= avg + 0.05 and row['RBI'] > 50: return "Clutch Hitter", "찬스에 유독 강하며 해결사 본능을 가지고 있습니다.", "🔥💪"
    else:
        if ops > 0.750: return "Solid Regular", "준수한 타격 능력을 갖춘 팀의 주축 선수입니다.", "🛡️"
        else: return "Developing Hitter", "성장 가능성을 보여주는 유망주 혹은 백업 자원입니다.", "🌱"

# ---------------------------------------------------------
# 4. 사이드바 및 선수 선택
# ---------------------------------------------------------
st.sidebar.header("🔍 Player Finder")

# 팀 선택
team_list = sorted(df['팀명'].unique())
selected_team = st.sidebar.selectbox("Select Team", team_list)

# [수정 3] 선수 선택 (동명이인 처리된 display_name 사용)
# 팀 내 선수 필터링
team_players = df[df['팀명'] == selected_team].sort_values(by='선수명')
player_list = team_players['display_name'].unique()

selected_player_display = st.sidebar.selectbox("Select Player", player_list)

# 선택된 선수 데이터 추출 (display_name 기준)
player_data = df[df['display_name'] == selected_player_display].iloc[0]
selected_player_real_name = player_data['선수명'] # 실제 이름 별도 저장

# --- 비교군 설정 ---
st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Analysis Settings")

pa_threshold = 200 
is_regular = player_data['PA'] >= pa_threshold

group_option = st.sidebar.radio(
    "Compare Group:",
    ("Regulars (PA ≥ 200)", "All Hitters (PA ≥ 0)"), # [수정 4] 필터 조건 완화 표시
    index=0 if is_regular else 1
)

if "Regulars" in group_option:
    ref_df = df[df['PA'] >= pa_threshold]
else:
    # [수정 5] 모든 선수 보기 위해 최소 타석 기준 제거 (0으로 설정)
    ref_df = df[df['PA'] >= 0]

st.sidebar.caption(f"Comparing with **{len(ref_df)}** hitters.")

# ---------------------------------------------------------
# 5. 백분위 및 차트
# ---------------------------------------------------------
def calculate_percentile(value, column, lower_is_better=False):
    values = ref_df[column].dropna().values
    if len(values) == 0: return 0
    if lower_is_better: score = (values >= value).mean() * 100
    else: score = (values <= value).mean() * 100
    return score

stats_to_plot = {
    'Contact (AVG)': calculate_percentile(player_data['AVG'], 'AVG'),
    'Power (ISO)': calculate_percentile(player_data['ISOP'], 'ISOP'),
    'Eye (BB/K)': calculate_percentile(player_data['BB/K'], 'BB/K'),
    'Clutch (RISP)': calculate_percentile(player_data['RISP'], 'RISP'),
    'Value (GPA)': calculate_percentile(player_data['GPA'], 'GPA')
}

# ---------------------------------------------------------
# 6. 대시보드 UI
# ---------------------------------------------------------
st.title(f"⚾ {selected_player_real_name} Scouting Report")
st.markdown(f"**Team:** {player_data['팀명']} | **PA:** {int(player_data['PA'])} (Avg {player_data['AVG']:.3f})")

# 순위 계산
def get_rank_str(value, col, ascending=False):
    if len(ref_df) == 0: return "-"
    rank = ref_df[col].rank(ascending=ascending, method='min')
    # 동명이인이 있을 수 있으므로 display_name으로 매칭
    # ref_df에도 display_name이 있으므로 이를 이용
    p_rank = rank[ref_df['display_name'] == selected_player_display]
    if len(p_rank) > 0:
        return f"#{int(p_rank.values[0])}/{len(ref_df)}"
    return "-"

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
kpi1.metric("AVG", f"{player_data['AVG']:.3f}", f"Rank: {get_rank_str(player_data['AVG'], 'AVG')}", delta_color="off")
kpi2.metric("HR", f"{int(player_data['HR'])}", f"Rank: {get_rank_str(player_data['HR'], 'HR')}", delta_color="off")
kpi3.metric("RBI", f"{int(player_data['RBI'])}", f"Rank: {get_rank_str(player_data['RBI'], 'RBI')}", delta_color="off")
kpi4.metric("OPS", f"{player_data['OPS']:.3f}", f"Rank: {get_rank_str(player_data['OPS'], 'OPS')}", delta_color="off")
kpi5.metric("GPA", f"{player_data['GPA']:.3f}", f"Rank: {get_rank_str(player_data['GPA'], 'GPA')}", delta_color="off")

st.markdown("---")

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("🕸️ 5-Tool Capability")
    categories = list(stats_to_plot.keys())
    values = list(stats_to_plot.values())
    categories.append(categories[0])
    values.append(values[0])

    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=values, theta=categories, fill='toself',
        name=selected_player_real_name, line_color='#29B5E8', opacity=0.7
    ))
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100], ticksuffix="%")),
        showlegend=False, margin=dict(t=20, b=20)
    )
    st.plotly_chart(fig_radar, use_container_width=True)

with col_right:
    st.subheader("🔎 Hitting Identity")
    style_title, style_desc, style_icon = determine_hitter_style(player_data)
    
    st.markdown(f"""
    <div style="padding: 20px; border-radius: 10px; background-color: rgba(41, 181, 232, 0.15); border-left: 5px solid #29B5E8;">
        <h3 style="margin:0; display:flex; align-items:center;">
            <span style="font-size: 1.5em; margin-right: 10px;">{style_icon}</span> {style_title}
        </h3>
        <p style="margin-top: 10px; font-size: 1.1em; color: gray;">
            {style_desc}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("IsoP (Power)", f"{player_data['ISOP']:.3f}")
    c2.metric("BB/K (Eye)", f"{player_data['BB/K']:.2f}")
    risp_diff = player_data['RISP'] - player_data['AVG']
    c3.metric("RISP (Clutch)", f"{player_data['RISP']:.3f}", delta=f"{risp_diff:+.3f} vs AVG")

st.markdown("---")
st.subheader("🎯 League Context (OBP vs SLG)")

fig_scatter = px.scatter(
    ref_df, x='OBP', y='SLG', 
    hover_name='display_name', 
    color_discrete_sequence=['#cccccc'], opacity=0.6,
    labels={'OBP': 'On-Base Percentage', 'SLG': 'Slugging Percentage'}
)

highlight = ref_df[ref_df['display_name'] == selected_player_display]
fig_scatter.add_trace(go.Scatter(
    x=highlight['OBP'], y=highlight['SLG'],
    mode='markers', marker=dict(color='#29B5E8', size=12, line=dict(width=2, color='black')),
    name=selected_player_real_name
))
st.plotly_chart(fig_scatter, use_container_width=True)

st.markdown("### 👯 Similar Hitters")
sim_cols = ['AVG', 'HR', 'OPS', 'BB/K', 'ISOP']
sim_df = ref_df.dropna(subset=sim_cols).copy()

if not sim_df.empty and len(sim_df) > 1:
    norm_df = (sim_df[sim_cols] - sim_df[sim_cols].mean()) / sim_df[sim_cols].std()
    
    # 내 벡터 찾기
    if selected_player_display in sim_df['display_name'].values:
        target_idx = sim_df[sim_df['display_name'] == selected_player_display].index[0]
        target_vec = norm_df.loc[target_idx].values
        
        distances = []
        for idx, row in norm_df.iterrows():
            if idx == target_idx: continue
            dist = distance.euclidean(target_vec, row.values)
            distances.append({
                '선수명': sim_df.loc[idx]['display_name'], # 표시용 이름 사용
                '팀명': sim_df.loc[idx]['팀명'], 
                'OPS': sim_df.loc[idx]['OPS'], 
                'dist': dist
            })
            
        top3 = sorted(distances, key=lambda x: x['dist'])[:3]
        
        sc1, sc2, sc3 = st.columns(3)
        for i, col in enumerate([sc1, sc2, sc3]):
            if i < len(top3):
                p = top3[i]
                col.info(f"**{p['선수명']}** ({p['팀명']})\n\nOPS: {p['OPS']:.3f}")
    else:
        st.warning("선수 데이터 부족으로 유사 타자를 찾을 수 없습니다.")
else:
    st.warning("비교군 데이터가 충분하지 않습니다.")

st.markdown("### 📋 Season Stats Detail")
display_cols = ['G', 'PA', 'AB', 'R', 'H', 'HR', 'RBI', 'BB', 'SO', 'AVG', 'OBP', 'SLG', 'OPS', 'RISP', 'GPA']
st.dataframe(
    pd.DataFrame([player_data[display_cols]]).style.format({
        'AVG': '{:.3f}', 'OBP': '{:.3f}', 'SLG': '{:.3f}', 'OPS': '{:.3f}', 'RISP': '{:.3f}', 'GPA': '{:.3f}'
    }),
    use_container_width=True, hide_index=True
)
