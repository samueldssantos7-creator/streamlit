import streamlit as st
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# === CONFIGURAÇÃO SEGURA PARA STREAMLIT CLOUD ===
if 'STREAMLIT_CLOUD' in os.environ:
    BASE_DIR = Path('/mount/src/strava-dashboard')
else:
    BASE_DIR = Path(__file__).resolve().parent

# Usar BASE_DIR diretamente (mais seguro)
OUT_DIR = BASE_DIR

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
# ==========================================

# === HELPER FUNCTIONS ===

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
    if df_in.empty: 
        return go.Figure().update_layout(
            title="Distribuição de corridas por distância",
            annotations=[dict(text="Nenhum dado disponível", x=0.5, y=0.5, showarrow=False)]
        )
    
    df_in = df_in.copy()
    
    # Verificar e converter colunas
    if "distance_km" in df_in.columns:
        df_in["distance_km"] = pd.to_numeric(df_in["distance_km"], errors="coerce").fillna(0)
    
    # Tentar diferentes nomes de coluna para duração
    duration_col = None
    for col in ["duration_min", "moving_time", "elapsed_time"]:
        if col in df_in.columns:
            duration_col = col
            break
    
    if not duration_col:
        return go.Figure().update_layout(
            title="Distribuição de corridas por distância",
            annotations=[dict(text="Coluna de duração não encontrada", x=0.5, y=0.5, showarrow=False)]
        )
    
    df_in["duration_min"] = pd.to_numeric(df_in[duration_col], errors="coerce").fillna(0)
    
    fig = px.scatter(df_in, x="distance_km", y="duration_min", size="duration_min",
                     color_discrete_sequence=[STRAVA_ORANGE], 
                     hover_name="name" if "name" in df_in.columns else None,
                     title="Distribuição de corridas por distância (Duração vs. Distância)",
                     labels={"distance_km":"Distância (km)", "duration_min": "Duração (min)"},
                     trendline=None)
    
    fig.update_layout(xaxis_title=None, yaxis_title=None) 
    
    return fig

def pace_by_category(df_in):
    """Gráfico de barras: pace médio por categoria"""
    if df_in.empty: 
        return go.Figure().update_layout(
            title="Pace médio por categoria",
            annotations=[dict(text="Nenhum dado disponível", x=0.5, y=0.5, showarrow=False)]
        )
    
    df_in = df_in.copy()
    
    # Verificar e converter colunas
    if "distance_km" in df_in.columns:
        df_in["distance_km"] = pd.to_numeric(df_in["distance_km"], errors="coerce").fillna(0)
    
    # Tentar diferentes nomes de coluna para duração
    duration_col = None
    for col in ["duration_min", "moving_time", "elapsed_time"]:
        if col in df_in.columns:
            duration_col = col
            break
    
    if not duration_col or "distance_km" not in df_in.columns:
        return go.Figure().update_layout(
            title="Pace médio por categoria",
            annotations=[dict(text="Colunas necessárias não encontradas", x=0.5, y=0.5, showarrow=False)]
        )
    
    df_in["duration_min"] = pd.to_numeric(df_in[duration_col], errors="coerce").fillna(0)
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
    
    if cat_pace.empty: 
        return go.Figure().update_layout(
            title="Pace médio por categoria",
            annotations=[dict(text="Dados insuficientes", x=0.5, y=0.5, showarrow=False)]
        )
    
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

# === CONFIGURAÇÃO INICIAL ===
st.set_page_config(page_title="Dashboard Strava", layout="wide")
st.title("Dashboard Strava — Interativo")

# CSS para KPIs
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

# === CARREGAMENTO DE DADOS ===
if btn_fetch:
    st.info("Buscando dados... aguarde")
    st.cache_data.clear()
    df = load_cached_activities(per_page, max_pages)
else:
    try:
        csv_path = OUT_DIR / "activities.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path) 
            st.info(f"Carregado CSV local: {csv_path.name}")
        else:
            df = pd.DataFrame()
            st.warning("Sem dados locais. Pressione 'Buscar/Atualizar dados'.")
    except Exception as e:
        st.error(f"Erro ao carregar CSV: {e}")
        df = pd.DataFrame()

if df.empty:
    st.error("❌ Não foi possível carregar os dados. Verifique suas credenciais no Streamlit Secrets.")
    st.stop()

# === DEBUG: MOSTRAR COLUNAS DISPONÍVEIS ===
st.sidebar.subheader("Debug Info")
st.sidebar.write(f"Colunas disponíveis: {df.columns.tolist()}")
st.sidebar.write(f"Total de linhas: {len(df)}")

# === TRATAMENTO DE COLUNAS ===
# Verificar coluna de data
date_col = None
for col in ["date", "start_date", "start_date_local"]:
    if col in df.columns:
        date_col = col
        break

if not date_col:
    st.error("❌ Nenhuma coluna de data encontrada")
    st.stop()

df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
df = df.rename(columns={date_col: "date"})

