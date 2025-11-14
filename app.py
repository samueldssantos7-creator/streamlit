import streamlit as st
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# importe as funções do seu etl.py (mesmo diretório)
from etl import (
    load_activities,
    create_distance_over_time, 
    create_activity_type_pie,
    create_pace_trend,
    create_monthly_stats,
)

# === CONFIGURAÇÃO DE CORES E DIRETÓRIOS ===
STRAVA_ORANGE = '#FC4C02'
LINE_COLOR = 'white'

BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "plots"
OUT_DIR.mkdir(parents=True, exist_ok=True)
# ==========================================

# === HELPER FUNCTIONS (Atualizadas com a cor FC4C02 e Layout) ===

def format_pace_minutes(pace_min):
    """Formata pace em minutos para MM:SS"""
    if pd.isna(pace_min) or pace_min == 0:
        return "N/A"
    pace_min = round(pace_min, 1)
    mins = int(pace_min)
    secs = int(round((pace_min - mins) * 60))
    return f"{mins}:{secs:02d}"

def format_minutes_hms(total_min):
    """Formata minutos para HH:MM:SS"""
    if pd.isna(total_min) or total_min == 0:
        return "0:00:00"
    total_min = round(total_min, 1)
    total_seconds = int(total_min * 60)
    hrs = total_seconds // 3600
    mins = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f"{hrs}:{mins:02d}:{secs:02d}"

def categorize_distance(distance_km):
    """Categoriza a corrida por distância"""
    if distance_km < 5:
        return "Treino leve (< 5km)"
    elif distance_km < 10:
        return "Curta (5-10km)"
    elif distance_km < 21:
        return "Médio (10-21km)"
    else:
        return "Meia maratona (> 21km)"

def total_runs_by_km(df_in):
    """Gráfico de dispersão: total corridas por km"""
    if df_in.empty: return None
    
    df_in = df_in.copy()
    df_in["distance_km"] = pd.to_numeric(df_in["distance_km"], errors="coerce").fillna(0)
    df_in["duration_min"] = pd.to_numeric(df_in["duration_min"], errors="coerce").fillna(0)
    
    fig = px.scatter(df_in, x="distance_km", y="duration_min", size="duration_min",
                     color_discrete_sequence=[STRAVA_ORANGE], 
                     hover_name="name",
                     title="Distribuição de corridas por distância (Duração vs. Distância)",
                     labels={"distance_km":"Distância (km)", "duration_min": "Duração (min)"},
                     trendline=None)
    
    fig.update_layout(xaxis_title=None, yaxis_title=None) 
    
    return fig

def pace_by_category(df_in):
    """Gráfico de barras: pace médio por categoria"""
    if df_in.empty: return None
    
    df_in = df_in.copy()
    df_in["distance_km"] = pd.to_numeric(df_in["distance_km"], errors="coerce").fillna(0)
    df_in["duration_min"] = pd.to_numeric(df_in["duration_min"], errors="coerce").fillna(0)
    
    df_in["category"] = df_in["distance_km"].apply(categorize_distance)
    
    df_in["pace_min_km"] = df_in.apply(
        lambda row: row["duration_min"] / row["distance_km"] if row["distance_km"] > 0 else pd.NA,
        axis=1
    )
    df_in["pace_min_km"] = pd.to_numeric(df_in["pace_min_km"], errors="coerce")
    df_in["pace_min_km"] = df_in["pace_min_km"].round(1)
    
    cat_pace = df_in.groupby("category")["pace_min_km"].mean().reset_index()
    cat_pace = cat_pace.sort_values("pace_min_km")
    cat_pace = cat_pace.dropna(subset=["pace_min_km"])
    
    if cat_pace.empty: return None
    
    fig = px.bar(cat_pace, x="category", y="pace_min_km",
                     title="Pace médio por categoria",
                     labels={"category":"Categoria","pace_min_km":"Pace (min/km)"},
                     text=cat_pace["pace_min_km"].apply(lambda x: format_pace_minutes(x)))
    
    fig.update_traces(
        textposition="outside",
        marker_color=STRAVA_ORANGE, 
        marker_cornerradius=5 
    )
    
    fig.update_layout(
        xaxis_title=None, 
        yaxis_title=None, 
        xaxis_tickangle=-45,
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
    )
    
    return fig

