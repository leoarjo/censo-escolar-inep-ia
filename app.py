# -*- coding: utf-8 -*-
"""
Dashboard - Censo Escolar (INEP) | IESB
=======================================

Fonte de dados: PostgreSQL (bigdata.dataiesb.com / db: iesb)

Modelo de dados (validado contra o banco):
    inep_censo_escolar  c   -> 1 linha por escola (co_entidade), ano 2025
      LEFT JOIN inep_censo_escolar_matricula m  ON c.co_entidade = m.co_entidade   (variáveis QT_MAT_*)
      JOIN      municipio                   mu  ON c.co_municipio = mu.codigo_municipio_dv  (nome + lat/long)
      JOIN      unidade_federacao           uf  ON mu.cd_uf       = uf.cd_uf        (sigla/nome UF)
      JOIN      regiao                       r  ON uf.cd_regiao   = r.cd_regiao     (nome região)

Variáveis solicitadas:
    nome_municipio, nome_uf, nome_regiao,
    tp_categoria_escola_privada, tp_localizacao, tp_localizacao_diferenciada,
    qt_mat_inf, qt_mat_fund, qt_mat_fund_af, qt_mat_med   (origem: tabela de matrícula)

Como executar:
    pip install -r requirements.txt
    streamlit run app.py
"""

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine, text

# ---------------------------------------------------------------------------
# Configuração da página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Censo Escolar | IESB",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Conexão com o banco (cacheada como recurso, reaproveitada entre execuções)
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def get_engine():
    cfg = st.secrets["postgres"]
    url = (
        f"postgresql+psycopg2://{cfg['user']}:{cfg['password']}"
        f"@{cfg['host']}:{cfg.get('port', 5432)}/{cfg['dbname']}"
    )
    # client_encoding=utf8 garante acentuação correta dos nomes/categorias
    return create_engine(url, connect_args={"client_encoding": "utf8"}, pool_pre_ping=True)


@st.cache_data(ttl=3600, show_spinner="Consultando o banco...")
def run_query(sql: str, params: dict | None = None) -> pd.DataFrame:
    """Executa SQL e devolve DataFrame. Resultado cacheado por 1h."""
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})


# CTE base com todas as junções e variáveis pedidas. Reutilizada em todas as
# consultas (apenas trocando o SELECT/GROUP BY e os filtros do WHERE).
BASE_JOIN = """
    FROM inep_censo_escolar c
    LEFT JOIN inep_censo_escolar_matricula m ON c.co_entidade   = m.co_entidade
    JOIN municipio                        mu ON c.co_municipio  = mu.codigo_municipio_dv
    JOIN unidade_federacao                uf ON mu.cd_uf         = uf.cd_uf
    JOIN regiao                            r ON uf.cd_regiao     = r.cd_regiao
"""

# Colunas de matrícula que o dashboard agrega
MAT_COLS = {
    "qt_mat_inf": "Educação Infantil",
    "qt_mat_fund": "Ensino Fundamental",
    "qt_mat_fund_af": "Fundamental - Anos Finais",
    "qt_mat_med": "Ensino Médio",
}


# ---------------------------------------------------------------------------
# Funções auxiliares para os filtros (carregam domínios distintos)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def opcoes_regiao() -> list[str]:
    df = run_query("SELECT DISTINCT r.nome_regiao " + BASE_JOIN + " ORDER BY 1")
    return df["nome_regiao"].dropna().tolist()


@st.cache_data(ttl=3600)
def opcoes_uf(regioes: tuple) -> pd.DataFrame:
    sql = "SELECT DISTINCT uf.sigla_uf, uf.nome_uf " + BASE_JOIN
    params = {}
    if regioes:
        sql += " WHERE r.nome_regiao = ANY(:regioes)"
        params["regioes"] = list(regioes)
    sql += " ORDER BY 1"
    return run_query(sql, params)


def _filtro_where(regioes, ufs, localizacoes, categorias) -> tuple[str, dict]:
    """Monta a cláusula WHERE dinâmica a partir dos filtros do sidebar."""
    clauses, params = [], {}
    if regioes:
        clauses.append("r.nome_regiao = ANY(:regioes)")
        params["regioes"] = list(regioes)
    if ufs:
        clauses.append("uf.sigla_uf = ANY(:ufs)")
        params["ufs"] = list(ufs)
    if localizacoes:
        clauses.append("c.tp_localizacao = ANY(:locs)")
        params["locs"] = list(localizacoes)
    if categorias:
        clauses.append("c.tp_categoria_escola_privada = ANY(:cats)")
        params["cats"] = list(categorias)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params


