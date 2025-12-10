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
    # -----------------------------------------------------------
    # [수정] 파일 경로를 절대 경로로 찾는 필살기 코드
    # -----------------------------------------------------------
    # 1. 현재 이 파일(1_Pitcher_Report.py)의 위치를 알아냅니다. (pages 폴더)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 2. 부모 폴더(한 단계 위)로 올라갑니다. (csv 파일이 있는 곳)
    parent_dir = os.path.dirname(current_dir)
    
    # 3. 경로와 파일명을 합칩니다.
    csv_path = os.path.join(parent_dir, "kbo_hitter_2025_tabs_final")
    
    # 4. 이제 읽어옵니다.
    df = pd.read_csv(csv_path)
    
    # (아래는 기존 전처리 코드 그대로 두시면 됩니다)
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
    
    # 수치형 변환 대상 컬럼
    numeric_cols = ['AVG', 'SLG', 'OBP', 'OPS', 'RISP', 'PH-BA', 'GO/AO', 'BB/K', 'P/PA', 'ISOP']
    
    for col in numeric_cols:
        # 문자열로 변환 후, '-' 등 예외 처리 및 float 변환
        df[col] = pd.to_numeric(df[col].astype(str).replace({'-': '0'}), errors='coerce').fillna(0.0)

    # 기본 수치형 컬럼 결측치 처리
    df['PA'] = df['PA'].fillna(0)
    df['GPA'] = df['GPA'].fillna(0.0)
    
    return df

df = load_data()

# ---------------------------------------------------------
# 3. 타자 스타일 판정 로직 함수
# ---------------------------------------------------------
def determine_hitter_style(row):
    avg = row['AVG']
    isop = row['ISOP'] # 순장타율 (Power)
    bb_k = row['BB/K'] # 선구안
    ops = row['OPS']
    hr = row['HR']
    
    # 1. 거포형 (Power Hitter)
    if isop >= 0.200 or hr >= 20:
        if avg >= 0.280:
            return "Elite Bomber", "정확도와 파괴력을 겸비한 리그 최정상급 강타자입니다.", "💣👑"
        else:
            return "Power Slugger", "한 방으로 경기 흐름을 뒤바꿀 수 있는 전형적인 거포입니다.", "💣"
            
    # 2. 교타자형 (Contact Hitter)
    elif avg >= 0.310:
        if row['SO'] < row['BB']: # 삼진보다 볼넷이 많음
            return "Contact Master", "배트 컨트롤이 예술이며 좀처럼 삼진을 당하지 않습니다.", "🎨🪄"
        else:
            return "Sprinter / Hitter", "높은 타율로 팀의 공격 물꼬를 트는 안타 제조기입니다.", "🏃‍♂️🏏"

    # 3. 선구안형 (On-Base Machine)
    elif bb_k >= 0.8 or row['OBP'] >= 0.380:
        return "Eagle Eye", "뛰어난 선구안으로 투수를 괴롭히며 꾸준히 출루합니다.", "👁️🥎"
        
    # 4. 클러치형 (Clutch)
    elif row['RISP'] >= avg + 0.05 and row['RBI'] > 50:
        return "Clutch Hitter", "찬스에 유독 강하며 해결사 본능을 가지고 있습니다.", "🔥💪"

    # 5. 기타
    else:
        if ops > 0.750:
            return "Solid Regular", "준수한 타격 능력을 갖춘 팀의 주축 선수입니다.", "🛡️"
        else:
            return "Developing Hitter", "성장 가능성을 보여주는 유망주 혹은 백업 자원입니다.", "🌱"

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

# --- 비교군 설정 (주전급 vs 전체) ---
st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Analysis Settings")

# 주전급 기준: 200타석 이상
pa_threshold = 200 
is_regular = player_data['PA'] >= pa_threshold

group_option = st.sidebar.radio(
    "Compare Group:",
    ("Regulars (PA ≥ 200)", "All Hitters"),
    index=0 if is_regular else 1
)

if "Regulars" in group_option:
    ref_df = df[df['PA'] >= pa_threshold]
else:
    ref_df = df[df['PA'] >= 10] # 최소 10타석

st.sidebar.caption(f"Comparing with **{len(ref_df)}** hitters.")

# ---------------------------------------------------------
# 5. 백분위 계산
# ---------------------------------------------------------
def calculate_percentile(value, column, lower_is_better=False):
    values = ref_df[column].dropna().values
    if lower_is_better:
        score = (values >= value).mean() * 100
    else:
        score = (values <= value).mean() * 100
    return score

# 레이더 차트용 지표 (5-Tool)
# Contact(AVG), Power(ISO), Eye(BB/K), Clutch(RISP), Value(GPA)
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
st.title(f"⚾ {player_data['선수명']} Scouting Report")
st.markdown(f"**Team:** {player_data['팀명']} | **PA:** {player_data['PA']} (Avg {player_data['AVG']:.3f})")

# 순위 계산 함수
def get_rank_str(value, col, ascending=False):
    rank = ref_df[col].rank(ascending=ascending, method='min')
    p_rank = rank[ref_df['선수명'] == selected_player_name]
    if len(p_rank) > 0:
        return f"#{int(p_rank.values[0])}/{len(ref_df)}"
    return "-"

# (1) KPI Metrics
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