# Verificar coluna de distância
if "distance_km" not in df.columns:
    for col in ["distance", "distance_km"]:
        if col in df.columns:
            df["distance_km"] = pd.to_numeric(df[col], errors="coerce")
            if col == "distance":  # Se for em metros, converter para km
                df["distance_km"] = df["distance_km"] / 1000
            break

# Verificar coluna de duração
if "duration_min" not in df.columns:
    for col in ["moving_time", "elapsed_time", "duration"]:
        if col in df.columns:
            # Converter segundos para minutos
            df["duration_min"] = pd.to_numeric(df[col], errors="coerce") / 60
            break

# Verificar coluna de tipo
if "type" not in df.columns:
    for col in ["sport_type", "type", "activity_type"]:
        if col in df.columns:
            df["type"] = df[col]
            break

# Remover linhas com dados essenciais faltando
df = df.dropna(subset=['date'])
if "distance_km" in df.columns:
    df = df[df["distance_km"] > 0]
if "duration_min" in df.columns:
    df = df[df["duration_min"] > 0]

if df.empty:
    st.error("❌ Nenhum dado válido após o processamento")
    st.stop()

# === FILTROS ===
with st.sidebar:
    st.subheader("Filtros de Data")
    
    anos = sorted(df["date"].dt.year.dropna().unique().tolist(), reverse=True)
    if not anos:
        st.error("Nenhum ano válido encontrado")
        st.stop()
        
    ano_selecionado = st.selectbox("Ano", options=["Todos"] + anos, key="ano")
    
    if ano_selecionado == "Todos":
        df_ano = df
    else:
        df_ano = df[df["date"].dt.year == ano_selecionado]

    meses = sorted(df_ano["date"].dt.month.dropna().unique().tolist())
    mes_selecionado = st.selectbox("Mês", options=["Todos"] + meses, key="mes")
    
    if mes_selecionado == "Todos":
        df_mes = df_ano
    else:
        df_mes = df_ano[df_ano["date"].dt.month == mes_selecionado]

    dias = sorted(df_mes["date"].dt.day.dropna().unique().tolist())
    dia_selecionado = st.selectbox("Dia", options=["Todos"] + dias, key="dia")

# Aplicar filtros
mask = pd.Series([True] * len(df), index=df.index)

if ano_selecionado != "Todos":
    mask &= (df["date"].dt.year == ano_selecionado)

if mes_selecionado != "Todos":
    mask &= (df["date"].dt.month == mes_selecionado)

if dia_selecionado != "Todos":
    mask &= (df["date"].dt.day == dia_selecionado)

df_filtered = df[mask].copy()

if df_filtered.empty:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")
    st.stop()

# === KPIs ===
total_runs = len(df_filtered)
total_km = df_filtered["distance_km"].sum() if "distance_km" in df_filtered.columns else 0
total_time_min = df_filtered["duration_min"].sum() if "duration_min" in df_filtered.columns else 0
pace_mean = total_time_min / total_km if total_km > 0 else None

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("Total atividades", f"{total_runs}")
with k2:
    st.metric("Km total", f"{total_km:.1f} km")
with k3:
    st.metric("Pace médio", format_pace_minutes(pace_mean) if pace_mean else "N/A")
with k4:
    st.metric("Tempo total", format_minutes_hms(total_time_min))

# === GRÁFICOS ===
col1, col2 = st.columns(2)

with col1:
    st.subheader("Distância acumulada")
    fig1 = create_distance_over_time(df_filtered)
    if fig1:
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("Nenhum dado para exibir o gráfico de distância acumulada")

    st.subheader("Tendência de pace")
    fig3 = create_pace_trend(df_filtered)
    if fig3:
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("Nenhum dado para exibir o gráfico de tendência de pace")

with col2:
    st.subheader("Tipos de atividade")
    fig2 = create_activity_type_pie(df_filtered)
    if fig2:
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Nenhum dado para exibir o gráfico de tipos de atividade")

    st.subheader("Distribuição por distância")
    fig_km = total_runs_by_km(df_filtered)
    if fig_km:
        st.plotly_chart(fig_km, use_container_width=True)
    else:
        st.info("Nenhum dado para exibir o gráfico de distribuição")

st.subheader("Estatísticas mensais")
fig_monthly = create_monthly_stats(df_filtered)
if fig_monthly:
    st.plotly_chart(fig_monthly, use_container_width=True)
else:
    st.info("Nenhum dado para exibir estatísticas mensais")

st.subheader("Pace médio por categoria")
fig_cat = pace_by_category(df_filtered)
if fig_cat:
    st.plotly_chart(fig_cat, use_container_width=True)
else:
    st.info("Nenhum dado para exibir pace por categoria")

# Download
if not df_filtered.empty:
    csv_bytes = df_filtered.to_csv(index=False).encode("utf-8")
    st.download_button("Baixar CSV", data=csv_bytes, file_name="activities.csv", mime="text/csv")

if not df.empty:
    st.write("Período total:", df["date"].min().strftime('%Y-%m-%d'), "→", df["date"].max().strftime('%Y-%m-%d'))