# ---------------------------------------------------------------------------
# SIDEBAR - Filtros
# ---------------------------------------------------------------------------
st.sidebar.title("🎓 Censo Escolar")
st.sidebar.caption("Filtros")

sel_regioes = st.sidebar.multiselect("Região", opcoes_regiao())

df_uf = opcoes_uf(tuple(sel_regioes))
sel_ufs = st.sidebar.multiselect("UF", df_uf["sigla_uf"].tolist())

sel_loc = st.sidebar.multiselect("Localização", ["Urbana", "Rural"])

sel_cat = st.sidebar.multiselect(
    "Categoria (rede privada)",
    ["Particular", "Comunitária", "Confessional", "Filantrópica", "Não aplicável"],
    help="'Não aplicável' corresponde às escolas da rede pública.",
)

where_sql, where_params = _filtro_where(sel_regioes, sel_ufs, sel_loc, sel_cat)

# ---------------------------------------------------------------------------
# CABEÇALHO
# ---------------------------------------------------------------------------
st.title("Dashboard do Censo Escolar — INEP")
st.markdown(
    "Matrículas da Educação Básica por região, UF e município "
    "(ano-base do Censo Escolar carregado no banco IESB)."
)

# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------
sql_kpi = f"""
    SELECT
        COUNT(DISTINCT c.co_entidade)        AS escolas,
        COALESCE(SUM(m.qt_mat_inf), 0)       AS qt_mat_inf,
        COALESCE(SUM(m.qt_mat_fund), 0)      AS qt_mat_fund,
        COALESCE(SUM(m.qt_mat_fund_af), 0)   AS qt_mat_fund_af,
        COALESCE(SUM(m.qt_mat_med), 0)       AS qt_mat_med
    {BASE_JOIN}
    {where_sql}
"""
kpi = run_query(sql_kpi, where_params).iloc[0]

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Escolas", f"{int(kpi['escolas']):,}".replace(",", "."))
c2.metric("Mat. Infantil", f"{int(kpi['qt_mat_inf']):,}".replace(",", "."))
c3.metric("Mat. Fundamental", f"{int(kpi['qt_mat_fund']):,}".replace(",", "."))
c4.metric("Fund. Anos Finais", f"{int(kpi['qt_mat_fund_af']):,}".replace(",", "."))
c5.metric("Mat. Médio", f"{int(kpi['qt_mat_med']):,}".replace(",", "."))

st.divider()

# ---------------------------------------------------------------------------
# MAPA - matrículas por município (bolhas sobre o mapa do Brasil)
# ---------------------------------------------------------------------------
st.subheader("🗺️ Distribuição geográfica das matrículas")

etapa = st.selectbox(
    "Etapa de ensino exibida no mapa",
    list(MAT_COLS.keys()),
    format_func=lambda k: MAT_COLS[k],
)

sql_mapa = f"""
    SELECT
        mu.nome_municipio,
        uf.sigla_uf,
        r.nome_regiao,
        mu.latitude::float  AS lat,
        mu.longitude::float AS lon,
        COUNT(DISTINCT c.co_entidade) AS escolas,
        COALESCE(SUM(m.{etapa}), 0)   AS matriculas
    {BASE_JOIN}
    {where_sql}
    {"AND" if where_sql else "WHERE"} mu.latitude IS NOT NULL AND mu.longitude IS NOT NULL
    GROUP BY mu.nome_municipio, uf.sigla_uf, r.nome_regiao, mu.latitude, mu.longitude
    HAVING COALESCE(SUM(m.{etapa}), 0) > 0
    ORDER BY matriculas DESC
"""
df_mapa = run_query(sql_mapa, where_params)

if df_mapa.empty:
    st.info("Sem dados para os filtros selecionados.")
