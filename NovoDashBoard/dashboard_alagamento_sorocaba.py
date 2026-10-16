"""
Dashboard interativo – Monitoramento de risco de alagamento em Sorocaba
Projeto Integrador – Univesp

Execute com:
    streamlit run dashboard_alagamento_sorocaba.py
"""

from datetime import datetime, timedelta
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

# Diretório do projeto: evita caminhos fixos como /home/workdir/...
BASE_DIR = Path(__file__).resolve().parent

st.set_page_config(
    page_title="Monitoramento de Alagamento – Sorocaba",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)


def classificar_risco(chuva_1h: float, chuva_3h: float, chuva_6h: float,
                     chuva_24h: float, nivel_rio: float) -> tuple[int, str, str]:
    """Classifica o risco de alagamento: 0 baixo, 1 médio, 2 alto."""
    if nivel_rio >= 3.5 or chuva_24h >= 70 or chuva_6h >= 45:
        return 2, "ALTO", "#e74c3c"
    if nivel_rio >= 2.9 or chuva_24h >= 35 or chuva_6h >= 25 or chuva_3h >= 18:
        return 1, "MÉDIO", "#f39c12"
    return 0, "BAIXO", "#27ae60"


def probabilidade_chuva_estimada(chuva_1h: float, chuva_3h: float) -> int:
    """Estimativa simples de chance de chuva nas próximas horas (0–100%)."""
    if chuva_1h >= 5 or chuva_3h >= 12:
        return min(95, 55 + int(chuva_1h * 4) + int(chuva_3h * 1.5))
    if chuva_1h >= 1 or chuva_3h >= 4:
        return min(70, 30 + int(chuva_1h * 8) + int(chuva_3h * 2))
    if chuva_1h > 0 or chuva_3h > 0:
        return min(100, 20 + int(chuva_3h * 3))
    return 10


def localizar_arquivo(nome: str) -> Path | None:
    """Procura dados no projeto e em locais comuns de execução do VS Code."""
    candidatos = [
        BASE_DIR / nome,
        BASE_DIR / "dados" / nome,
        BASE_DIR.parent / "artifacts" / nome,
        Path("/home/workdir/artifacts") / nome,
        Path("/home/workdir/attachments") / nome,
    ]
    return next((p for p in candidatos if p.exists()), None)


def carregar_historico_exemplo() -> pd.DataFrame:
    path = localizar_arquivo("dados_exemplo_alagamento_sorocaba.csv")
    if path is None:
        return pd.DataFrame()
    try:
        df = pd.read_csv(path)
        obrigatorias = {"data_hora", "chuva_1h", "chuva_3h", "chuva_6h", "chuva_24h", "nivel_rio"}
        if not obrigatorias.issubset(df.columns):
            return pd.DataFrame()
        df["data_hora"] = pd.to_datetime(df["data_hora"], errors="coerce")
        return df.dropna(subset=["data_hora"])
    except (OSError, ValueError, pd.errors.ParserError):
        return pd.DataFrame()


def carregar_chuva_sibh() -> pd.DataFrame | None:
    path = localizar_arquivo("sibh_data_eawz4ux.csv")
    if path is None:
        return None
    try:
        df = pd.read_csv(path)
        if not {"Data", "Valor"}.issubset(df.columns):
            return None
        df["Data"] = pd.to_datetime(df["Data"], format="%Y/%m/%d %H:%M", errors="coerce")
        df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0)
        return df.dropna(subset=["Data"])
    except (OSError, ValueError, pd.errors.ParserError):
        return None


st.sidebar.title("⚙️ Controles")
st.sidebar.markdown("Ajuste os valores para simular a situação atual.")
modo = st.sidebar.radio(
    "Modo de dados",
    ["Manual (ao vivo)", "Últimos dados de exemplo", "Chuva SIBH (histórico)"],
    index=0,
)
st.sidebar.divider()
st.sidebar.subheader("📊 Entradas meteorológicas / hidrológicas")

if modo == "Manual (ao vivo)":
    chuva_1h = st.sidebar.slider("Chuva última 1h (mm)", 0.0, 40.0, 2.0, 0.2)
    chuva_3h = st.sidebar.slider("Chuva últimas 3h (mm)", 0.0, 80.0, 6.0, 0.5)
    chuva_6h = st.sidebar.slider("Chuva últimas 6h (mm)", 0.0, 120.0, 12.0, 0.5)
    chuva_24h = st.sidebar.slider("Chuva últimas 24h (mm)", 0.0, 200.0, 28.0, 1.0)
    nivel_rio = st.sidebar.slider("Nível do Rio Sorocaba (m)", 1.0, 6.0, 2.4, 0.05)
elif modo == "Últimos dados de exemplo":
    hist = carregar_historico_exemplo()
    if not hist.empty:
        ultimo = hist.iloc[-1]
        chuva_1h = float(ultimo["chuva_1h"])
        chuva_3h = float(ultimo["chuva_3h"])
        chuva_6h = float(ultimo["chuva_6h"])
        chuva_24h = float(ultimo["chuva_24h"])
        nivel_rio = float(ultimo["nivel_rio"])
        st.sidebar.info(f"Registro: {ultimo['data_hora']}")
    else:
        st.sidebar.warning("Arquivo de histórico não encontrado; usando valores padrão.")
        chuva_1h, chuva_3h, chuva_6h, chuva_24h, nivel_rio = 2.0, 6.0, 12.0, 28.0, 2.4
