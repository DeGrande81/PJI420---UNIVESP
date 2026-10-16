"""
Dashboard interativo – Monitoramento de risco de alagamento em Sorocaba
Projeto Integrador – Univesp
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import folium
from streamlit_folium import st_folium

# -----------------------------------------------------------------------------
# Configuração da página
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Monitoramento de Alagamento – Sorocaba",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# Funções auxiliares
# -----------------------------------------------------------------------------
def classificar_risco(chuva_1h: float, chuva_3h: float, chuva_6h: float,
                     chuva_24h: float, nivel_rio: float) -> tuple[int, str, str]:
    """
    Classifica risco de alagamento.
    Retorna: (código, rótulo, cor)
    0 = Baixo | 1 = Médio | 2 = Alto
    """
    # Regras calibradas para o contexto de Sorocaba (protótipo)
    if nivel_rio >= 3.5 or chuva_24h >= 70 or chuva_6h >= 45:
        return 2, "ALTO", "#e74c3c"
    if nivel_rio >= 2.9 or chuva_24h >= 35 or chuva_6h >= 25 or chuva_3h >= 18:
        return 1, "MÉDIO", "#f39c12"
    return 0, "BAIXO", "#27ae60"


def probabilidade_chuva_estimada(chuva_1h: float, chuva_3h: float) -> int:
    """Estimativa simples de chance de chuva nas próximas horas (0-100%)."""
    if chuva_1h >= 5 or chuva_3h >= 12:
        return min(95, 55 + int(chuva_1h * 4) + int(chuva_3h * 1.5))
    if chuva_1h >= 1 or chuva_3h >= 4:
        return min(70, 30 + int(chuva_1h * 8) + int(chuva_3h * 2))
    if chuva_1h > 0 or chuva_3h > 0:
        return 20 + int(chuva_3h * 3)
    return 10


def carregar_historico_exemplo() -> pd.DataFrame:
    path = Path("/home/workdir/artifacts/dados_exemplo_alagamento_sorocaba.csv")
    if path.exists():
        df = pd.read_csv(path)
        df["data_hora"] = pd.to_datetime(df["data_hora"])
        return df
    return pd.DataFrame()


def carregar_chuva_sibh() -> pd.DataFrame | None:
    path = Path("/home/workdir/attachments/sibh_data_eawz4ux.csv")
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path)
        df["Data"] = pd.to_datetime(df["Data"], format="%Y/%m/%d %H:%M", errors="coerce")
        df = df.dropna(subset=["Data"])
        df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0)
        return df
    except Exception:
        return None


# -----------------------------------------------------------------------------
# Sidebar – entradas e controles
# -----------------------------------------------------------------------------
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
        chuva_1h, chuva_3h, chuva_6h, chuva_24h, nivel_rio = 2.0, 6.0, 12.0, 28.0, 2.4
else:
    sibh = carregar_chuva_sibh()
    if sibh is not None and not sibh.empty:
        agora = sibh["Data"].max()
        # Acumulados a partir do último registro
        def acum(horas):
            ini = agora - timedelta(hours=horas)
            return float(sibh.loc[sibh["Data"] >= ini, "Valor"].sum())
        chuva_1h = acum(1)
        chuva_3h = acum(3)
        chuva_6h = acum(6)
        chuva_24h = acum(24)
        nivel_rio = 2.4  # não há nível no arquivo SIBH de chuva
        st.sidebar.warning("Nível do rio não disponível neste arquivo SIBH (apenas chuva). Usando 2,4 m como referência.")
        st.sidebar.caption(f"Último registro SIBH: {agora}")
    else:
        chuva_1h, chuva_3h, chuva_6h, chuva_24h, nivel_rio = 2.0, 6.0, 12.0, 28.0, 2.4

st.sidebar.divider()
st.sidebar.caption("Projeto Integrador – Univesp | Protótipo acadêmico")

# -----------------------------------------------------------------------------
# Cálculos
# -----------------------------------------------------------------------------
risco_cod, risco_label, risco_cor = classificar_risco(
    chuva_1h, chuva_3h, chuva_6h, chuva_24h, nivel_rio
)
chance_chuva = probabilidade_chuva_estimada(chuva_1h, chuva_3h)
agora_str = datetime.now().strftime("%d/%m/%Y %H:%M")

# -----------------------------------------------------------------------------
# Cabeçalho
# -----------------------------------------------------------------------------
st.title("🌊 Monitoramento de Risco de Alagamento – Sorocaba")
st.markdown(
    f"**Pontos críticos:** Av. Dom Aguirre · Parque das Águas · entorno do Rio Sorocaba  \n"
    f"Atualizado em: `{agora_str}`"
)

# -----------------------------------------------------------------------------
# Indicadores principais (KPI)
# -----------------------------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric(
        label="Nível do Rio Sorocaba",
        value=f"{nivel_rio:.2f} m",
        delta="acima do normal" if nivel_rio > 2.8 else "dentro da faixa",
        delta_color="inverse" if nivel_rio > 2.8 else "off",
    )

with c2:
    st.metric(
        label="Chuva (24h)",
        value=f"{chuva_24h:.1f} mm",
        delta=f"{chuva_6h:.1f} mm em 6h",
    )

with c3:
    st.metric(
        label="Chance de chuva (próx. horas)",
        value=f"{chance_chuva}%",
    )

with c4:
    st.markdown(
        f"""
        <div style="
            background-color:{risco_cor};
            color:white;
            padding:16px 12px;
            border-radius:10px;
            text-align:center;
            font-weight:bold;
            font-size:1.1rem;
        ">
            RISCO<br>{risco_label}
        </div>
        """,
        unsafe_allow_html=True,
    )

st.divider()

# -----------------------------------------------------------------------------
# Detalhamento de chuva + recomendações
# -----------------------------------------------------------------------------
col_esq, col_dir = st.columns([1.2, 1])

with col_esq:
    st.subheader("🌧️ Intensidade de chuva")
    dados_chuva = pd.DataFrame({
        "Período": ["1 hora", "3 horas", "6 horas", "24 horas"],
        "Acumulado (mm)": [chuva_1h, chuva_3h, chuva_6h, chuva_24h],
    })
    st.bar_chart(dados_chuva.set_index("Período"), height=260)

    st.subheader("📋 Situação atual")
    if risco_cod == 2:
        st.error(
            "**Risco ALTO** – Evite circular nas vias críticas (Av. Dom Aguirre, "
            "Parque das Águas, Av. XV de Agosto). Acompanhe orientações da Defesa Civil."
        )
    elif risco_cod == 1:
        st.warning(
            "**Risco MÉDIO** – Possibilidade de alagamentos pontuais. "
            "Fique atento a atualizações e evite trechos baixos próximos ao rio."
        )
    else:
        st.success(
            "**Risco BAIXO** – Condições dentro da normalidade no momento. "
            "Continue acompanhando em caso de chuva intensa."
        )

with col_dir:
    st.subheader("📍 Mapa dos pontos críticos")
    m = folium.Map(location=[-23.501, -47.458], zoom_start=13, tiles="OpenStreetMap")

    pontos = [
        {"nome": "Av. Dom Aguirre (Santa Rosália)", "lat": -23.5025, "lon": -47.4550, "cor": "red"},
        {"nome": "Parque das Águas", "lat": -23.4960, "lon": -47.4520, "cor": "red"},
        {"nome": "Av. XV de Agosto (Centro)", "lat": -23.5018, "lon": -47.4585, "cor": "orange"},
        {"nome": "Retiro São João", "lat": -23.4935, "lon": -47.4490, "cor": "orange"},
        {"nome": "Av. Afonso Vergueiro", "lat": -23.5050, "lon": -47.4620, "cor": "orange"},
    ]
    for p in pontos:
        folium.Marker(
            [p["lat"], p["lon"]],
            popup=p["nome"],
            tooltip=p["nome"],
            icon=folium.Icon(color=p["cor"], icon="info-sign"),
        ).add_to(m)

    # Destaque visual do nível de risco no mapa
    folium.Circle(
        location=[-23.499, -47.454],
        radius=1200 if risco_cod == 2 else (800 if risco_cod == 1 else 400),
        color=risco_cor,
        fill=True,
        fill_opacity=0.15,
        popup=f"Área de atenção – Risco {risco_label}",
    ).add_to(m)

    st_folium(m, width=None, height=340, returned_objects=[])

st.divider()

# -----------------------------------------------------------------------------
# Histórico recente (dados de exemplo)
# -----------------------------------------------------------------------------
st.subheader("📈 Histórico recente (dados de exemplo do projeto)")
hist = carregar_historico_exemplo()
if not hist.empty:
    hist_plot = hist.tail(40).copy()
    hist_plot = hist_plot.set_index("data_hora")[["chuva_24h", "nivel_rio"]]
    st.line_chart(hist_plot, height=280)

    # Tabela resumida
    with st.expander("Ver tabela dos últimos registros"):
        st.dataframe(
            hist.tail(15).style.format({
                "chuva_1h": "{:.1f}",
                "chuva_3h": "{:.1f}",
                "chuva_6h": "{:.1f}",
                "chuva_24h": "{:.1f}",
                "nivel_rio": "{:.2f}",
            }),
            use_container_width=True,
        )
else:
    st.info("Arquivo de histórico de exemplo não encontrado.")

# -----------------------------------------------------------------------------
# Rodapé
# -----------------------------------------------------------------------------
st.markdown("---")
st.caption(
    "Protótipo acadêmico – Projeto Integrador Univesp. "
    "Os valores de risco são estimativas baseadas em regras simplificadas e não substituem "
    "os alertas oficiais da Defesa Civil de Sorocaba. "
    "Fontes de dados: DAEE/SIBH, registros de eventos e dados de exemplo do projeto."
)
