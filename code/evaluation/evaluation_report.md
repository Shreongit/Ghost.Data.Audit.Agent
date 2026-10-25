> **Live Groq evaluation:** model IDs were selected from the authenticated `/models` listing. `qwen/qwen3.8-27b` handled images and `openai/gpt-oss-120b` handled structured link investigation. The live sample matched the deterministic baseline; live results were retained.

# Evaluation report

## Public calibration set

- Cases: 32
- Case-level deletion-status accuracy: 32/32 (100.00%).
- Confusion matrix (gold rows, predicted columns ordered COMPLETE, INCOMPLETE, NOT_APPLICABLE):

| Gold \ Predicted | COMPLETE | INCOMPLETE | NOT_APPLICABLE |
|---|---|---|---|
| COMPLETE | 10 | 0 | 0 |
| INCOMPLETE | 0 | 22 | 0 |
| NOT_APPLICABLE | 0 | 0 | 0 |

- Step-set precision/recall/F1: 92.15%/91.19%/91.67%.
- Exact sequence accuracy: 18/32 (56.25%); mean normalized LCS: 88.66%.
- Field-level accuracy: phase 89.95%, system_id 81.91%, resource_id 80.40%, operation 80.90%, state 81.41%, evidence_id 90.45%, step_no 92.96%.
- Operation-only F1: 96.88%; per-operation F1: {"ANONYMIZE_RECORD": 0.9091, "BLOCK_RESTORE": 1.0, "DELETE_RECORD": 0.9767, "DISABLE_DATA_FLOW": 1.0, "REDACT_RECORD": 1.0, "REPORT_ACTIVE_DATA_FLOW": 1.0, "REPORT_EXPOSED_PII": 0.9565, "REPORT_REMAINING_RECORD": 0.9767, "REPORT_RESTORE_RISK": 1.0, "VERIFY_DATA_FLOW_DISABLED": 1.0, "VERIFY_RECORD_ABSENT": 1.0, "VERIFY_RECORD_ANONYMIZED": 0.96, "VERIFY_RECORD_PRESENT": 0.8293, "VERIFY_RECORD_REDACTED": 1.0, "VERIFY_RESTORE_BLOCKED": 1.0}.
- Per-data-category F1: {"ACCOUNT_TOMBSTONE": 1.0, "ANALYTICS_PROFILE": 1.0, "BACKUP_ARCHIVE": 1.0, "DATA_FLOW": 1.0, "SEARCH_INDEX_ENTRY": 0.9231, "SECONDARY_IDENTIFIER": 1.0, "SECURITY_AUDIT_LOG": 0.8718, "SUPPORT_ATTACHMENT": 1.0, "SUPPORT_MESSAGE": 1.0, "UNKNOWN": 0.9032, "USER_EXPORT": 1.0, "USER_PROFILE": 1.0}.
- Error taxonomy: {"extra_step": 15, "missing_or_wrong_record": 7, "missing_record_or_step": 6, "wrong_evidence_id": 1}.
- Sample invariant errors: 0. Full-run invariant errors: 0.

## Additional participant-authored cases

- **non-English non-deletion** — expected `NOT_APPLICABLE; steps=[]` — PASS.
- **historical email and cutoff hash** — expected `old email + its sha256 alias active; future email excluded` — PASS.
- **re-enabled sync flow** — expected `REPORT_ACTIVE_DATA_FLOW; DISABLE_DATA_FLOW; VERIFY_DATA_FLOW_DISABLED` — PASS.
- **evidence after audit cutoff** — expected `no linked finding or step` — PASS.
- **tombstone still contains email** — expected `REPORT_EXPOSED_PII; REDACT_RECORD; VERIFY_RECORD_REDACTED` — PASS.
- **private support attachment** — expected `REPORT_REMAINING_RECORD; DELETE_RECORD; VERIFY_RECORD_ABSENT` — PASS.
- **active legal hold** — expected `VERIFY_RECORD_PRESENT` — PASS.

## Per-case differences