else:
    sibh = carregar_chuva_sibh()
    if sibh is not None and not sibh.empty:
        agora = sibh["Data"].max()

        def acum(horas: int) -> float:
            inicio = agora - timedelta(hours=horas)
            return float(sibh.loc[sibh["Data"] >= inicio, "Valor"].sum())

        chuva_1h, chuva_3h, chuva_6h, chuva_24h = (acum(h) for h in (1, 3, 6, 24))
        nivel_rio = 2.4
        st.sidebar.warning("Nível do rio não disponível no arquivo SIBH; usando 2,4 m como referência.")
        st.sidebar.caption(f"Último registro SIBH: {agora}")
    else:
        st.sidebar.warning("Arquivo SIBH não encontrado; usando valores padrão.")
        chuva_1h, chuva_3h, chuva_6h, chuva_24h, nivel_rio = 2.0, 6.0, 12.0, 28.0, 2.4

st.sidebar.divider()
st.sidebar.caption("Projeto Integrador – Univesp | Protótipo acadêmico")

risco_cod, risco_label, risco_cor = classificar_risco(
    chuva_1h, chuva_3h, chuva_6h, chuva_24h, nivel_rio
)
chance_chuva = probabilidade_chuva_estimada(chuva_1h, chuva_3h)
agora_str = datetime.now().strftime("%d/%m/%Y %H:%M")

st.title("🌊 Monitoramento de Risco de Alagamento – Sorocaba")
st.markdown(
    f"**Pontos críticos:** Av. Dom Aguirre · Parque das Águas · entorno do Rio Sorocaba  \n"
    f"Atualizado em: `{agora_str}`"
)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Nível do Rio Sorocaba", f"{nivel_rio:.2f} m",
              delta="acima do normal" if nivel_rio > 2.8 else "dentro da faixa",
              delta_color="inverse" if nivel_rio > 2.8 else "off")
with c2:
    st.metric("Chuva (24h)", f"{chuva_24h:.1f} mm", delta=f"{chuva_6h:.1f} mm em 6h")
with c3:
    st.metric("Chance de chuva (próx. horas)", f"{chance_chuva}%")
with c4:
    st.markdown(
        f'<div style="background-color:{risco_cor};color:white;padding:16px 12px;border-radius:10px;'
        f'text-align:center;font-weight:bold;font-size:1.1rem;">RISCO<br>{risco_label}</div>',
        unsafe_allow_html=True,
    )

st.divider()
col_esq, col_dir = st.columns([1.2, 1])
with col_esq:
    st.subheader("🌧️ Intensidade de chuva")
    dados_chuva = pd.DataFrame({
        "Período": ["1 hora", "3 horas", "6 horas", "24 horas"],
        "Acumulado (mm)": [chuva_1h, chuva_3h, chuva_6h, chuva_24h],
    })
    st.bar_chart(dados_chuva.set_index("Período"), height=260)
    st.subheader("📋 Situação atual")
    mensagens = {
        2: (st.error, "**Risco ALTO** – Evite circular nas vias críticas (Av. Dom Aguirre, Parque das Águas, Av. XV de Agosto). Acompanhe orientações da Defesa Civil."),
        1: (st.warning, "**Risco MÉDIO** – Possibilidade de alagamentos pontuais. Fique atento a atualizações e evite trechos baixos próximos ao rio."),
        0: (st.success, "**Risco BAIXO** – Condições dentro da normalidade no momento. Continue acompanhando em caso de chuva intensa."),
    }
    mensagens[risco_cod][0](mensagens[risco_cod][1])

with col_dir:
    st.subheader("📍 Mapa dos pontos críticos")
    mapa = folium.Map(location=[-23.501, -47.458], zoom_start=13, tiles="OpenStreetMap")
    pontos = [
        ("Av. Dom Aguirre (Santa Rosália)", -23.5025, -47.4550, "red"),
        ("Parque das Águas", -23.4960, -47.4520, "red"),
        ("Av. XV de Agosto (Centro)", -23.5018, -47.4585, "orange"),
        ("Retiro São João", -23.4935, -47.4490, "orange"),
        ("Av. Afonso Vergueiro", -23.5050, -47.4620, "orange"),
    ]
    for nome, lat, lon, cor in pontos:
        folium.Marker([lat, lon], popup=nome, tooltip=nome,
                      icon=folium.Icon(color=cor, icon="info-sign")).add_to(mapa)
    folium.Circle(
        location=[-23.499, -47.454],
        radius=1200 if risco_cod == 2 else (800 if risco_cod == 1 else 400),
        color=risco_cor, fill=True, fill_opacity=0.15,
        popup=f"Área de atenção – Risco {risco_label}",
    ).add_to(mapa)
    st_folium(mapa, width=None, height=340, returned_objects=[])

st.divider()
st.subheader("📈 Histórico recente (dados de exemplo do projeto)")
hist = carregar_historico_exemplo()
if not hist.empty:
    hist_plot = hist.tail(40).set_index("data_hora")[["chuva_24h", "nivel_rio"]]
    st.line_chart(hist_plot, height=280)
    with st.expander("Ver tabela dos últimos registros"):
        st.dataframe(hist.tail(15), use_container_width=True)
else:
    st.info("Arquivo de histórico de exemplo não encontrado. Coloque o CSV na pasta do projeto ou em dados/.")

st.markdown("---")
st.caption(
    "Protótipo acadêmico – Projeto Integrador Univesp. Os valores de risco são estimativas "
    "baseadas em regras simplificadas e não substituem os alertas oficiais da Defesa Civil de Sorocaba."
)