# === CONFIGURAÇÃO INICIAL E CSS PERSONALIZADO PARA KPIs ===
st.set_page_config(page_title="Dashboard Strava", layout="wide")
st.title("Dashboard Strava — Interativo")

# CSS para tornar os KPIs interativos, coloridos e centralizados
st.markdown(
    """
    <style>
    div[data-testid="stMetric"] {
        background-color: #FC4C02; 
        border-radius: 10px; 
        padding: 10px; 
        color: white; 
        overflow: hidden; 
    }
    div[data-testid="stMetricValue"] {
        color: white !important;
        text-align: center; 
    }
    div[data-testid="stMetricLabel"] {
        color: white; 
        text-align: center; 
        font-weight: bold; 
    }
    div[data-testid="stMetric"] > div {
        align-items: center;
        justify-content: center;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

@st.cache_data(ttl=3600)
def load_cached_activities(per_page: int, max_pages: int) -> pd.DataFrame:
    """Função para buscar dados do Strava, usa cache do Streamlit."""
    return load_activities(per_page=per_page, max_pages=max_pages)

with st.sidebar:
    st.header("Configuração")
    per_page = st.number_input("Atividades por página", min_value=10, max_value=200, value=50, step=10)
    max_pages = st.number_input("Máx páginas", min_value=1, max_value=50, value=4)
    btn_fetch = st.button("Buscar/Atualizar dados")

if btn_fetch:
    st.info("Buscando dados... aguarde")
    st.cache_data.clear()
    df = load_cached_activities(per_page, max_pages)
else:
    try:
        csv_path = OUT_DIR / "activities.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path, parse_dates=["date"]) 
            st.info(f"Carregado CSV local: {csv_path.name}")
        else:
            df = pd.DataFrame()
            st.warning("Sem dados locais. Pressione 'Buscar/Atualizar dados'.")
    except:
        df = pd.DataFrame()
        st.warning("Sem dados disponíveis. Pressione 'Buscar/Atualizar dados'.")

if df.empty:
    st.error("❌ Não foi possível carregar os dados. Verifique suas credenciais no Streamlit Secrets.")
    st.stop()

# === TRATAMENTO DE TIPOS E FILTROS ===
if "duration_min" in df.columns:
    df["duration_min"] = pd.to_numeric(df["duration_min"], errors="coerce").round(1)
if "distance_km" in df.columns:
    df["distance_km"] = pd.to_numeric(df["distance_km"], errors="coerce").round(1)
if "date" in df.columns:
    df["date"] = pd.to_datetime(df["date"], errors='coerce')

with st.sidebar:
    st.subheader("Filtros de Data")
    
    anos = sorted(df["date"].dt.year.dropna().unique().tolist(), reverse=True)
    ano_selecionado = st.selectbox("Ano", options=["Todos"] + anos, format_func=lambda x: "Todos" if x == "Todos" else str(x), key="ano")
    
    if ano_selecionado == "Todos":
        df_ano = df
    else:
        df_ano = df[df["date"].dt.year == ano_selecionado]

    meses = sorted(df_ano["date"].dt.month.dropna().unique().tolist())
    mes_selecionado = st.selectbox("Mês", options=["Todos"] + meses, format_func=lambda m: "Todos" if m == "Todos" else f"{m:02d}", key="mes")
    
    if mes_selecionado == "Todos":
        df_mes = df_ano
    else:
        df_mes = df_ano[df["date"].dt.month == mes_selecionado]

    dias = sorted(df_mes["date"].dt.day.dropna().unique().tolist())
    dia_selecionado = st.selectbox("Dia", options=["Todos"] + dias, format_func=lambda d: "Todos" if d == "Todos" else f"{d:02d}", key="dia")

mask = pd.Series([True] * len(df), index=df.index)

if ano_selecionado != "Todos":
    mask &= (df["date"].dt.year == ano_selecionado)

if mes_selecionado != "Todos":
    mask &= (df["date"].dt.month == mes_selecionado)

if dia_selecionado != "Todos":
    mask &= (df["date"].dt.day == dia_selecionado)

df_filtered = df[mask].copy()

if ano_selecionado == "Todos" and mes_selecionado == "Todos" and dia_selecionado == "Todos":
    periodo_txt = "Todos os períodos"
elif ano_selecionado == "Todos":
    periodo_txt = "Todos os anos"
elif mes_selecionado == "Todos":
    periodo_txt = f"Todos os meses de {ano_selecionado}"
elif dia_selecionado == "Todos":
    periodo_txt = f"{ano_selecionado}-{mes_selecionado:02d}"
else:
    periodo_txt = f"{ano_selecionado}-{mes_selecionado:02d}-{dia_selecionado:02d}"

st.markdown(f"**Período selecionado:** {periodo_txt} — **Atividades:** {len(df_filtered)}")

# === KPIs (Cálculo e Exibição com CSS) ===
total_runs = len(df_filtered)
total_km = float(df_filtered["distance_km"].sum())
pace_mean = df_filtered["duration_min"].sum() / total_km if total_km > 0 else None
total_time_min = float(df_filtered["duration_min"].sum())

if mes_selecionado != "Todos" and ano_selecionado != "Todos":
    if mes_selecionado == 1:
        prev_mes, prev_ano = 12, ano_selecionado - 1
    else:
        prev_mes, prev_ano = mes_selecionado - 1, ano_selecionado
    
    pm_mask = (df["date"].dt.month == prev_mes) & (df["date"].dt.year == prev_ano)
    pm_df = df.loc[pm_mask]
    pm_dist = pm_df["distance_km"].sum()
    pace_prev = pm_df["duration_min"].sum() / pm_dist if pm_dist > 0 else None
    prev_month_display = f"{prev_ano}-{prev_mes:02d}"
else:
    pace_prev = None
    prev_month_display = "N/A"

k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.metric("Total corridas", f"{total_runs}")
with k2:
    st.metric("Km total", f"{total_km:.1f} km")
with k3:
    st.metric("Pace médio", format_pace_minutes(pace_mean) if pace_mean else "N/A")
with k4:
    st.metric(f"Pace mês ant. ({prev_month_display})", format_pace_minutes(pace_prev) if pace_prev else "N/A")
with k5:
    st.metric("Tempo total", format_minutes_hms(total_time_min))

# === GRÁFICOS ===
col1, col2 = st.columns(2)
with col1:
    st.subheader("Distância acumulada")
    fig1 = create_distance_over_time(df_filtered)
    
    fig1.update_traces(
        line=dict(color=LINE_COLOR, width=2),
        mode='lines+markers', 
        marker=dict(color=STRAVA_ORANGE, size=8, line=dict(width=1, color=LINE_COLOR)) 
    )
    fig1.update_layout(xaxis_title=None, yaxis_title=None) 
    
    st.plotly_chart(fig1, width='stretch') 

    st.subheader("Tendência de pace")
    fig3 = create_pace_trend(df_filtered)
    
    fig3.update_traces(
        line=dict(color=LINE_COLOR, width=2),
        mode='lines+markers',
        marker=dict(color=STRAVA_ORANGE, size=8, line=dict(width=1, color=LINE_COLOR))
    )
    fig3.update_layout(xaxis_title=None, yaxis_title=None)
    
    st.plotly_chart(fig3, width='stretch')

with col2:
    st.subheader("Tipos de atividade")
    fig2 = create_activity_type_pie(df_filtered)
    
    fig2.update_traces(
        marker=dict(colors=[STRAVA_ORANGE, '#FF7F50', '#FFD700', '#A0522D']),
        marker_line_color='white'
    )
    
    st.plotly_chart(fig2, width='stretch')

    st.subheader("Total corridas por km")
    fig_km = total_runs_by_km(df_filtered)
    if fig_km:
        st.plotly_chart(fig_km, width='stretch')

st.subheader("Estatísticas mensais")
fig_monthly = create_monthly_stats(df_filtered)

fig_monthly.update_traces(
    marker_line_width=0, 
    marker_line_color='rgba(0,0,0,0)', 
    marker_cornerradius=5,
    marker_color=STRAVA_ORANGE 
)
fig_monthly.update_layout(
    xaxis_title=None, 
    yaxis_title=None,
    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
) 

st.plotly_chart(fig_monthly, width='stretch')

st.subheader("Pace médio por categoria")
fig_cat = pace_by_category(df_filtered)
if fig_cat:
    st.plotly_chart(fig_cat, width='stretch')

csv_bytes = df_filtered.to_csv(index=False).encode("utf-8")
st.download_button("Baixar CSV", data=csv_bytes, file_name="activities.csv", mime="text/csv")

st.write("Período total:", df["date"].min().strftime('%Y-%m-%d'), "→", df["date"].max().strftime('%Y-%m-%d'))