else:
    fig_mapa = px.scatter_mapbox(
        df_mapa,
        lat="lat",
        lon="lon",
        size="matriculas",
        color="nome_regiao",
        size_max=40,
        zoom=3,
        hover_name="nome_municipio",
        hover_data={"sigla_uf": True, "escolas": True, "matriculas": ":,",
                    "lat": False, "lon": False, "nome_regiao": False},
        labels={"matriculas": MAT_COLS[etapa], "nome_regiao": "Região"},
        height=560,
    )
    fig_mapa.update_layout(
        mapbox_style="carto-positron",
        margin=dict(l=0, r=0, t=0, b=0),
        legend_title_text="Região",
    )
    st.plotly_chart(fig_mapa, use_container_width=True)

    # ----- Alternativa: mapa coroplético por UF (descomente se quiser) ------
    # Requer um GeoJSON dos estados brasileiros. Exemplo:
    # geojson = requests.get("https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson").json()
    # df_uf_map = ... (agregar por uf.sigla_uf)
    # fig = px.choropleth_mapbox(df_uf_map, geojson=geojson, locations="sigla_uf",
    #                            featureidkey="properties.sigla", color="matriculas",
    #                            mapbox_style="carto-positron", zoom=3,
    #                            center={"lat": -14, "lon": -52})
    # st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# GRÁFICOS ANALÍTICOS
# ---------------------------------------------------------------------------
col_esq, col_dir = st.columns(2)

# --- Matrículas por região (por etapa, empilhado) ---
with col_esq:
    st.subheader("Matrículas por região e etapa")
    sql_reg = f"""
        SELECT r.nome_regiao,
               COALESCE(SUM(m.qt_mat_inf),0)     AS "Educação Infantil",
               COALESCE(SUM(m.qt_mat_fund),0)    AS "Ensino Fundamental",
               COALESCE(SUM(m.qt_mat_med),0)     AS "Ensino Médio"
        {BASE_JOIN}
        {where_sql}
        GROUP BY r.nome_regiao
        ORDER BY 1
    """
    df_reg = run_query(sql_reg, where_params)
    df_reg_long = df_reg.melt(
        id_vars="nome_regiao", var_name="Etapa", value_name="Matrículas"
    )
    fig_reg = px.bar(
        df_reg_long, x="nome_regiao", y="Matrículas", color="Etapa",
        labels={"nome_regiao": "Região"}, barmode="stack",
    )
    fig_reg.update_layout(margin=dict(t=10, b=0), legend_title_text="")
    st.plotly_chart(fig_reg, use_container_width=True)

# --- Matrículas por localização ---
with col_dir:
    st.subheader("Matrículas por localização")
    sql_loc = f"""
        SELECT c.tp_localizacao AS localizacao,
               COALESCE(SUM(m.qt_mat_inf + m.qt_mat_fund + m.qt_mat_med),0) AS matriculas
        {BASE_JOIN}
        {where_sql}
        GROUP BY c.tp_localizacao
        ORDER BY matriculas DESC
    """
    df_loc = run_query(sql_loc, where_params)
    fig_loc = px.pie(df_loc, names="localizacao", values="matriculas", hole=0.45)
    fig_loc.update_layout(margin=dict(t=10, b=0))
    st.plotly_chart(fig_loc, use_container_width=True)

