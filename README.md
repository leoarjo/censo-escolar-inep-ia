# Censo Escolar (INEP) — Dashboard + IA

Dashboard interativo em **Streamlit** sobre os dados do Censo Escolar (INEP), com mapas de matrículas por município e um chatbot integrado ao **Amazon Bedrock (Claude)** que responde perguntas em linguagem natural consultando o banco de dados automaticamente.

---

## Funcionalidades

- **Filtros** por região, UF, localização (urbana/rural) e categoria da rede privada
- **KPIs** com número de escolas e matrículas por etapa (Infantil, Fundamental, Anos Finais, Médio)
- **Mapa** de bolhas por município
- **Gráficos** de matrículas por região, localização e ranking de UFs
- **Tabela** detalhada por município com exportação CSV
- **Chatbot com IA** — faça perguntas em português e o assistente consulta o banco automaticamente

---

## Pré-requisitos

- Python 3.10 ou superior
- Acesso ao banco PostgreSQL do IESB (`bigdata.dataiesb.com`)
- Acesso ao portal AWS do IESB (`https://d-90663e488b.awsapps.com/start`)

---

## Instalação

**1. Clone o repositório ou baixe o `app.py`**

**2. Instale as dependências:**
```bash
pip install streamlit pandas plotly sqlalchemy psycopg2-binary boto3
```

Ou se houver `requirements.txt`:
```bash
pip install -r requirements.txt
pip install boto3
```

---

## Configuração

### 1. Credenciais do banco (secrets.toml)

Crie a pasta `.streamlit` dentro da pasta do projeto e o arquivo `secrets.toml` dentro dela:

```
projeto/
  app.py
  .streamlit/
    secrets.toml
```


### 2. Credenciais AWS (Bedrock)

Acesse o portal AWS do IESB:
**https://d-90663e488b.awsapps.com/start**

1. Faça login com seu usuário institucional
2. Clique em **Sergio da Costa Cortes**
3. Clique em **BedrockFullAccess → Credenciais de acesso programático**
4. Vá na aba **PowerShell**
5. Copie as 3 linhas da **Opção 1** e cole no terminal **antes** de rodar o app:

```powershell
$Env:AWS_ACCESS_KEY_ID="sua_key_id"
$Env:AWS_SECRET_ACCESS_KEY="sua_secret_key"
$Env:AWS_SESSION_TOKEN="seu_token"
```

> ⚠️ Essas credenciais expiram em ~8 horas. Quando expirar, repita esse passo.

> ⚠️ Cole as credenciais e rode o Streamlit no **mesmo terminal**.

---

## Como rodar

No terminal, dentro da pasta do projeto:

```powershell
# 1. Cole as credenciais AWS (passo acima)

# 2. Rode o app
streamlit run app.py
```

O app abrirá automaticamente no navegador em `http://localhost:8501`

---

## Como usar o chatbot

Na seção **"Pergunte à IA"** no final do dashboard, digite perguntas como:

- *"Qual UF tem mais matrículas no Ensino Médio?"*
- *"Quantas escolas rurais existem no Nordeste?"*
- *"Compare as matrículas de SP e MG no Ensino Fundamental."*
- *"Qual município do DF tem mais matrículas?"*

O assistente consulta o banco automaticamente e responde em português.

---

## Estrutura do projeto

```
projeto/
  app.py              # aplicação principal
  requirements.txt    # dependências
  .streamlit/
    secrets.toml      # credenciais do banco (não commitar no git)
```

---

## Observações

- O arquivo `secrets.toml` **não deve ser enviado ao GitHub** — ele já está no `.gitignore`
- As credenciais AWS são pessoais e temporárias — cada usuário pega as suas no portal do IESB
- Fonte dos dados: INEP — Censo Escolar · Banco de dados IESB
