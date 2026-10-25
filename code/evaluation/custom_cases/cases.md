# Participant-authored synthetic robustness cases

These cases contain no sample-output rows or organizer truth. Automated outcomes are reported from `custom_cases()` in the evaluator and the corresponding `code/tests/test_core.py` checks.

| Case | Input scenario | Expected output/steps | Automated check |
|---|---|---|---|
| MC-01 | Spanish: `Solo quiero una copia de mis datos.` | `NOT_APPLICABLE`, `steps_json=[]` | Intent gate test |
| MC-02 | Request uses `old@example.test`; audit log links it to the current address; a later address change is after `audit_at`. | Resolve `old@example.test`, its SHA-256 alias, and the valid user ID; exclude the later email. | Historical alias cutoff test |
| MC-03 | A data flow is disabled, then a later cutoff-valid sync re-enables it. | `REPORT_ACTIVE_DATA_FLOW`, `DISABLE_DATA_FLOW`, `VERIFY_DATA_FLOW_DISABLED`, in that order. | Latest-state and flow tests |
| MC-04 | A user-linked record has an observation or file capture after `audit_at`. | Do not include it in the dossier or output steps. | Evidence time-filter test |
| MC-05 | A linked tombstone keeps `user_id` but still has `email=person@example.test`. | `REPORT_EXPOSED_PII`, `REDACT_RECORD`, `VERIFY_RECORD_REDACTED`; preserve `user_id`. | Tombstone policy test |
| MC-06 | A support record has attachment properties and a customer-uploaded identity-document filename. | `REPORT_REMAINING_RECORD`, `DELETE_RECORD`, `VERIFY_RECORD_ABSENT`. | Category and policy tests |
| MC-07 | A record is classified as `LEGAL_HOLD_RECORD` with `hold_status=active`. | Preserve the record and emit `VERIFY_RECORD_PRESENT` when that record is linked and otherwise compliant. | Legal-hold policy test |
| MC-08 | The same evidence facts are shuffled, the request email is uppercased, and post-cutoff evidence is added. | Identical plan across all three perturbations. | End-to-end deterministic plan test |

Expected future verification operations are descriptions of checks; they are not represented as completed state unless participant evidence proves that state.
