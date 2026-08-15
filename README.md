# Gap Finder 🔎

**Encontre o espaço na literatura** — um buscador de lacunas de pesquisa construído sobre a [SerpApi](https://serpapi.com/) (Google Scholar).

Feito para o **SerpApi Python Nordeste Coding Challenge 2026**.

> Given a research topic, Gap Finder tells you *where there is room to publish* — not just what exists.

## O que ele faz

Você digita um tema (ex.: *explainable artificial intelligence*) e o app:

1. **Busca no Google Scholar** (via SerpApi Python SDK) os papers mais relevantes.
2. **Analisa 4 sinais de lacuna** — 100% localmente, sem chamadas extras:
   - **Densidade temporal** — os últimos anos estão sub-publicados? (campo esfriando = espaço se abrindo)
   - **Whitespace de subtópicos** — quais subtemas têm *poucos* papers *e* poucas citações (nicho inexplorado)?
   - **Estagnação de citações** — as citações ainda estão presas a trabalhos antigos (resultado recente sem desdobramento)?
   - **Questões abertas declaradas** — quais papers dizem literalmente *"future work" / "remains open" / "pouco se sabe"*?
3. Gera um **índice de oportunidade de gap (0–100)**, direções sugeridas e uma **reading list** com citações formatadas (APA ou ABNT).

Interface **bilíngue** (PT-BR / EN).

## Por que isso é "uso significativo" da SerpApi

- `google_scholar` (busca com `q`, `num`, `as_ylo`/`as_yhi`)
- Extração de `cited_by`, `publication_info`, `resources[].file_format`
- Citações geradas **localmente** (ABNT NBR 6023 / APA 7) a partir dos dados retornados — evita o custo de `google_scholar_cite` por paper
- Camada de **cache offline** que intercepta toda chamada do SDK (`HTTPClient.request`) — protege os créditos do plano free

## Instalação

```bash
# 1. clone e entre na pasta
git clone https://github.com/<seu-user>/serpapi_challenge26.git
cd serpapi_challenge26

# 2. crie o venv e instale (uv)
uv venv
uv pip install -e .
# ou com pip clássico:
#   python -m venv .venv && .venv/Scripts/pip install -e .

# 3. configure a chave
cp .env.EXAMPLE .env
# edite .env e cole sua SERPAPIKEY
```

## Como rodar

```bash
uv run streamlit run src/serpapi_challenge26/app.py
# ou, se instalado em modo editável:
gap-finder
```

Abra `http://localhost:8501`.

## Modos de cache (não estoure seus créditos)

O `CachingClient` tem 3 modos, controlados por `SERPAPI_MODE` no `.env`:

| Modo | Rede | Créditos | Quando usar |
|------|------|----------|-------------|
| `replay` | ❌ nunca | **0** | desenvolvimento, testes, demo offline (default) |
| `record` | ✅ + salva | custo real | gravar fixtures reais **uma vez** |
| `online` | ✅ | custo real | dados sempre ao vivo |

O app roda **sem chave nenhuma** em `replay` (usa `fixtures/`). Isso também deixa o projeto reproduzível para a banca avaliadora.

## Screenshots

<!-- Cole aqui 1–3 capturas do app rodando -->

## Deploy (bônus)

### Streamlit Cloud

1. Suba o repo no GitHub.
2. Em [share.streamlit.io](https://share.streamlit.io) → "New app" → aponte para o repo.
3. **Main file:** `src/serpapi_challenge26/app.py`.
4. Em **Secrets**, adicione:

   ```
   SERPAPIKEY = "sua_chave"
   SERPAPI_MODE = "online"
   ```

5. Deploy. A app lê a chave de `st.secrets` automaticamente.

### Rodar com pip (alternativa ao uv)

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/streamlit run src/serpapi_challenge26/app.py
```

## Tecnologias

- Python 3.14
- [SerpApi Python SDK](https://github.com/serpapi/serpapi-python) (`google_scholar`)
- [Streamlit](https://streamlit.io/) (UI + deploy)

## Autor

Alley — SerpApi Python Nordeste Coding Challenge 2026