- `case_04`: missing `VERIFICATION|account_service|account_004|VERIFY_RECORD_ABSENT|ABSENT|evidence_54`; extra `none`.
- `case_09`: missing `VERIFICATION|security_service|audit_record_4902|VERIFY_RECORD_PRESENT|PRESENT|`; extra `VERIFICATION|analytics_platform|analytics_5718|VERIFY_RECORD_ANONYMIZED|ANONYMIZED|`.
- `case_12`: missing `FINDING|analytics_platform|analytics_9914|REPORT_REMAINING_RECORD|PRESENT|evidence_01; REMEDIATION|analytics_platform|analytics_9914|DELETE_RECORD|ABSENT|; VERIFICATION|analytics_platform|analytics_9914|VERIFY_RECORD_ABSENT|ABSENT|`; extra `FINDING|analytics_platform|analytics_9914|REPORT_EXPOSED_PII|PRESENT|evidence_01; FINDING|search_service|search_4801|REPORT_REMAINING_RECORD|PRESENT|evidence_01; REMEDIATION|analytics_platform|analytics_9914|ANONYMIZE_RECORD|ANONYMIZED|; REMEDIATION|search_service|search_4801|DELETE_RECORD|ABSENT|; VERIFICATION|analytics_platform|analytics_9914|VERIFY_RECORD_ANONYMIZED|ANONYMIZED|; VERIFICATION|search_service|search_4801|VERIFY_RECORD_ABSENT|ABSENT|`.
- `case_17`: missing `none`; extra `FINDING|search_service|search_4882|REPORT_REMAINING_RECORD|PRESENT|evidence_01; REMEDIATION|search_service|search_4882|DELETE_RECORD|ABSENT|; VERIFICATION|search_service|search_4882|VERIFY_RECORD_ABSENT|ABSENT|`.
- `case_18`: missing `VERIFICATION|security_service|audit_record_6645|VERIFY_RECORD_PRESENT|PRESENT|`; extra `none`.
- `case_20`: missing `VERIFICATION|security_service|audit_record_5569|VERIFY_RECORD_PRESENT|PRESENT|`; extra `none`.
- `case_23`: missing `VERIFICATION|account_service|account_410|VERIFY_RECORD_ABSENT|ABSENT|; VERIFICATION|security_service|audit_record_4128|VERIFY_RECORD_PRESENT|PRESENT|`; extra `VERIFICATION|account_service|account_7015|VERIFY_RECORD_ABSENT|ABSENT|`.
- `case_24`: missing `VERIFICATION|security_service|audit_record_7095|VERIFY_RECORD_PRESENT|PRESENT|`; extra `VERIFICATION|analytics_platform|analytics_1895|VERIFY_RECORD_ANONYMIZED|ANONYMIZED|`.
- `case_25`: missing `VERIFICATION|analytics_platform|analytics_1895|VERIFY_RECORD_ANONYMIZED|ANONYMIZED|evidence_92`; extra `none`.
- `case_26`: missing `VERIFICATION|analytics_platform|analytics_4566|VERIFY_RECORD_ANONYMIZED|ANONYMIZED|evidence_92`; extra `none`.
- `case_28`: missing `VERIFICATION|account_service|account_5482|VERIFY_RECORD_ABSENT|ABSENT|evidence_92`; extra `VERIFICATION|account_service|account_7012|VERIFY_RECORD_ABSENT|ABSENT|evidence_07`.
- `case_29`: missing `VERIFICATION|account_service|account_7012|VERIFY_RECORD_ABSENT|ABSENT|; VERIFICATION|security_service|audit_record_3954|VERIFY_RECORD_PRESENT|PRESENT|`; extra `VERIFICATION|account_service|account_5482|VERIFY_RECORD_ABSENT|ABSENT|`.
- `case_30`: missing `VERIFICATION|security_service|audit_record_1707|VERIFY_RECORD_PRESENT|PRESENT|`; extra `none`.
- `case_31`: missing `VERIFICATION|account_service|account_4857|VERIFY_RECORD_ABSENT|ABSENT|evidence_51`; extra `VERIFICATION|account_service|account_4857|VERIFY_RECORD_ABSENT|ABSENT|evidence_07`.

## First differing steps

