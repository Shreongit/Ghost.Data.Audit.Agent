# Root-cause tests (baseline failures)

These checks are registered before corrective edits. The public sample set is participant-facing calibration data; no organizer data is used.

| Root cause | Baseline failure to reproduce | Corrective acceptance check |
|---|---|---|
| RC1 resource inference | Trace currently manufactures `account_<user number>` from `user_<number>` even without a link. | No resource can enter the dossier without a visible evidence/activity link; unrelated snapshots cannot prove absence. |
| RC2 category/policy | Support attachments are guessed as messages from a `support_` prefix; policy actions depend on row metadata. | Attachment metadata/collection beats generic support prefix; shared messages remain a different category. |
| RC3 retained data | Retention evidence is inconsistently included and tombstone verification is too broad. | Retained records and tombstones require actual evidence, valid retention/hold state, and policy-supported linkage. |
| RC4 extraction | Native Tesseract executable is absent; image evidence is skipped. | Cached PDF/OCR text is deterministic; OCR path preprocesses images and gives actionable missing-binary diagnostics. |
| RC5 order | Order logic is embedded in planner; no isolated unit test. | Pure orderer enforces phase, table operation order, system/resource tie breaks, deduplication, and step numbering. |
| RC6 empty plans | Seven full-run authorized cases have no evidence-backed plan. | Investigate alias expansion and graph paths; never invent a resource or evidence citation to make a plan nonempty. |
| RC7 evaluation | Full-run evaluator prints `0/0` against sample gold and only partial invariants. | State explicitly that full-run gold is unavailable; run structural, evidence-cutoff, distribution, and perturbation checks. |

## Baseline recorded

Sample run: 32/32 status accuracy, 83.42% step F1, 11/32 exact sequences, and zero sample schema invariant errors. Full run: 518 rows, with seven empty authorized plans. No LLM credentials are set in the environment, and `tesseract.exe` is not on PATH or at the configured default path.
