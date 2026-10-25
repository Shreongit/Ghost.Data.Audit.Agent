# Ghost Data Still Exists — deletion audit agent

This runnable Python solution investigates deletion requests using only the participant-facing files under `dataset/`. It resolves current and historical identities at each `audit_at`, links evidence to resources, reconstructs point-in-time state, applies `deletion_rules.csv`, and emits the required CSV.

## Architecture

```text
dataset/* ──► parsers + cached PDF/OCR/VLM text ──► provenance evidence graph
                                                        │
request ──► multilingual intent gate ──► cutoff identity aliases
                                                        │
                       graph walk ──► state replay ──► condition-aware policy
                                                        │
                  optional structured LLM hints ────────┤
                                                        ▼
                 deterministic findings/remediation/verification
                          ──► pure orderer ──► contract validator ──► output.csv
```

The deterministic pipeline is the default and works offline. Resource links preserve evidence provenance and are globally checked for conflicting owners. Log events are grouped by trace/request/session IDs, including JSON logs with quoted keys; OCR/PDF facts use resource-local context to avoid linking unrelated records on the same page. Low-confidence activity-window plus probe candidates are recorded but not treated as ownership proof. See `code/linking/PATTERNS.md` for the sample evidence audit and `weights.json` for frozen link weights.

An optional bounded tool agent can inspect unresolved links with read-only evidence search, trace-group, activity-window, SELECT-only SQLite, alias-set, and resource-fact tools. Every proposed link must pass a deterministic verifier against cutoff-valid cited evidence. Model JSON is schema-checked; intent rationales and category citations must be found in the request/evidence text. Models cannot directly write the final step list.

## Setup

Windows PowerShell:

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r code\requirements.txt
winget install --id UB-Mannheim.TesseractOCR -e
```

macOS: `brew install tesseract`, then create the venv and install `code/requirements.txt`.

Debian/Ubuntu: `sudo apt-get install tesseract-ocr`, then create the venv and install `code/requirements.txt`.

If Tesseract is installed somewhere nonstandard, set `TESSERACT_CMD` to its executable. PNG OCR uses pytesseract and native Tesseract; PDF extraction uses pdfplumber with pypdf fallback. Text extractions are cached under `code/.cache/extractions/` by source SHA-256.

Optional xAI provider setup (keep the key in the environment; never add it to a file):

```powershell
$env:LLM_PROVIDER = 'xai'
$env:XAI_API_KEY = '<your xAI API key>'
$env:LLM_MODEL_FAST = '<model id from your xAI console>'
$env:LLM_MODEL_STRONG = '<model id from your xAI console>'
$env:LLM_INPUT_USD_PER_MILLION = '<console input rate>'
$env:LLM_OUTPUT_USD_PER_MILLION = '<console output rate>'
```

The provider uses the OpenAI Python SDK at `https://api.x.ai/v1`, tries JSON Schema output first, and falls back to JSON mode with local schema validation and a repair retry when constrained output is unavailable. It sends images only when the opt-in LLM path is enabled.

Optional Groq provider setup uses model IDs available to the configured API key (query `https://api.groq.com/openai/v1/models` first):

```powershell
$env:LLM_PROVIDER = 'groq'
$env:GROQ_API_KEY = '<your Groq API key>'
$env:LLM_MODEL_FAST = '<listed model id>'
$env:LLM_MODEL_STRONG = '<listed model id>'
```

The current provider caps concurrent SDK requests at two, backs off on HTTP 429, and caches successful text and structured calls. PNGs are sent only to a listed image-capable model; this path compares VLM facts with the cached Tesseract transcript.

## Run

Run all requests using the offline deterministic pipeline:

```powershell
.venv\Scripts\python.exe code\main.py --no-llm
```

To enable Groq or xAI after setting the matching environment variables above, use `--llm`; the bounded investigator defaults to 25 ambiguous cases.

Run only a small set or trace evidence-graph paths:

```powershell
.venv\Scripts\python.exe code\main.py --no-llm --cases case_01,case_07 --trace-case case_01,case_07 --output trace.csv --verbose
```

Evaluate public samples and run unit tests:

```powershell
.venv\Scripts\python.exe code\main.py --no-llm --input dataset\sample_deletion_requests.csv --output sample_predictions.csv
.venv\Scripts\python.exe code\evaluation\main.py --predictions sample_predictions.csv --write-report
.venv\Scripts\python.exe -m unittest discover -s code\tests -v
```

Full-dataset invariants (there are no gold answers for these 518 requests):

```powershell
.venv\Scripts\python.exe code\evaluation\main.py --predictions output.csv
```

The output is UTF-8 without BOM, sorted numerically by `case_id`. Repeated offline runs are deterministic. Use `--refresh-cache` to clear extraction and model caches; use `--trace-case ids` to print aliases, matched evidence facts, and graph paths.

## Optional structured LLM/VLM

Only use `--llm` when an authorized provider account and API key are configured in environment variables. Supported `LLM_PROVIDER` values are `openai`, `anthropic`, and `gemini`; set the provider key (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `GEMINI_API_KEY`), `LLM_MODEL_FAST`, and (for tool-based link investigation) `LLM_MODEL_STRONG`. The tool agent checks at most 25 unresolved cases by default and at most five tool steps per case; override with `--link-agent-max-cases`. For a hard spend guard, set both `LLM_INPUT_USD_PER_MILLION` and `LLM_OUTPUT_USD_PER_MILLION` to the rates for the selected model, then pass `--budget-usd`:

```powershell
$env:LLM_PROVIDER = 'openai'
$env:LLM_MODEL_FAST = '<your-model-id>'
$env:LLM_MODEL_STRONG = '<your-strong-model-id>'
$env:OPENAI_API_KEY = '<read from your secret manager>'
$env:LLM_INPUT_USD_PER_MILLION = '<provider rate>'
$env:LLM_OUTPUT_USD_PER_MILLION = '<provider rate>'
.venv\Scripts\python.exe code\main.py --llm --budget-usd 1.00
```

Never paste credentials into source files, logs, prompts, or the archive. Structured calls use temperature zero, a prompt/input/schema hash cache under `code/.cache/llm/`, schema validation with one repair retry, bounded retries, and token/cost accounting in `code/.cache/usage.json`. Groq was evaluated live using model IDs and prices returned from its authenticated `/models` endpoint. The fast vision model was `qwen/qwen3.8-27b`; the strong structured model was `openai/gpt-oss-120b`.

## Evaluation and known limits

`code/evaluation/evaluation_report.md` contains public-sample metrics, first differing steps with cause labels, operation/category metrics, custom cases, cumulative OOF linker ablations, source-ID grep results, and full-run invariants. `code/linking/heldout_link_misses.md` lists every held-out account and analytics miss with competing candidates and timing/result signals. OOF offsets are refitted on 31 public cases per fold; `offsets.json` is the all-public-sample production calibration. No account IDs are inferred from user-number suffixes. Per-case OOF prediction JSON is diagnostic-only and excluded from `code.zip`.

The latest reproduced sample evaluation reports 32/32 status accuracy, 91.67% step F1, and 18/32 exact sequences; the requested 92% F1 and 20 exact sequence targets remain unmet. Account and analytics OOF linkage targets remain below 90%; 395 full-run resource assignments are marked ambiguous. Two authorized full-run plans use a low-confidence catalog-link fallback, listed in the report. The live Groq sample matched the deterministic baseline and the live results passed the non-regression gate. See the usage report for 99 successful inference completions, tokens, costs, 11 PNG comparisons, and rate-limit handling.

PDF support uses `pdfplumber` with `pypdf` fallback. Image OCR requires the Python packages in `code/requirements.txt` and native Tesseract; on Windows install Tesseract with `winget install --id UB-Mannheim.TesseractOCR -e`. The default executable path is `C:\Program Files\Tesseract-OCR\tesseract.exe`; set `TESSERACT_CMD` if it is installed elsewhere. `--refresh-cache` rebuilds OCR/PDF extraction from evidence files.

## Package

Build `code.zip` with the intended `code/` paths while excluding datasets, caches, virtual environments, and bytecode:

```powershell
.venv\Scripts\python.exe code\package.py
```

Submit `code.zip`, root `output.csv`, and `log.txt` separately.
