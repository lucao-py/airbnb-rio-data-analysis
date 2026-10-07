"""Dashboard das análises finais de analise.ipynb (Inside Airbnb, Rio de Janeiro)."""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


COL_BAIRRO = "neighbourhood_cleansed"
FAIXAS_ESTADIA = ["1 noite", "2–3 noites", "4–6 noites", "7–29 noites", "30+ noites"]
CORES_ESTADIA = {
    "1 noite": "#2563eb",
    "2–3 noites": "#14b8a6",
    "4–6 noites": "#f59e0b",
    "7–29 noites": "#f97316",
    "30+ noites": "#7c3aed",
}
CORES_CAPACIDADE = {
    "2 hóspedes": "#2563eb",
    "4 hóspedes": "#14b8a6",
    "6 hóspedes": "#f59e0b",
}


def formatar_reais(valor: float) -> str:
    """Mostra números no padrão brasileiro, inclusive nos tooltips."""
    return "R$ " + f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


@st.cache_data(show_spinner="Carregando anúncios...")
def load_data() -> pd.DataFrame:
    caminho = Path(__file__).resolve().parent / "listings.csv.gz"
    return pd.read_csv(
        caminho,
        usecols=[COL_BAIRRO, "price", "accommodates", "minimum_nights"],
        low_memory=False,
    )


