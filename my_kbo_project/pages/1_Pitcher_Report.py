import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy.spatial import distance

# ---------------------------------------------------------
# 1. 페이지 및 스타일 설정
# ---------------------------------------------------------
st.set_page_config(page_title="Pro KBO Pitcher Scouting Report", layout="wide")

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
        border-left: 5px solid #ff4b4b;
        margin-bottom: 20px;
    }
    .dark-mode .style-card {
        background-color: #262730;
    }
    /* 배지 스타일 */
    .badge-ace {
        background-color: #FFD700;
        color: black;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 0.8em;
        margin-left: 8px;
    }
    .badge-pilseung {
        background-color: #1E90FF;
        color: white;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 0.8em;
        margin-left: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 데이터 로드 및 전처리
# ---------------------------------------------------------
@st.cache_data
def load_data():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    csv_path = os.path.join(parent_dir, "kbo_pitcher_2025_tabs_final.csv")
    
    df = pd.read_csv(csv_path)
    
    def parse_ip(val):
        val = str(val)
        try:
            if ' ' in val: 
                whole, frac = val.split(' ')
                num, den = frac.split('/')
                return float(whole) + (float(num) / float(den))
            elif '/' in val:
                num, den = val.split('/')
                return float(num) / float(den)
            else:
                return float(val)
        except:
            return 0.0

    df['IP_float'] = df['IP'].apply(parse_ip)

    def parse_go_ao(val):
        try:
            return float(val)
        except:
            return 0.0
    df['GO/AO_float'] = df['GO/AO'].apply(parse_go_ao)
    
    return df

df = load_data()

# ---------------------------------------------------------
# 3. 투구 스타일 판정 로직 함수 (업데이트됨)
# ---------------------------------------------------------
def determine_pitching_style(row):
    k_9 = row['K/9']
    bb_9 = row['BB/9']
    go_ao = row['GO/AO_float']
    era = row['ERA']
    whip = row['WHIP']
    g = row['G']
    ip = row['IP_float']
    gs = row['GS']
    
    # 불펜 여부 확인
    is_bullpen = gs <= (g / 2) if g > 0 else True
    
    # 1순위: 마당쇠 (Workhorse)
    if is_bullpen and g >= 65 and ip >= 65:
        return "Iron Man (Madang-soe)", "65경기, 65이닝 이상을 소화하며 팀을 위해 헌신한 마당쇠 유형입니다.", "💪🐎"

    # 2순위: 성장형 투수 (Developing)
    if era >= 6.00 or whip >= 1.70:
        return "Developing Pitcher", "아직 다듬어지지 않았으며, 제구와 구위의 발전이 필요한 성장형 투수입니다.", "🌱"

    # 3순위: 파워 피처
    if k_9 >= 9.0:
        if go_ao > 1.3:
            return "Power Sinkerballer", "강력한 구위로 삼진과 땅볼을 동시에 유도하는 까다로운 유형입니다.", "🔥🪨"
        else:
            return "Power Pitcher", "압도적인 구위로 타자를 찍어 누르는 '닥터 K' 유형입니다.", "🔥"
            
    # 4순위: 피네스 피처
    elif bb_9 <= 2.5:
        if go_ao > 1.3:
            return "Control Artist (Ground)", "정교한 제구력으로 땅볼을 유도해 투구수를 아끼는 유형입니다.", "🎨🪨"
        else:
            return "Finesse Pitcher", "구속보다는 칼 같은 제구력과 수싸움으로 타자를 요리합니다.", "🎨"
            
    # 5순위: 솔리드 레귤러 (Solid Regular)
    elif era <= 4.80:
        return "Solid Regular", "준수한 투구 능력을 바탕으로 팀 마운드의 중심을 잡아주는 주축 선수입니다.", "🛡️"

    # 6순위: 그 외
    else:
        if go_ao > 1.15:
            return "Groundball Pitcher", "맞춰 잡는 능력이 좋으며 내야 수비와의 호흡이 중요합니다.", "🪨"
        elif go_ao < 0.85:
            return "Flyball Pitcher", "뜬공 유도가 많습니다. 넓은 구장을 쓸 때 유리합니다.", "☁️"
        else:
            return "Balanced Pitcher", "특별한 치우침 없이 상황에 맞춰 던지는 밸런스형 투수입니다.", "⚖️"

# ---------------------------------------------------------
# [추가] 에이스 / 필승조 배지 판별 함수
# ---------------------------------------------------------
def get_player_badge(row):
    gs = row['GS']
    g = row['G']
    ip = row['IP_float']
    era = row['ERA']
    sv = row['SV']
    hld = row['HLD']
    
    is_starter = gs > (g / 2) if g > 0 else False
    
    # 에이스 조건: 선발, 100이닝+, ERA 3.50 이하
    if is_starter:
        if ip >= 100 and era <= 3.50:
            return "👑 Team Ace"
    # 필승조 조건: 불펜, (세이브 10+ or 홀드 10+), ERA 4.50 이하
    else:
        if (sv >= 10 or hld >= 10) and era <= 4.50:
            return "🔒 Winning Setup/Closer"
            
    return None

# ---------------------------------------------------------
# 4. 사이드바 및 선수 선택
# ---------------------------------------------------------
st.sidebar.header("🔍 Player Finder")
team_list = sorted(df['팀명'].unique())
selected_team = st.sidebar.selectbox("Select Team", team_list)

player_list = sorted(df[df['팀명'] == selected_team]['선수명'].unique())
selected_player_name = st.sidebar.selectbox("Select Player", player_list)

# 선택된 선수 데이터 추출
player_data = df[(df['팀명'] == selected_team) & (df['선수명'] == selected_player_name)].iloc[0]

player_role = 'Starter' if player_data['GS'] > player_data['G']/2 else 'Reliever'

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Analysis Settings")
compare_group = st.sidebar.radio(
    "Compare Group:",
    (f"Same Role ({player_role}s Only)", "All Pitchers"),
    help="선수의 보직(선발/불펜)에 맞는 선수들과 비교할지, 전체 투수와 비교할지 선택합니다."
)

base_ref = df[df['IP_float'] >= 10]

if "Same Role" in compare_group:
    if player_role == 'Starter':
        ref_df = base_ref[base_ref['GS'] > base_ref['G']/2]
    else:
        ref_df = base_ref[base_ref['GS'] <= base_ref['G']/2]
else:
    ref_df = base_ref

st.sidebar.caption(f"Comparing with **{len(ref_df)}** pitchers.")

# ---------------------------------------------------------
# 5. 백분위 계산
# ---------------------------------------------------------
def calculate_percentile(value, column, lower_is_better=True):
    values = ref_df[column].dropna().values
    if lower_is_better:
        score = (values >= value).mean() * 100
    else:
        score = (values <= value).mean() * 100
    return score

stats_to_plot = {
    'ERA': calculate_percentile(player_data['ERA'], 'ERA', True),
    'WHIP': calculate_percentile(player_data['WHIP'], 'WHIP', True),
    'K/9': calculate_percentile(player_data['K/9'], 'K/9', False),
    'BB/9': calculate_percentile(player_data['BB/9'], 'BB/9', True),
    'OPS': calculate_percentile(player_data['OPS'], 'OPS', True),
    'IP': calculate_percentile(player_data['IP_float'], 'IP_float', False)
}

# ---------------------------------------------------------
# 6. 대시보드 UI
# ---------------------------------------------------------
# [배지 표시 로직]
special_badge = get_player_badge(player_data)
badge_html = ""
if special_badge:
    badge_color = "#FFD700" if "Ace" in special_badge else "#1E90FF"
    text_color = "black" if "Ace" in special_badge else "white"
    badge_html = f'<span style="background-color:{badge_color}; color:{text_color}; padding: 4px 10px; border-radius: 5px; font-size: 0.6em; vertical-align: middle; margin-left: 10px;">{special_badge}</span>'

st.markdown(f"<h1>⚾ {player_data['선수명']} Scouting Report {badge_html}</h1>", unsafe_allow_html=True)
st.markdown(f"**Team:** {player_data['팀명']} | **Role:** {player_role}")

# 순위(Rank) 배지 계산 함수
def get_rank_str(value, col, ascending=True):
    rank = ref_df[col].rank(ascending=ascending, method='min')
    p_rank = rank[ref_df['선수명'] == selected_player_name]
    
    if len(p_rank) > 0:
        p_rank = int(p_rank.values[0])
        total = len(ref_df)
        return f"#{p_rank}/{total}"
    return "-"

# (1) KPI Metrics
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

era_rank_str = get_rank_str(player_data['ERA'], 'ERA', True)
ops_rank_str = get_rank_str(player_data['OPS'], 'OPS', True)
whip_rank_str = get_rank_str(player_data['WHIP'], 'WHIP', True)
so_rank_str = get_rank_str(player_data['SO'], 'SO', False)

kpi1.metric("ERA", f"{player_data['ERA']:.2f}", delta=f"Rank: {era_rank_str}", delta_color="off")
kpi2.metric("OPS", f"{player_data['OPS']:.3f}", delta=f"Rank: {ops_rank_str}", delta_color="off")
kpi3.metric("Record", f"{player_data['W']}W - {player_data['L']}L")
kpi4.metric("WHIP", f"{player_data['WHIP']:.2f}", delta=f"Rank: {whip_rank_str}", delta_color="off")
kpi5.metric("Strikeouts", f"{player_data['SO']}", delta=f"Rank: {so_rank_str}", delta_color="off")

st.markdown("---")

col_left, col_right = st.columns([1, 1])

# (2) 왼쪽: 레이더 차트
with col_left:
    st.subheader("🕸️ Capability Radar")
    categories = list(stats_to_plot.keys())
    values = list(stats_to_plot.values())
    categories.append(categories[0])
    values.append(values[0])

    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=values, theta=categories, fill='toself',
        name=player_data['선수명'], line_color='#E63946', opacity=0.7
    ))
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100], ticksuffix="%")),
        showlegend=False, margin=dict(t=20, b=20)
    )
    st.plotly_chart(fig_radar, use_container_width=True)