# 순위 텍스트 생성
avg_rank = get_rank_str(player_data['AVG'], 'AVG')
hr_rank = get_rank_str(player_data['HR'], 'HR')
rbi_rank = get_rank_str(player_data['RBI'], 'RBI')
ops_rank = get_rank_str(player_data['OPS'], 'OPS')
gpa_rank = get_rank_str(player_data['GPA'], 'GPA')

kpi1.metric("AVG", f"{player_data['AVG']:.3f}", f"Rank: {avg_rank}", delta_color="off")
kpi2.metric("HR", f"{player_data['HR']}", f"Rank: {hr_rank}", delta_color="off")
kpi3.metric("RBI", f"{player_data['RBI']}", f"Rank: {rbi_rank}", delta_color="off")
kpi4.metric("OPS", f"{player_data['OPS']:.3f}", f"Rank: {ops_rank}", delta_color="off")
kpi5.metric("GPA", f"{player_data['GPA']:.3f}", f"Rank: {gpa_rank}", delta_color="off", help="Gross Production Average: (1.8*OBP + SLG)/4")

st.markdown("---")

col_left, col_right = st.columns([1, 1])

# (2) 왼쪽: 레이더 차트
with col_left:
    st.subheader("🕸️ 5-Tool Capability")
    categories = list(stats_to_plot.keys())
    values = list(stats_to_plot.values())
    categories.append(categories[0])
    values.append(values[0])

    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=values, theta=categories, fill='toself',
        name=player_data['선수명'], line_color='#29B5E8', opacity=0.7
    ))
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100], ticksuffix="%")),
        showlegend=False, margin=dict(t=20, b=20)
    )
    st.plotly_chart(fig_radar, use_container_width=True)

# (3) 오른쪽: 스타일 분석
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
    
    # 보조 지표
    c1, c2, c3 = st.columns(3)
    # 순장타율 (ISO)
    c1.metric("IsoP (Power)", f"{player_data['ISOP']:.3f}", delta="High" if player_data['ISOP'] > 0.2 else "Normal")
    # 선구안 (BB/K)
    c2.metric("BB/K (Eye)", f"{player_data['BB/K']:.2f}", delta="Good" if player_data['BB/K'] > 0.8 else "Normal")
    # 득점권 (RISP)
    risp_diff = player_data['RISP'] - player_data['AVG']
    c3.metric("RISP (Clutch)", f"{player_data['RISP']:.3f}", delta=f"{risp_diff:+.3f} vs AVG")

# (4) 리그 컨텍스트 (OPS Scatter)
st.markdown("---")
st.subheader("🎯 League Context (OBP vs SLG)")

fig_scatter = px.scatter(
    ref_df, x='OBP', y='SLG', 
    hover_name='선수명', 
    color_discrete_sequence=['#cccccc'],
    opacity=0.6,
    labels={'OBP': 'On-Base Percentage (출루율)', 'SLG': 'Slugging Percentage (장타율)'}
)

# 하이라이트
highlight = ref_df[ref_df['선수명'] == selected_player_name]
fig_scatter.add_trace(go.Scatter(
    x=highlight['OBP'], y=highlight['SLG'],
    mode='markers', marker=dict(color='#29B5E8', size=12, line=dict(width=2, color='black')),
    name=selected_player_name
))

# 평균선
avg_obp = ref_df['OBP'].mean()
avg_slg = ref_df['SLG'].mean()
fig_scatter.add_vline(x=avg_obp, line_dash="dash", line_color="green", annotation_text="Avg OBP")
fig_scatter.add_hline(y=avg_slg, line_dash="dash", line_color="green", annotation_text="Avg SLG")

st.plotly_chart(fig_scatter, use_container_width=True)

# (5) 유사 타자 찾기
st.markdown("### 👯 Similar Hitters")
st.caption("비교군 내에서 **AVG, HR, OPS, BB/K, ISOP** 패턴이 가장 유사한 선수들입니다.")

sim_cols = ['AVG', 'HR', 'OPS', 'BB/K', 'ISOP']
sim_df = ref_df.dropna(subset=sim_cols).copy()

if not sim_df.empty and selected_player_name in sim_df['선수명'].values:
    # 정규화 (Z-Score)
    norm_df = (sim_df[sim_cols] - sim_df[sim_cols].mean()) / sim_df[sim_cols].std()
    
    # 타겟 벡터
    target_idx = sim_df[sim_df['선수명'] == selected_player_name].index[0]
    target_vec = norm_df.loc[target_idx].values
    
    distances = []
    for idx, row in norm_df.iterrows():
        if sim_df.loc[idx]['선수명'] == selected_player_name: continue
        
        dist = distance.euclidean(target_vec, row.values)
        distances.append({
            '선수명': sim_df.loc[idx]['선수명'], 
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
    st.warning("비교할 데이터가 충분하지 않습니다.")

# (6) 상세 데이터
st.markdown("### 📋 Season Stats Detail")
display_cols = ['G', 'PA', 'AB', 'R', 'H', 'HR', 'RBI', 'BB', 'SO', 'AVG', 'OBP', 'SLG', 'OPS', 'RISP', 'GPA']
st.dataframe(
    pd.DataFrame([player_data[display_cols]]).style.format({
        'AVG': '{:.3f}', 'OBP': '{:.3f}', 'SLG': '{:.3f}', 'OPS': '{:.3f}', 'RISP': '{:.3f}', 'GPA': '{:.3f}'
    }),
    use_container_width=True, hide_index=True

)