| Case | First step | Prediction | Sample answer | Cause |
|---|---:|---|---|---|
| `case_04` | 1 | VERIFICATION VERIFY_RECORD_ANONYMIZED analytics_platform/analytics_901 [evidence_56] | VERIFICATION VERIFY_RECORD_ABSENT account_service/account_004 [evidence_54] | missing step |
| `case_09` | 4 | VERIFICATION VERIFY_RECORD_ANONYMIZED analytics_platform/analytics_5718 [] | VERIFICATION VERIFY_RECORD_PRESENT security_service/audit_record_4902 [] | missing step, extra step |
| `case_12` | 1 | FINDING REPORT_REMAINING_RECORD search_service/search_4801 [evidence_01] | FINDING REPORT_REMAINING_RECORD analytics_platform/analytics_9914 [evidence_01] | wrong operation, missing step, extra step |
| `case_17` | 1 | FINDING REPORT_REMAINING_RECORD search_service/search_4882 [evidence_01] | FINDING REPORT_RESTORE_RISK backup_service/backup_3245 [evidence_01] | extra step |
| `case_18` | 11 | VERIFICATION VERIFY_RECORD_REDACTED support_platform/support_5569 [] | VERIFICATION VERIFY_RECORD_PRESENT security_service/audit_record_6645 [] | missing step |
| `case_20` | 7 | VERIFICATION VERIFY_DATA_FLOW_DISABLED integration_service/data_flow_1770 [] | VERIFICATION VERIFY_RECORD_PRESENT security_service/audit_record_5569 [] | missing step |
| `case_23` | 5 | VERIFICATION VERIFY_RECORD_ABSENT account_service/account_7015 [] | VERIFICATION VERIFY_RECORD_ABSENT account_service/account_410 [] | missing step, extra step |
| `case_24` | 7 | VERIFICATION VERIFY_RECORD_ANONYMIZED analytics_platform/analytics_1895 [] | VERIFICATION VERIFY_RECORD_PRESENT security_service/audit_record_7095 [] | missing step, extra step |
| `case_25` | 3 | end of sequence | VERIFICATION VERIFY_RECORD_ANONYMIZED analytics_platform/analytics_1895 [evidence_92] | missing step |
| `case_26` | 4 | VERIFICATION VERIFY_DATA_FLOW_DISABLED integration_service/data_flow_6244 [evidence_92] | VERIFICATION VERIFY_RECORD_ANONYMIZED analytics_platform/analytics_4566 [evidence_92] | missing step |
| `case_28` | 1 | VERIFICATION VERIFY_RECORD_ABSENT account_service/account_7012 [evidence_07] | VERIFICATION VERIFY_RECORD_ABSENT account_service/account_5482 [evidence_92] | missing step, extra step |
| `case_29` | 9 | VERIFICATION VERIFY_RECORD_ABSENT account_service/account_5482 [] | VERIFICATION VERIFY_RECORD_ABSENT account_service/account_7012 [] | missing step, extra step |
| `case_30` | 11 | VERIFICATION VERIFY_RECORD_REDACTED support_platform/support_6477 [] | VERIFICATION VERIFY_RECORD_PRESENT security_service/audit_record_1707 [] | missing step |
| `case_31` | 1 | VERIFICATION VERIFY_RECORD_ABSENT account_service/account_4857 [evidence_07] | VERIFICATION VERIFY_RECORD_ABSENT account_service/account_4857 [evidence_51] | missing step, extra step |

## Resource linker calibration

Direct evidence links: **76/79 candidates correct**, precision **96.20%**, recall **68.47%** against 111 gold resource links. The target recall threshold was not met.

| Resource type | Precision | Recall | True / gold | Candidates |
|---|---:|---:|---:|---:|
| account | 100.00% | 34.38% | 11/32 | 11 |
| analytics | 100.00% | 46.15% | 6/13 | 6 |
| audit | 100.00% | 70.83% | 17/24 | 17 |
| backup | 100.00% | 100.00% | 6/6 | 6 |
| export | 100.00% | 100.00% | 2/2 | 2 |
| flow | 100.00% | 100.00% | 9/9 | 9 |
| search | 100.00% | 100.00% | 12/12 | 12 |
| support | 100.00% | 100.00% | 11/11 | 11 |
| tombstone | 100.00% | 100.00% | 2/2 | 2 |

| Signal removed | Precision | Recall | Remaining candidates |
|---|---:|---:|---:|
| identity_link_activity | 98.70% | 68.47% | 77 |
| same_record_identity_resource | 88.00% | 19.82% | 25 |
| subject_reference_user_id | 97.73% | 38.74% | 44 |
| trace_group_identity_resource | 96.43% | 48.65% | 56 |

The table above is a one-signal-at-a-time removal analysis. The cumulative out-of-fold S1 → +S2 → +S3 → +S4 → +global-matching ablation is reported below.

