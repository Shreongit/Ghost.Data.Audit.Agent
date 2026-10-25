<div align="center">

# Ghost Data Audit Agent

### Proving that "deleted" really means deleted

**A source-first Python agent that audits whether a person's personal data is truly gone across databases, logs, search indexes, exports, support tickets, analytics and backups, and tells you exactly what to fix if it is not.**

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Approach](https://img.shields.io/badge/Approach-Deterministic%20%2B%20LLM-6f42c1)
![Evidence](https://img.shields.io/badge/Evidence-SQL%20%7C%20JSON%20%7C%20Logs%20%7C%20PDF%20%7C%20PNG-blue)
![Tests](https://img.shields.io/badge/Tests-49%20passing-brightgreen)
![Event](https://img.shields.io/badge/HackerRank-Orchestrate%20Oct%202026-00ea64)
![License](https://img.shields.io/badge/License-All%20rights%20reserved-lightgrey)

**Current release:** `v1.0.0` (HackerRank Orchestrate submission)

[Overview](#overview) · [Results](#results) · [How it works](#how-it-works) · [Quick start](#quick-start) · [Evaluation](#evaluation) · [Design decisions](#design-decisions) · [Limitations](#limitations) · [Roadmap](#roadmap) · [Author](#author)

</div>

---

## Overview

Northstar Shop (a fictional company in the challenge) lost **$2.4 million** after a customer whose deletion request showed **"Complete"** in every dashboard came back as a "ghost": their email was still registered, and their data still lived in replicas, search indexes, support attachments, analytics exports, logs and backups. A sync job had even re-created data the primary service had already deleted.

This project is the **deletion audit agent** that would have caught it. For each deletion request it:

1. decides whether deletion was actually requested (`COMPLETE`, `INCOMPLETE` or `NOT_APPLICABLE`);
2. resolves the person's **current and historical identifiers** (emails, phones, hashes, user ids);
3. reconstructs what really exists **at the audit time**, treating workflow statuses as claims, not proof;
4. applies the company deletion policy (delete, redact, anonymize, **retain**, keep an account tombstone);
5. finds **active data flows and restore paths** that can bring deleted data back;
6. outputs an **ordered list** of findings, remediation actions and verification checks as machine-readable JSON.

> Built for the [HackerRank Orchestrate October 2026](https://www.hackerrank.com/contests/hackerrank-orchestrate-october26/challenges/ghost-data-still-exists) challenge **"Ghost Data Still Exists"**. All people, companies and records in the dataset are fictional.

---

## Why this is a hard problem

| Challenge | What makes it tricky |
|---|---|
| Identity changes | The request email may be an *old* email; historical evidence only shows old identifiers. |
| Claims vs proof | `reported_status = COMPLETE` and `SUCCESS` log lines are not evidence that data is gone. |
| Time | Only evidence available at or before `audit_at` may be used; later deletes or re-syncs change the answer. |
| Records with no name on them | Many resource ids (for example an account id in an activity log) carry no email at all and must be **linked** to a person through indirect evidence. |
| Policy | Some data must be kept (security audit logs, legal holds); some must be redacted or anonymized, not deleted. |
| Messy evidence | SQL replicas, JSON exports, six log dialects, PDFs and screenshots. |
| Exact output | The grader compares step order, systems, resources, operations and evidence ids. |

---

## Results

Measured on the 32 public sample cases with known answers and on the full 518-case run.

| Metric | Result |
|---|---|
| Deletion status accuracy (sample) | **32 / 32** |
| Step-level F1 (sample) | **91.67 %** |
| Exact step sequence (sample) | **18 / 32** |
| Full run | **518 rows**, 0 invariant errors, no empty plans, **byte-identical** across runs |
| Held-out resource linking (account) | 83.9 % precision / 81.3 % recall |
| Held-out resource linking (analytics) | 81.8 % precision / 69.2 % recall |
| Unit tests | **49 passing** |
| Live LLM run (Groq) | 99 calls, ~90k input / ~30k output tokens, **≈ $0.06** |

The sample numbers are partly in-sample because link weights were calibrated on the same 32 cases. **Held-out numbers are reported honestly** in [`code/evaluation/evaluation_report.md`](code/evaluation/evaluation_report.md), with every miss listed in [`code/linking/heldout_link_misses.md`](code/linking/heldout_link_misses.md).

---

## How it works

```text
                     ┌─────────────────────────────────────────────┐
 dataset/*.csv  ───► │ Loaders: requests · identities · audit log  │
 evidence/**    ───► │ · activity · rules · evidence manifest      │
                     └──────────────────────┬──────────────────────┘
                                            ▼
        ┌───────────────────────────────────────────────────────────────┐
        │ Evidence ingestion: SQL (SQLite) · JSON · 6 log dialects ·     │
        │ text · PDF · PNG (Tesseract OCR + optional vision model)       │
        └───────────────────────────────┬───────────────────────────────┘
                                        ▼
                     ┌──────────────────────────────────────┐
  request text ────► │ Intent gate (multilingual) ──► NOT_APPLICABLE → []
                     └──────────────────┬───────────────────┘
                                        ▼
                     ┌──────────────────────────────────────┐
                     │ Identity resolver (current + historical│
                     │ emails, phones, hashes, user_id)       │
                     └──────────────────┬───────────────────┘
                                        ▼
        ┌───────────────────────────────────────────────────────────────┐
        │ Linker: evidence graph + trace-id joins + time-anchored       │
        │ scoring + global one-to-one assignment across all requests    │
        └───────────────────────────────┬───────────────────────────────┘
                                        ▼
        State at audit_at ─► Category classifier ─► Policy engine (deletion_rules.csv)
                                        ▼
        Planner ─► Orderer ─► Serializer ─► Validator ─► output.csv
                                        ▲
        Optional LLM/VLM layer (Groq / xAI): reads images, investigates
        ambiguous links, classifies edge cases; every answer is checked
        against the evidence before it is accepted.
```

**Key ideas**

- **Evidence graph.** Every fact keeps its source id (`file_id`, `activity_id`, `audit_id`) and timestamp, so each finding is explainable.
- **Time-anchored linking.** The deletion worker's events sit in a narrow, type-specific time band around each request's `reported_at`. Combined with status-to-result patterns and evidence links, requests are matched to resources **jointly across all 550 requests**, so a resource can belong to only one person.
- **Deterministic core, LLM as a checked assistant.** The planner never lets a model write the final steps; models propose facts with citations and code verifies them.
- **Reproducible.** Same input → identical bytes; LLM calls are cached; keys come only from environment variables.

---

## Output format

One row per case, sorted by `case_id`:

```csv
case_id,deletion_status,steps_json
case_000,NOT_APPLICABLE,[]
```

`steps_json` is an ordered JSON array. Example step:

```json
{
  "step_no": 1,
  "phase": "FINDING",
  "system_id": "account_service",
  "resource_id": "account_005",
  "operation": "REPORT_REMAINING_RECORD",
  "state": "PRESENT",
  "evidence_id": "evidence_01"
}
```

Phases run **FINDING → REMEDIATION → VERIFICATION**. Proposed (future) steps carry an empty `evidence_id`.

---

## Quick start

**Requirements:** Python 3.10+, optionally [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) for screenshots.

```bash
git clone https://github.com/ifshreyas/ghost-data-audit-agent.git
cd ghost-data-audit-agent

python -m venv .venv
# Windows:  .venv\Scripts\activate      macOS/Linux:  source .venv/bin/activate
pip install -r code/requirements.txt
```

Place the challenge files in `dataset/` (not included in this repository), then:

```bash
# Full run, deterministic mode (no API key needed)
python code/main.py --no-llm

# Full run with the optional LLM/VLM layer
export LLM_PROVIDER=groq          # or xai
export GROQ_API_KEY=...           # never commit keys
python code/main.py

# Evaluate against the public samples
python code/main.py --input dataset/sample_deletion_requests.csv --output sample_predictions.csv --no-llm
python code/evaluation/main.py --predictions sample_predictions.csv

# Explain how one case was decided
python code/main.py --no-llm --trace-case case_09

# Run the tests
python -m unittest discover -s code/tests
```

> Check `python code/main.py --help` for the exact flags in your version.

---

## Evaluation

The `code/evaluation/` folder contains:

- **`evaluation_report.md`**: status accuracy, step precision/recall/F1, per-field accuracy, sequence accuracy, held-out linking accuracy, ablations, custom test cases, failures found and fixes made.
- **`usage_report.md`**: model providers and models, call counts, input/output tokens, average tokens per request, estimated cost.
- **`main.py`**: the evaluation harness (also runs invariants on the full 518-case output: valid JSON, consecutive steps, phase order, valid evidence ids not after `audit_at`).

---

## Design decisions

1. **Removed a tempting shortcut.** An early version assumed user `N` owns `account_00N`. It scored well on the first samples but would silently fail on most hidden cases, so it was deleted and replaced by real evidence linking.
2. **Honest evaluation.** Link weights are calibrated on samples; the report separates in-sample from held-out numbers.
3. **Safe LLM use.** Models never emit the final plan. Output is schema-checked, citations must exist and be valid at `audit_at`, and live results are kept only if accuracy does not regress.
4. **Policy first.** Retention rules (security audit logs, legal holds, backups) are respected: the agent blocks restores and redacts tombstones instead of deleting what must be kept.

---

## Limitations

- Linking people to resources that carry no identifier is the main source of errors (see held-out numbers).
- Exact step ordering matches the reference in 18 of 32 sample cases.
- In the live run the LLM layer cross-checked OCR and examined ambiguous links but did not change the final answers; the deterministic pipeline produces them.
- Built and tuned on a synthetic dataset; real systems need real connectors and access controls.

---

## Roadmap

- [ ] Raise held-out linking accuracy above 90 % for accounts and analytics
- [ ] Improve exact-sequence accuracy with a per-case ordering diff report
- [ ] Add more custom adversarial cases (decoy users, re-enabled sync flows, late evidence)
- [ ] Optional web UI to explore a case's evidence graph
- [ ] Pluggable connectors for real data stores

---

## Tech stack

Python · SQLite · `csv` / `json` / `re` / `hashlib` · Tesseract OCR · OpenAI-compatible SDK (Groq, xAI) · `unittest`

---

## Author

**Shreyas Pathak**: B.Tech CSE, PSIT Kanpur · [GitHub @ifshreyas](https://github.com/ifshreyas) · [LinkedIn](https://linkedin.com/in/shreyaspathakk)

---

## License

All rights reserved. The challenge dataset belongs to its organizers and is not included in this repository.
