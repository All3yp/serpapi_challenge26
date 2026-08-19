# Gap Finder 🔎

**Encontre o espaço na literatura** — um buscador de lacunas de pesquisa construído sobre a [SerpApi](https://serpapi.com/) (Google Scholar).

> Dado um tema de pesquisa, o Gap Finder diz **onde há espaço para publicar** — não apenas o que já existe.

---

## O que ele faz

Você digita um tema (ex.: *explainable artificial intelligence*) e o app:

1. **Busca no Google Scholar** os papers mais relevantes (via SerpApi Python SDK).
2. **Analisa 4 sinais de lacuna**, 100% localmente:
   - **Densidade temporal** — os últimos anos estão sub-publicados? (campo esfriando = espaço abrindo)
   - **Whitespace de subtópicos** — subtemas com *poucos* papers *e* poucas citações (nicho inexplorado)
   - **Estagnação de citações** — citações presas a trabalhos antigos (resultado recente sem desdobramento)
   - **Questões abertas declaradas** — papers que dizem literalmente *"future work" / "remains open" / "pouco se sabe"*
3. Gera um **índice de oportunidade de gap (0–100)**, direções sugeridas e uma **reading list** com citações formatadas.

Interface **bilíngue** (PT-BR / EN), **modo offline** que não gasta créditos e tópicos demo prontos para avaliação rápida.

---

## Como funciona por baixo

### Pipeline

```
query ──► Scholar.search_all() ──► [Paper, Paper, ...] ──► GapAnalyzer ──► GapReport
              (SerpApi SDK)            (normalização)        (4 sinais)        (score + direções)
```

### Score de oportunidade (0–100)

Média ponderada dos quatro sinais, cada um normalizado e limitado a 0–100:

| Sinal | Peso | O que mede |
|-------|------|-----------|
| Temporal | 0.35 | fração de papers dos últimos 3 anos (esfriando = gap) |
| Whitespace | 0.25 | termos pouco explorados (poucos papers + poucas citações) |
| Estagnação | 0.25 | citações concentradas em trabalho antigo |
| Open questions | 0.15 | declarações explícitas de "future work" / lacuna |

Pesos e limiares ficam em `src/gap_finder/gap.py` (`Thresholds`), ajustáveis sem tocar na lógica.

### Uso da SerpApi

- `google_scholar` (`q`, `num`, `as_ylo`/`as_yhi`, `start` para paginação)
- Extração de `cited_by`, `publication_info`, `resources[].file_format`
- Citações geradas **localmente** (ABNT NBR 6023 / APA 7 / IEEE / Vancouver / MLA / Chicago / BibTeX) a partir dos dados retornados — evita o custo de `google_scholar_cite` por paper
- Camada de **cache offline** que intercepta toda chamada do SDK (`HTTPClient.request`) — protege os créditos do plano free

---

## Instalação

Requer Python **3.10+**.

```bash
# 1. clone
git clone https://github.com/All3yp/gap-finder.git
cd gap-finder

# 2. ambiente + dependências (uv)
uv sync

# 3. configure a chave (opcional — veja "modos de cache")
cp .env.EXAMPLE .env
# edite .env e cole sua SERPAPIKEY
```

Com pip clássico:

```bash
python -m venv .venv
.venv/Scripts/activate          # no Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## Como rodar

```bash
uv run gap-finder
# ou
uv run python main.py
```

Abra `http://localhost:8501`.

Tópicos demo disponíveis no app:

- `explainable artificial intelligence`
- `climate change adaptation`
- `quantum machine learning`

---

## Modos de cache (não estoure seus créditos)

O `CachingClient` tem 3 modos, controlados por `SERPAPI_MODE` (`.env` ou `st.secrets`):

| Modo | Rede | Créditos | Quando usar |
|------|------|----------|-------------|
| `replay` | ❌ nunca | **0** | desenvolvimento, testes, demo offline (default) |
| `record` | ✅ + salva | custo real | gravar fixtures reais **uma vez** |
| `online` | ✅ | custo real | dados sempre ao vivo |

O app roda **sem chave nenhuma** em `replay` (usa `fixtures/`). Isso torna o projeto reproduzível e demonstrável sem gastar um crédito sequer.

---

## Deploy no Streamlit Cloud

1. Suba o repo no GitHub (público).
2. Em [share.streamlit.io](https://share.streamlit.io) → **New app** → aponte para o repo.
3. **Main file:** `streamlit_app.py`.
4. Em **Advanced settings**, escolha Python **3.11** (o código é compatível com 3.10+).
5. Em **Secrets**, adicione:

   ```
   SERPAPIKEY = "sua_chave"
   SERPAPI_MODE = "replay"     # demo sem custo; use "online" para dados ao vivo
   ```

O app lê a chave de `st.secrets` automaticamente (`config.py`).

> **Por que `streamlit_app.py`?** O Cloud roda na raiz do repo, onde o pacote em `src/` não é importável sem build. O shim `streamlit_app.py` injeta `src/` no `sys.path` e delega para o app real.

---

## Internacionalização

A interface é traduzida via **gettext** (`.po`/`.mo`) com suporte a **plural** (`ngettext`). Para adicionar um idioma:

1. Crie `locale/<lang>/LC_MESSAGES/messages.po` (traduza o `.po` do PT como base).
2. Compile: `uv run pybabel compile -D messages -d locale`.

Os títulos/snippets/autores **não são traduzidos** — são dados-fonte do Scholar e devem permanecer originais para a citação bibliográfica.

---

## Testes

```bash
uv run pytest
```

160 testes cobrindo análise de gap, paginação, cache, citação, i18n e a camada de UI.

---

## Estrutura

```
src/gap_finder/
  app.py        UI Streamlit (bilíngue, tabs)
  scholar.py    busca + normalização + formatação de citações
  gap.py        os 4 sinais de lacuna + score + direções
  caching.py    cache offline (replay/record/online)
  config.py     chave de API + modo (.env / st.secrets)
  i18n.py       gettext, locale, número/plural
streamlit_app.py  shim de deploy no Streamlit Cloud
fixtures/         respostas gravadas do Scholar (modo replay)
locale/           catálogos de tradução (.po/.mo)
tests/            suíte de testes
```

## Licença

MIT — veja [`LICENSE`](LICENSE).

## Autor

Alley — [github.com/All3yp](https://github.com/All3yp)
