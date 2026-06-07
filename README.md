# Censo Escolar (INEP) — Dashboard + IA

Dashboard interativo em **Streamlit** sobre os dados do **Censo Escolar (INEP)**,
com mapas de matrículas por município e uma seção preparada para um **agente de IA**.

Fonte de dados: PostgreSQL (`bigdata.dataiesb.com` / banco `iesb`).

## Funcionalidades

- **Filtros**: região, UF (dependente da região), localização (urbana/rural) e categoria da rede privada.
- **KPIs**: nº de escolas e matrículas por etapa (Infantil, Fundamental, Fund. Anos Finais, Médio).
- **🗺️ Mapa**: bolhas por município (tamanho = matrículas, cor = região) sobre o mapa do Brasil.
- **Gráficos**: matrículas por região × etapa, por localização e top UFs.
- **Tabela detalhada** por município + download em CSV.
- **🤖 Pergunte à IA**: interface pronta; template de integração do agente comentado em `app.py`.

## Modelo de dados

```
inep_censo_escolar  c   (1 linha por escola, co_entidade)
  LEFT JOIN inep_censo_escolar_matricula m  ON c.co_entidade  = m.co_entidade   -- QT_MAT_*
  JOIN      municipio                   mu  ON c.co_municipio = mu.codigo_municipio_dv  -- nome + lat/long
  JOIN      unidade_federacao           uf  ON mu.cd_uf       = uf.cd_uf
  JOIN      regiao                        r ON uf.cd_regiao   = r.cd_regiao
```

> As variáveis de matrícula (`qt_mat_inf`, `qt_mat_fund`, `qt_mat_fund_af`, `qt_mat_med`)
> vivem na tabela `inep_censo_escolar_matricula`, não na `inep_censo_escolar`.

## Como executar

```bash
pip install -r requirements.txt

# configure as credenciais
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edite .streamlit/secrets.toml com usuário e senha

streamlit run app.py
```

O app abre em `http://localhost:8501`.

## Integração com o agente de IA

A seção "Pergunte à IA" já tem a interface. O template de integração (Anthropic /
Claude, incluindo o contexto do esquema das tabelas e a ideia de gerar/executar SQL)
está comentado em `app.py`, dentro do bloco do botão **Perguntar**. Para habilitar,
preencha a seção `[ai]` em `secrets.toml` e descomente o template.

## Estrutura

```
app.py                       # dashboard Streamlit
requirements.txt             # dependências
.streamlit/secrets.toml      # credenciais (NÃO versionado)
.streamlit/secrets.toml.example
.gitignore
```
