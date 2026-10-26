# BrandGuard backend: AI and backend module

Python / FastAPI service for the knowledge base, exact rule checks, claim checking, grounded Gemini review, TiDB schema and the accuracy test set.

## How a review works

1. **Exact rules (no AI):** terminology, banned phrases, product-name variants, alt text, inline-style colour contrast (WCAG formula), brand palette on images.
2. **Claim check (no AI needed):** numbers are matched to the approved fact next to them and marked `supported`, `contradicted` or `cannot_verify`. Expired facts and numbers with no fact never count as supported.
3. **Gemini (optional):** retrieves the top guideline passages by embedding similarity and reviews tone and messaging. Every answer is validated in code: the quote must exist in the content, the cited passage id must be one we sent, a claim verdict needs a real fact id. Anything else is dropped or downgraded to `cannot_verify`.

If Gemini is missing or fails, the review still returns every exact finding plus an `ai_error` note.

## Run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill DATABASE_URL (TiDB) and GEMINI_API_KEY
uvicorn app.main:app --reload
```

Tables are created on startup. TiDB Cloud needs TLS; it is enabled automatically for `mysql+pymysql://` URLs.

Load the sample brand kit (imaginary company, made-up data only):

```python
from app.db import SessionLocal, init_db
from app.kit import load_kit
init_db(); s = SessionLocal()
print(load_kit(s, "sample_kit/northwind.json"))   # prints the org id; embeds guidelines if GEMINI_API_KEY is set
```

## Main endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/orgs` | create organisation (product names, palette) |
| POST | `/orgs/{id}/kb/documents` | upload PDF/DOCX/TXT/MD guidelines (chunked + embedded) |
| POST/GET | `/orgs/{id}/kb/facts`, `/kb/terms` | approved facts and preferred/banned terms |
| POST | `/orgs/{id}/kb/reembed` | embed passages saved while the API was down |
| POST | `/orgs/{id}/review/text` | `{text, channel, use_ai}` returns findings + claim verdicts |
| POST | `/orgs/{id}/review/image` | image upload + alt text |
| POST | `/orgs/{id}/review/contrast` | `{fg, bg, large_text, level}` |
| PATCH | `/findings/{id}` | accept / dismiss (reason required) / mark incorrect |
| GET | `/orgs/{id}/insights/rules` | per-rule counts and dismissal rate for the dashboard |

Interactive docs at `/docs`.

## Accuracy test

```bash
python -m eval.run_eval                                  # exact rules + claims
python -m eval.run_eval --ai                             # adds Gemini (needs key)
python -m eval.run_eval --min-recall 0.8 --max-false-alarms 0
pytest
```

`eval/testset.json` holds 30 items: 20 with planted mistakes (22 expected findings) and 10 clean items. The harness prints planted mistakes found, false alarms on clean items, and extra findings on planted items. Report these numbers for the "at least 80% of planted mistakes" target.

## Known limits (say these honestly in the demo)

- Contrast is checked for HTML inline styles and hex pairs, not for text inside images (that would need OCR).
- Palette check looks at dominant colours only: best for banners and graphics, not photos. Logo matching is not built yet.
- Claim matching is keyword-based. Each fact needs good `keywords`; wording that avoids them becomes `cannot_verify`, never a false "supported".
- Embeddings live in a JSON column and are compared in Python: fine for a small knowledge base.
- The free Google AI Studio tier may use submitted data to improve Google products: use made-up sample data only.
- Login/JWT, comments, approvals and version history belong to the workflow module; add its auth dependency to these routes.
- The Gemini model name defaults to `gemini-2.5-flash`; set `GEMINI_MODEL` to whatever your key can use.

## Declaration

Generated with AI assistance (Claude). Declare this as the hackathon rules require, and review and understand every file before you present it.