# (3) 오른쪽: 스타일 분석
with col_right:
    st.subheader("🔎 Pitching Identity")
    
    style_title, style_desc, style_icon = determine_pitching_style(player_data)
    
    st.markdown(f"""
    <div style="padding: 20px; border-radius: 10px; background-color: rgba(200, 200, 200, 0.2); border-left: 5px solid #FF4B4B;">
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
    c1.metric("K/9 (구위)", f"{player_data['K/9']}", delta="High" if player_data['K/9'] > 9 else "Normal")
    c2.metric("BB/9 (제구)", f"{player_data['BB/9']}", delta="Good" if player_data['BB/9'] < 2.5 else "Normal", delta_color="inverse")
    c3.metric("GO/AO", f"{player_data['GO/AO_float']}", help="1.2 이상이면 땅볼형, 0.8 이하면 뜬공형")

    babip = player_data['BABIP']
    avg_babip = ref_df['BABIP'].mean()
    luck_val = babip - avg_babip
    
    if luck_val < -0.035:
        luck_msg = "운이 따름 (Lucky 🍀)"
    elif luck_val > 0.035:
        luck_msg = "불운함 (Unlucky ☔)"
    else:
        luck_msg = "중립 (Neutral 👌)"
        
    st.markdown(f"**BABIP Analysis:** {luck_msg} (vs Group Avg {avg_babip:.3f})")

# --- 유사한 투수 찾기 (Similarity Search) ---
st.markdown("---")
st.subheader("👯 Similar Pitchers")
st.caption(f"현재 선택된 비교군({compare_group}) 내에서 **ERA, WHIP, K/9, BB/9, GO/AO** 패턴이 가장 유사한 선수들입니다.")

sim_cols = ['ERA', 'WHIP', 'K/9', 'BB/9', 'GO/AO_float']
sim_df = ref_df.dropna(subset=sim_cols).copy()

if not sim_df.empty:
    norm_df = (sim_df[sim_cols] - sim_df[sim_cols].mean()) / sim_df[sim_cols].std()
    
    if selected_player_name in sim_df['선수명'].values:
        target_idx = sim_df[sim_df['선수명'] == selected_player_name].index[0]
        target_vec = norm_df.loc[target_idx].values

        distances = []
        for idx, row in norm_df.iterrows():
            if idx == target_idx: continue
            
            dist = distance.euclidean(target_vec, row.values)
            original_row = sim_df.loc[idx]
            distances.append({
                '선수명': original_row['선수명'],
                '팀명': original_row['팀명'],
                'ERA': original_row['ERA'],
                '유사도': dist
            })
        
        similar_players = sorted(distances, key=lambda x: x['유사도'])[:3]
        
        sc1, sc2, sc3 = st.columns(3)
        for i, col in enumerate([sc1, sc2, sc3]):
            if i < len(similar_players):
                p = similar_players[i]
                with col:
                    st.info(f"**{p['선수명']}** ({p['팀명']})")
                    st.markdown(f"ERA: {p['ERA']:.2f}")
    else:
        st.warning("비교군 내에 현재 선수의 데이터가 부족하여 유사도를 계산할 수 없습니다.")
else:
    st.warning("비교할 대상 데이터가 충분하지 않습니다.")

# ---------------------------------------------------------
# [추가됨] 리그 전체 위치 시각화 (League Context)
# ---------------------------------------------------------
st.markdown("---")
st.subheader("📊 League Context (K/9 vs BB/9)")
st.caption(f"**X축: 9이닝당 볼넷(BB/9)** - 왼쪽일수록 제구 좋음 | **Y축: 9이닝당 삼진(K/9)** - 위쪽일수록 구위 좋음")

# 산점도 그리기
fig_scatter = px.scatter(
    ref_df, 
    x='BB/9', 
    y='K/9', 
    hover_name='선수명', 
    hover_data=['팀명', 'ERA'],
    color='팀명', 
    title=f"Pitching Style Map ({compare_group})"
)

# 현재 선택된 선수 강조 (빨간 점 + 큰 사이즈)
current_p = ref_df[ref_df['선수명'] == selected_player_name]
if not current_p.empty:
    fig_scatter.add_trace(go.Scatter(
        x=current_p['BB/9'], 
        y=current_p['K/9'],
        mode='markers+text',
        marker=dict(color='red', size=15, line=dict(width=2, color='black')),
        name=selected_player_name,
        text=[selected_player_name],
        textposition="top center"
    ))

st.plotly_chart(fig_scatter, use_container_width=True)

# ---------------------------------------------------------
# (4) 하단: 상세 데이터 테이블
# ---------------------------------------------------------
st.markdown("---")
st.markdown("### 📋 Season Stats Detail")

display_cols = ['G', 'GS', 'W', 'L', 'SV', 'HLD', 'IP', 'ERA', 'WHIP', 'SO', 'BB', 'OPS', 'BABIP']
stats_df = pd.DataFrame([player_data[display_cols]])

format_dict = {
    'ERA': '{:.2f}', 
    'WHIP': '{:.2f}', 
    'OPS': '{:.3f}', 
    'BABIP': '{:.3f}'
}

st.dataframe(
    stats_df.style.format(format_dict, na_rep="-"),
    use_container_width=True,
    hide_index=True
)