def prepare_data(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    dados = df.copy()
    dados["price_num"] = pd.to_numeric(
        dados["price"]
        .astype("string")
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip(),
        errors="coerce",
    )
    dados["accommodates"] = pd.to_numeric(dados["accommodates"], errors="coerce")
    dados["minimum_nights"] = pd.to_numeric(dados["minimum_nights"], errors="coerce")
    top_bairros = dados[COL_BAIRRO].value_counts().head(10).index.tolist()
    return dados, top_bairros


def grafico_preco_bairro(df: pd.DataFrame, bairros: list[str], capacidade: int | None):
    dados = df[df[COL_BAIRRO].isin(bairros) & df["price_num"].notna()]
    if capacidade is not None:
        dados = dados[dados["accommodates"] == capacidade]
    preco_bairro = (
        dados.groupby(COL_BAIRRO, as_index=False)
        .agg(preco_mediano=("price_num", "median"), anuncios=("price_num", "size"))
        .sort_values("preco_mediano", ascending=True)
    )
    if preco_bairro.empty:
        return None
    preco_bairro["preco_formatado"] = preco_bairro["preco_mediano"].map(formatar_reais)
    fig = px.bar(
        preco_bairro,
        x="preco_mediano",
        y=COL_BAIRRO,
        orientation="h",
        text="preco_formatado",
        custom_data=["preco_formatado", "anuncios"],
        labels={"preco_mediano": "Preço mediano por noite (R$)", COL_BAIRRO: "Bairro"},
        title="Preço mediano das hospedagens nos 10 bairros com mais anúncios",
    )
    fig.update_traces(
        marker_color="#2563eb",
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Preço mediano: %{customdata[0]}<br>Anúncios: %{customdata[1]}<extra></extra>",
    )
    fig.update_layout(
        template="plotly_white",
        showlegend=False,
        xaxis_title="Preço mediano por noite (R$)",
        yaxis_title="",
        margin=dict(l=15, r=95, t=80, b=40),
        height=540,
    )
    fig.update_yaxes(categoryorder="array", categoryarray=preco_bairro[COL_BAIRRO].tolist())
    return fig


def grafico_preco_capacidade(df: pd.DataFrame, bairros: list[str]):
    capacidades = [2, 4, 6]
    dados = df[
        df[COL_BAIRRO].isin(bairros)
        & df["accommodates"].isin(capacidades)
        & df["price_num"].notna()
    ]
    preco_capacidade = (
        dados.groupby([COL_BAIRRO, "accommodates"], as_index=False)
        .agg(preco_mediano=("price_num", "median"), anuncios=("price_num", "size"))
    )
    if preco_capacidade.empty:
        return None
    # Mantém a ordenação final do notebook: preço das acomodações para 4 hóspedes.
    ordem_bairros = (
        preco_capacidade[preco_capacidade["accommodates"] == 4]
        .sort_values("preco_mediano", ascending=False)[COL_BAIRRO]
        .tolist()
    )
    ordem_bairros += [bairro for bairro in bairros if bairro not in ordem_bairros]
    preco_capacidade["Capacidade"] = preco_capacidade["accommodates"].astype(int).astype(str) + " hóspedes"
    preco_capacidade["preco_formatado"] = preco_capacidade["preco_mediano"].map(formatar_reais)
    fig = px.bar(
        preco_capacidade,
        x=COL_BAIRRO,
        y="preco_mediano",
        color="Capacidade",
        barmode="group",
        category_orders={COL_BAIRRO: ordem_bairros, "Capacidade": ["2 hóspedes", "4 hóspedes", "6 hóspedes"]},
        color_discrete_map=CORES_CAPACIDADE,
        custom_data=["preco_formatado", "anuncios"],
        labels={COL_BAIRRO: "Bairro", "preco_mediano": "Preço mediano por noite (R$)"},
        title="Preço mediano por bairro para acomodações de capacidade semelhante",
    )
    fig.update_traces(
        hovertemplate="<b>%{x}</b><br>%{fullData.name}<br>Preço mediano: %{customdata[0]}<br>Anúncios: %{customdata[1]}<extra></extra>"
    )
    fig.update_layout(
        template="plotly_white",
        xaxis_title="Bairro",
        yaxis_title="Preço mediano por noite (R$)",
        legend_title="Capacidade",
        xaxis_tickangle=-35,
        margin=dict(l=20, r=20, t=80, b=110),
        height=540,
    )
    return fig


def preparar_estadia(df: pd.DataFrame, bairros: list[str]) -> pd.DataFrame:
    dados = df[df[COL_BAIRRO].isin(bairros) & df["minimum_nights"].notna()].copy()
    dados["perfil_estadia"] = pd.cut(
        dados["minimum_nights"],
        bins=[0, 1, 3, 6, 29, float("inf")],
        labels=FAIXAS_ESTADIA,
    )
    return dados.dropna(subset=["perfil_estadia"])


def grafico_perfil_estadia(df_min: pd.DataFrame, bairros: list[str]):
    perfil_bairro = (
        df_min.groupby([COL_BAIRRO, "perfil_estadia"], observed=True)
        .size()
        .reset_index(name="quantidade")
    )
    if perfil_bairro.empty:
        return None
    perfil_bairro["percentual"] = (
        perfil_bairro.groupby(COL_BAIRRO)["quantidade"].transform(lambda x: x / x.sum() * 100)
    )
    perfil_bairro["percentual_formatado"] = perfil_bairro["percentual"].map(lambda x: f"{x:.1f}%")
    fig = px.bar(
        perfil_bairro,
        y=COL_BAIRRO,
        x="percentual",
        color="perfil_estadia",
        orientation="h",
        barmode="stack",
        category_orders={"perfil_estadia": FAIXAS_ESTADIA},
        color_discrete_map=CORES_ESTADIA,
        custom_data=["percentual_formatado", "quantidade"],
        labels={COL_BAIRRO: "Bairro", "percentual": "Participação dos anúncios (%)", "perfil_estadia": "Estadia mínima"},
        title="Perfil de estadia mínima nos 10 bairros com mais anúncios",
    )
    fig.update_traces(
        hovertemplate="<b>%{y}</b><br>%{fullData.name}: %{customdata[0]}<br>Anúncios: %{customdata[1]}<extra></extra>"
    )
    fig.update_layout(
        template="plotly_white",
        xaxis_title="Participação dos anúncios (%)",
        yaxis_title="",
        legend_title="Estadia mínima",
        xaxis=dict(range=[0, 100], ticksuffix="%"),
        margin=dict(l=15, r=20, t=80, b=40),
        height=540,
    )
    fig.update_yaxes(categoryorder="array", categoryarray=list(reversed(bairros)))
    return fig


def grafico_estadia_7_mais(df_min: pd.DataFrame):
    dados = df_min.copy()
    dados["estadia_7_mais"] = dados["minimum_nights"] >= 7
    longa_bairro = (
        dados.groupby(COL_BAIRRO, as_index=False)
        .agg(percentual_7_mais=("estadia_7_mais", "mean"), anuncios=("minimum_nights", "size"))
    )
    if longa_bairro.empty:
        return None
    longa_bairro["percentual_7_mais"] *= 100
    longa_bairro = longa_bairro.sort_values("percentual_7_mais", ascending=True)
    longa_bairro["percentual_formatado"] = longa_bairro["percentual_7_mais"].map(lambda x: f"{x:.1f}%")
    fig = px.scatter(
        longa_bairro,
        x="percentual_7_mais",
        y=COL_BAIRRO,
        text="percentual_formatado",
        custom_data=["anuncios"],
        labels={"percentual_7_mais": "Anúncios com estadia mínima de 7+ noites (%)", COL_BAIRRO: "Bairro"},
        title="Participação de anúncios com estadia mínima de 7 noites ou mais",
    )
    fig.update_traces(
        marker=dict(size=13, color="#2563eb"),
        textposition="middle right",
        hovertemplate="<b>%{y}</b><br>Participação: %{text}<br>Anúncios: %{customdata[0]}<extra></extra>",
    )
    fig.update_layout(
        template="plotly_white",
        xaxis_title="Participação dos anúncios (%)",
        yaxis_title="",
        showlegend=False,
        xaxis=dict(range=[0, max(10, float(longa_bairro["percentual_7_mais"].max()) * 1.22)], ticksuffix="%"),
        margin=dict(l=15, r=65, t=80, b=40),
        height=540,
    )
    fig.update_yaxes(categoryorder="array", categoryarray=longa_bairro[COL_BAIRRO].tolist())
    return fig


def mostrar_grafico(fig):
    if fig is None:
        st.info("Não há anúncios suficientes para este gráfico com os filtros selecionados.")
    else:
        st.plotly_chart(fig, width="stretch")


def main() -> None:
    st.set_page_config(page_title="Airbnb no Rio de Janeiro", layout="wide")
    st.title("Airbnb no Rio de Janeiro — Análise da Oferta de Hospedagem")
    st.caption("Dashboard baseado nos anúncios ativos do Airbnb no Rio de Janeiro, coletados em 24 de junho de 2026.")

    try:
        dados, top_bairros = prepare_data(load_data())
    except (FileNotFoundError, ValueError, KeyError, OSError) as exc:
        st.error(f"Não foi possível carregar listings.csv.gz: {exc}")
        st.stop()

    st.sidebar.header("Filtros")
    bairros = st.sidebar.multiselect(
        "Bairros (entre os 10 com mais anúncios)",
        options=top_bairros,
        default=top_bairros,
    )
    capacidade_rotulo = st.sidebar.selectbox(
        "Capacidade no gráfico 1",
        options=["Todas", "2 hóspedes", "4 hóspedes", "6 hóspedes"],
    )
    capacidade = {"Todas": None, "2 hóspedes": 2, "4 hóspedes": 4, "6 hóspedes": 6}[capacidade_rotulo]
    st.sidebar.caption("O gráfico 2 mantém a comparação entre 2, 4 e 6 hóspedes. Os gráficos de estadia mínima incluem todas as capacidades.")

    if not bairros:
        st.info("Selecione ao menos um bairro na barra lateral para visualizar as análises.")
        return

    st.header("1. Preços e localização")
    st.markdown("**Como os preços das hospedagens variam entre os principais bairros do Rio de Janeiro e essas diferenças permanecem quando comparamos acomodações com capacidade semelhante?**")
    coluna_1, coluna_2 = st.columns(2, gap="large")
    with coluna_1:
        st.caption("Mediana do preço anunciado por bairro. Anúncios sem preço são excluídos; a capacidade escolhida na barra lateral vale para este gráfico.")
        mostrar_grafico(grafico_preco_bairro(dados, bairros, capacidade))
    with coluna_2:
        st.caption("Comparação dos preços medianos para acomodações de 2, 4 e 6 hóspedes nos mesmos bairros selecionados.")
        mostrar_grafico(grafico_preco_capacidade(dados, bairros))

    st.header("2. Estadia mínima")
    st.markdown("**Os principais bairros do Rio de Janeiro apresentam perfis diferentes de exigência de estadia mínima?**")
    dados_estadia = preparar_estadia(dados, bairros)
    coluna_3, coluna_4 = st.columns(2, gap="large")
    with coluna_3:
        st.caption("Cada barra soma 100% dos anúncios com estadia mínima informada no bairro. Valores extremos permanecem na faixa de 30+ noites.")
        mostrar_grafico(grafico_perfil_estadia(dados_estadia, bairros))
    with coluna_4:
        st.caption("Percentual de anúncios que exigem pelo menos 7 noites; essa exigência não indica, por si só, aluguel de longa duração.")
        mostrar_grafico(grafico_estadia_7_mais(dados_estadia))


if __name__ == "__main__":
    main()