- Full run: resources considered 1814; assigned 1793; unresolved 395; ambiguity rate 0.217751.
- Sample-only threshold calibration (frozen to maximize link F1, ties prefer precision): selected `0.98`.

| Minimum direct-link score | Precision | Recall | F1 |
|---:|---:|---:|---:|
| 0.90 | 96.20% | 68.47% | 80.00% |
| 0.95 | 96.20% | 68.47% | 80.00% |
| 0.97 | 96.20% | 68.47% | 80.00% |
| 0.98 | 96.20% | 68.47% | 80.00% |
| 0.99 | 95.65% | 19.82% | 32.84% |

### Leave-one-out evaluation

Offsets are fitted on 31 public sample cases per held-out case. The candidate universe contains the 32 public cases plus all 518 evaluation requests; no held-out sample labels are used to fit that fold.

| Resource type | OOF precision | OOF recall | True / gold | Candidates |
|---|---:|---:|---:|---:|
| account | 83.87% | 81.25% | 26/32 | 31 |
| analytics | 81.82% | 69.23% | 9/13 | 11 |
| audit | 100.00% | 70.83% | 17/24 | 17 |
| backup | 100.00% | 100.00% | 6/6 | 6 |
| data | 100.00% | 100.00% | 9/9 | 9 |
| export | 100.00% | 100.00% | 2/2 | 2 |
| object | 0.00% | 0.00% | 0/0 | 1 |
| search | 85.71% | 100.00% | 12/12 | 14 |
| support | 100.00% | 100.00% | 11/11 | 11 |
| tombstone | 66.67% | 100.00% | 2/2 | 3 |

The ≥90% OOF precision-and-recall target was **not met** for account or analytics links. The account OOF result was 26/32 true, precision 83.87%, recall 81.25%. The 518-request run has 395 ambiguous resource assignments in the global candidate graph.

#### Cumulative out-of-fold ablation

| Signal stage | Micro precision | Micro recall | Micro F1 | Account P/R | Analytics P/R | TP / gold |
|---|---:|---:|---:|---:|---:|---:|
| S1 | 23.26% | 27.03% | 25.00% | 35.48%/34.38% | 20.00%/30.77% | 30/111 |
| S1+S2 | 28.68% | 33.33% | 30.83% | 61.29%/59.38% | 20.00%/30.77% | 37/111 |
| S1+S2+S3 | 37.21% | 43.24% | 40.00% | 74.19%/71.88% | 30.00%/46.15% | 48/111 |
| S1+S2+S3+S4 | 60.90% | 85.59% | 71.16% | 80.65%/78.12% | 52.38%/84.62% | 95/111 |
| S1+S2+S3+S4+global | 89.52% | 84.68% | 87.04% | 83.87%/81.25% | 81.82%/69.23% | 94/111 |

Each held-out fold refits its timing and status/result distributions on the other 31 public sample cases. The production `offsets.json` is fitted on all public sample labels, but it is not read for OOF scoring; held-out labels do not contribute to their fold's offsets or status/result counts.

Low-confidence identity-link fallbacks used to prevent empty authorized plans in the full output: `case_33`, `case_61`. These plans cite the ambiguous catalog link as evidence and should be reviewed as lower confidence than resource snapshots.

## Leakage and source scan

- Grep-style scan of 9 production Python modules found **0 literal case/resource IDs** (case-number and resource-number patterns). Synthetic unit-test identifiers and evaluation artifacts were excluded; no sample-specific ID shortcut is present in the prediction path.
- `offsets.json` contains aggregate operation timing distributions and status/result frequencies learned from participant-facing public samples; it contains **no case/resource IDs**. This is the intended S1/S2 calibration artifact, not a per-case answer table. Reported OOF scores refit it from 31 training cases per fold and do not use the full-fit production file.
- Per-case OOF predictions are diagnostic-only and are excluded from `code.zip`; the aggregate linker metrics and miss audit remain for reproducibility.
- Detailed held-out account/analytics misses, candidate alternatives, cutoff-valid offsets/results, status/result matches, and competing owners are in `../linking/heldout_link_misses.md`.

- Row-level resource provenance and the 32-case pattern audit are in `../linking/PATTERNS.md`; the full run's unassigned owner/resource candidates are in `../linking/low_confidence.md`.
- The audit of the 11 previously disputed resources, including cutoff-valid activity rows, offsets, results, and same-type competitors, is in `../linking/disputed_11_audit.md`. A missing direct identifier match does not establish that a link is unrecoverable.