# --- Top 15 UFs por total de matrículas ---
st.subheader("Top UFs por total de matrículas (Infantil + Fundamental + Médio)")
sql_top_uf = f"""
    SELECT uf.nome_uf, uf.sigla_uf,
           COALESCE(SUM(m.qt_mat_inf + m.qt_mat_fund + m.qt_mat_med),0) AS matriculas
    {BASE_JOIN}
    {where_sql}
    GROUP BY uf.nome_uf, uf.sigla_uf
    ORDER BY matriculas DESC
    LIMIT 15
"""
df_top_uf = run_query(sql_top_uf, where_params)
fig_uf = px.bar(
    df_top_uf.sort_values("matriculas"),
    x="matriculas", y="sigla_uf", orientation="h",
    hover_data=["nome_uf"], labels={"matriculas": "Matrículas", "sigla_uf": "UF"},
)
fig_uf.update_layout(margin=dict(t=10, b=0))
st.plotly_chart(fig_uf, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# TABELA DETALHADA POR MUNICÍPIO (com download)
# ---------------------------------------------------------------------------
st.subheader("📋 Detalhamento por município")
sql_tab = f"""
    SELECT r.nome_regiao            AS "Região",
           uf.nome_uf               AS "UF",
           mu.nome_municipio        AS "Município",
           COUNT(DISTINCT c.co_entidade)      AS "Escolas",
           COALESCE(SUM(m.qt_mat_inf),0)      AS "Mat. Infantil",
           COALESCE(SUM(m.qt_mat_fund),0)     AS "Mat. Fundamental",
           COALESCE(SUM(m.qt_mat_fund_af),0)  AS "Fund. Anos Finais",
           COALESCE(SUM(m.qt_mat_med),0)      AS "Mat. Médio"
    {BASE_JOIN}
    {where_sql}
    GROUP BY r.nome_regiao, uf.nome_uf, mu.nome_municipio
    ORDER BY "Mat. Fundamental" DESC
"""
df_tab = run_query(sql_tab, where_params)
st.dataframe(df_tab, use_container_width=True, hide_index=True)
st.download_button(
    "⬇️ Baixar CSV",
    df_tab.to_csv(index=False).encode("utf-8-sig"),
    file_name="censo_escolar_municipios.csv",
    mime="text/csv",
)

st.divider()

# ===========================================================================
# SEÇÃO: PERGUNTE À IA
# ===========================================================================
st.subheader("🤖 Pergunte à IA")
st.caption(
    "Faça uma pergunta em linguagem natural sobre os dados do Censo Escolar. "
    "A integração com o agente será habilitada futuramente."
)

pergunta = st.text_input(
    "Sua pergunta",
    placeholder="Ex.: Qual UF tem mais matrículas no Ensino Médio na região Nordeste?",
)

if st.button("Perguntar", type="primary"):
    if not pergunta.strip():
        st.warning("Digite uma pergunta.")
    else:
        # -------------------------------------------------------------------
        # TEMPLATE DE INTEGRAÇÃO DO AGENTE DE IA (deixar comentado por ora)
        # -------------------------------------------------------------------
        # A ideia é dar ao agente: (1) o contexto/esquema das tabelas,
        # (2) a pergunta do usuário, e (3) ferramentas para consultar o banco
        # (ex.: gerar SQL e executá-lo via run_query) e devolver a resposta.
        #
        # Exemplo usando a Anthropic API (Claude):
        #
        # import anthropic
        #
        # CONTEXTO_DADOS = '''
        # Você responde perguntas sobre o Censo Escolar (INEP), ano carregado no
        # PostgreSQL IESB. Tabelas e junções disponíveis:
        #   inep_censo_escolar c  (1 linha por escola; co_entidade, co_municipio,
        #       co_uf, tp_categoria_escola_privada, tp_localizacao,
        #       tp_localizacao_diferenciada, latitude, longitude)
        #   inep_censo_escolar_matricula m  ON c.co_entidade = m.co_entidade
        #       (qt_mat_inf, qt_mat_fund, qt_mat_fund_af, qt_mat_med, ...)
        #   municipio mu  ON c.co_municipio = mu.codigo_municipio_dv
        #       (nome_municipio, latitude, longitude)
        #   unidade_federacao uf  ON mu.cd_uf = uf.cd_uf (sigla_uf, nome_uf)
        #   regiao r  ON uf.cd_regiao = r.cd_regiao (nome_regiao)
        # Gere SQL PostgreSQL apenas de leitura (SELECT).
        # '''
        #
        # client = anthropic.Anthropic(api_key=st.secrets["ai"]["api_key"])
        # resp = client.messages.create(
        #     model=st.secrets["ai"].get("model", "claude-opus-4-8"),
        #     max_tokens=1024,
        #     system=CONTEXTO_DADOS,
        #     messages=[{"role": "user", "content": pergunta}],
        #     # tools=[{...}]  # ferramenta que chama run_query(sql) e retorna o resultado
        # )
        # resposta = resp.content[0].text
        #
        # # Caso o agente devolva SQL, podemos executá-lo e mostrar o resultado:
        # # df_resp = run_query(sql_gerado)
        # # st.dataframe(df_resp)
        #
        # st.markdown(resposta)
        # -------------------------------------------------------------------

        st.info(
            "🔧 Agente de IA ainda não conectado. O template de integração "
            "está pronto e comentado em `app.py` (seção 'Pergunte à IA'). "
            f"\n\nPergunta recebida: **{pergunta}**"
        )

st.caption("Fonte: INEP — Censo Escolar · Banco de dados IESB")