## Root-cause changes and remaining failures

| Root cause | Previous measured result | Current measured result | Notes |
|---|---:|---:|---|
| v1 baseline | User-reported 25/32 status, 44% step F1, 3/32 exact | 32/32 status, 91.67% step F1, 18/32 exact | User-reported starting point; current public sample metrics are reproduced above. |
| v2 identity and evidence | Prior local run 32/32 status, 83.42% F1 | 32/32 status, 91.67% F1 | Alias and evidence graph work is measured on the same 32 public cases. |
| v3 policy and cutoff | Prior exact sequence 4/32 | 18/32 exact | Time cutoffs, policy actions, and verification generation are covered by sample metrics and tests. |
| v4 time-anchored linking | Prior linker OOF not available | Account OOF P/R 83.87%/81.25%; sample F1 91.67% | S1 offset, S2 result/status, burst scoring, and global assignment added; ≥90% per-type OOF goal remains unmet. |
| RC2 category/policy | Not isolated | See operation/category F1 and case diffs | Attachment detection and evidence-based support redaction are tested. |
| RC3 retained records | Not isolated | See case diffs and custom hold/tombstone tests | The grader sample contains retained-resource references without an independently linked resource in some cases. |
| RC4 document extraction | OCR cache provenance unclear | Tesseract-backed clean-cache extraction completed | OCR cache sidecars record source SHA-256, extracted-text SHA-256, and extractor/version. |
| RC5 ordering | 4/32 exact sequences | 18/32 exact sequences | Deterministic orderer and unit tests added. |
| RC6 empty plans | Seven full-run gaps in prior run | 0 authorized full-run gaps | No resource IDs or evidence are invented to fill them. |
| RC7 full-run gold | Evaluator printed 0/0 | Explicit no-gold mode | Full dataset is checked for invariants, evidence cutoffs, distribution, and BOM only. |

## LLM ablation

| Mode | Status accuracy | Step F1 | Calls / tokens | Cost | Runtime |
|---|---:|---:|---:|---:|---:|
| Deterministic `--no-llm` | 32/32 | 91.67% | 0 / 0 | $0.00 | Offline run. |
| Groq LLM path | 32/32 | 91.67% | 78 / 72,790 in + 27,525 out | $0.040752 | Sample run elapsed time not separately captured. |

The deterministic baseline and Groq sample have identical status accuracy, step F1, and exact-sequence accuracy; live results therefore pass the non-regression gate. Sample calls include 11-image OCR comparison, cached ambiguous-link investigation, and low-confidence intent/category handling. The full run reused these cached responses where inputs matched.

- RC1: Removed synthetic account-ID inference. Resources now require evidence-graph co-mentions, direct identifiers, or cutoff-valid identity-link activity. This intentionally exposes sample answers whose resource IDs cannot be independently linked from participant evidence; those outputs are not guessed.
- RC2: Added attachment metadata/text detection and condition-aware policy actions for shared support conversations, logs, legal holds, analytics, and backups. Remaining mismatches are listed above.
- RC3: Retention and tombstone handling are tested; complete coverage still depends on a linked record and policy evidence.
- RC4: PDF extraction is cached; resource-local OCR/PDF text and image preprocessing are implemented. A clean-cache run was performed with the native Tesseract executable at `C:\Program Files\Tesseract-OCR\tesseract.exe`; 11 PNGs were processed. Cache sidecars document content hashes and extractor provenance.
- RC5: Ordering is a pure deterministic function with unit tests.
- RC6: The full output has 0 empty authorized plans. Low-confidence identity-link fallbacks are listed above and are visibly distinguishable by activity citations.
- RC7: Full-run evaluation reports no gold available and runs structural, citation-cutoff, distribution, and BOM checks only.
- LLM/VLM: xAI and Groq use the OpenAI Python SDK. Groq JSON Schema rejections fall back to JSON mode with local validation and repair; its 27B Qwen model accepted images. The intent classifier disagreed with the deterministic gate for several requests; the generic guard retained deterministic intent, preserving sample accuracy.
- Authorized full-run requests without a plan: 0 (none). The fallback cases are disclosed above and in the linker ambiguity artifacts.

## Failing-test plan

See `rc_test_plan.md`; implementation checks run with `python -m unittest discover -s code/tests -v`.
