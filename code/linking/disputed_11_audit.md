# Audit of the 11 prior “unrecoverable” public-sample links

This audit uses only sample requests, sample answers for selecting the disputed rows, system activity, and leave-one-case-out public-sample offsets. The disputed case is excluded when fitting its timing model. Candidate competitors are all same-resource-type activity candidates retained by the calibrated timing likelihood for that request. “Not in model” means no cutoff-valid, type-compatible activity edge met the likelihood floor; it does not prove the resource itself is absent.

## case_02 — `account_002`

Reported status/result context: `PARTIALLY_COMPLETE`; `reported_at=2026-08-22T07:25:00Z`; `audit_at=2026-09-04T15:00:00Z`.

| activity_id | event_time | Δ reported_at − event_time (h) | event_type | target_system | reported_result |
|---|---|---:|---|---|---|
| `activity_3376` | `2026-08-22T07:30:03Z` | -0.084 | `DELETE_RECORD` | `account_service` | `PARTIAL` |

Candidate activity competitors for this request and resource type (0):
None meet the cutoff and calibrated offset-likelihood floor.

Competing request owners for this exact resource (0):
No request in the 550-request candidate universe receives a calibrated activity candidate for this exact resource.

Assessment: activity names the resource, but its result/time is outside the learned candidate envelope. The activity row cannot establish subject ownership by itself.

## case_04 — `account_004`

Reported status/result context: `COMPLETE`; `reported_at=2026-08-27T08:54:00Z`; `audit_at=2026-09-07T10:20:00Z`.

No cutoff-valid `system_activity.csv` row names this resource ID.

Candidate activity competitors for this request and resource type (0):
None meet the cutoff and calibrated offset-likelihood floor.

Competing request owners for this exact resource (0):
No request in the 550-request candidate universe receives a calibrated activity candidate for this exact resource.

Assessment: this resource has no activity row in the participant-facing stream. The earlier blanket “unrecoverable” claim should be scoped to this specific evidence gap; timing cannot link a resource that never appears in the stream.

## case_08 — `account_008`

Reported status/result context: `PARTIALLY_COMPLETE`; `reported_at=2026-08-31T13:44:00Z`; `audit_at=2026-09-14T16:10:00Z`.

| activity_id | event_time | Δ reported_at − event_time (h) | event_type | target_system | reported_result |
|---|---|---:|---|---|---|
| `activity_3554` | `2026-08-31T13:48:58Z` | -0.083 | `DELETE_RECORD` | `account_service` | `SUCCESS` |

Candidate activity competitors for this request and resource type (1):

| candidate resource | score | signals | provenance |
|---|---:|---|---|
| `account_008` | 0.7521 | `reported_at_offset_likelihood, reported_status_result_likelihood` | `activity_3554; offset:account_service|DELETE_RECORD modes=2 median=0.873611h iqr=0.061111..1.005278h; delta_hours=-0.082778; burst_strength=0.0000; reported_result=SUCCESS` |

Competing request owners for this exact resource (1):

| candidate case | score | signals | provenance |
|---|---:|---|---|
| `case_08` | 0.7521 | `reported_at_offset_likelihood, reported_status_result_likelihood` | `activity_3554; offset:account_service|DELETE_RECORD modes=2 median=0.873611h iqr=0.061111..1.005278h; delta_hours=-0.082778; burst_strength=0.0000; reported_result=SUCCESS` |

Assessment: activity exists and the highest scored owner in the 550-request candidate universe is `case_08`. Margin over its runner-up is 0.7521. This is a scored ownership signal, not direct identity evidence.

## case_09 — `audit_record_4902`

Reported status/result context: `NOT_STARTED`; `reported_at=2026-09-07T09:00:00Z`; `audit_at=2026-09-16T09:00:00Z`.

No cutoff-valid `system_activity.csv` row names this resource ID.

Candidate activity competitors for this request and resource type (0):
None meet the cutoff and calibrated offset-likelihood floor.

Competing request owners for this exact resource (0):
No request in the 550-request candidate universe receives a calibrated activity candidate for this exact resource.

Assessment: this resource has no activity row in the participant-facing stream. The earlier blanket “unrecoverable” claim should be scoped to this specific evidence gap; timing cannot link a resource that never appears in the stream.

## case_10 — `account_010`

Reported status/result context: `COMPLETE`; `reported_at=2026-09-02T10:08:00Z`; `audit_at=2026-09-18T12:25:00Z`.

| activity_id | event_time | Δ reported_at − event_time (h) | event_type | target_system | reported_result |
|---|---|---:|---|---|---|
| `activity_3595` | `2026-09-02T10:08:37Z` | -0.010 | `DELETE_RECORD` | `account_service` | `SUCCESS` |

Candidate activity competitors for this request and resource type (1):

| candidate resource | score | signals | provenance |
|---|---:|---|---|
| `account_010` | 0.9080 | `reported_at_offset_likelihood, reported_status_result_likelihood` | `activity_3595; offset:account_service|DELETE_RECORD modes=2 median=0.873611h iqr=0.061111..1.005278h; delta_hours=-0.010278; burst_strength=0.0000; reported_result=SUCCESS` |

Competing request owners for this exact resource (1):

| candidate case | score | signals | provenance |
|---|---:|---|---|
| `case_10` | 0.9080 | `reported_at_offset_likelihood, reported_status_result_likelihood` | `activity_3595; offset:account_service|DELETE_RECORD modes=2 median=0.873611h iqr=0.061111..1.005278h; delta_hours=-0.010278; burst_strength=0.0000; reported_result=SUCCESS` |

Assessment: activity exists and the highest scored owner in the 550-request candidate universe is `case_10`. Margin over its runner-up is 0.9080. This is a scored ownership signal, not direct identity evidence.

## case_18 — `audit_record_6645`

Reported status/result context: `COMPLETE`; `reported_at=2026-09-09T11:00:00Z`; `audit_at=2026-09-26T11:00:00Z`.

No cutoff-valid `system_activity.csv` row names this resource ID.

Candidate activity competitors for this request and resource type (0):
None meet the cutoff and calibrated offset-likelihood floor.

Competing request owners for this exact resource (0):
No request in the 550-request candidate universe receives a calibrated activity candidate for this exact resource.

Assessment: this resource has no activity row in the participant-facing stream. The earlier blanket “unrecoverable” claim should be scoped to this specific evidence gap; timing cannot link a resource that never appears in the stream.

## case_20 — `audit_record_5569`

Reported status/result context: `NOT_STARTED`; `reported_at=2026-09-09T11:00:00Z`; `audit_at=2026-09-26T11:00:00Z`.

No cutoff-valid `system_activity.csv` row names this resource ID.

Candidate activity competitors for this request and resource type (0):
None meet the cutoff and calibrated offset-likelihood floor.

Competing request owners for this exact resource (0):
No request in the 550-request candidate universe receives a calibrated activity candidate for this exact resource.

Assessment: this resource has no activity row in the participant-facing stream. The earlier blanket “unrecoverable” claim should be scoped to this specific evidence gap; timing cannot link a resource that never appears in the stream.

## case_23 — `audit_record_4128`

Reported status/result context: `NOT_STARTED`; `reported_at=2026-09-05T12:00:00Z`; `audit_at=2026-09-15T12:00:00Z`.

No cutoff-valid `system_activity.csv` row names this resource ID.

Candidate activity competitors for this request and resource type (0):
None meet the cutoff and calibrated offset-likelihood floor.

Competing request owners for this exact resource (0):
No request in the 550-request candidate universe receives a calibrated activity candidate for this exact resource.

Assessment: this resource has no activity row in the participant-facing stream. The earlier blanket “unrecoverable” claim should be scoped to this specific evidence gap; timing cannot link a resource that never appears in the stream.

## case_24 — `audit_record_7095`

Reported status/result context: `COMPLETE`; `reported_at=2026-09-02T12:00:00Z`; `audit_at=2026-09-15T12:00:00Z`.

No cutoff-valid `system_activity.csv` row names this resource ID.

Candidate activity competitors for this request and resource type (0):
None meet the cutoff and calibrated offset-likelihood floor.

Competing request owners for this exact resource (0):
No request in the 550-request candidate universe receives a calibrated activity candidate for this exact resource.

Assessment: this resource has no activity row in the participant-facing stream. The earlier blanket “unrecoverable” claim should be scoped to this specific evidence gap; timing cannot link a resource that never appears in the stream.

## case_29 — `audit_record_3954`

Reported status/result context: `NOT_STARTED`; `reported_at=2026-08-30T12:00:00Z`; `audit_at=2026-09-15T12:00:00Z`.

No cutoff-valid `system_activity.csv` row names this resource ID.

Candidate activity competitors for this request and resource type (0):
None meet the cutoff and calibrated offset-likelihood floor.

Competing request owners for this exact resource (0):
No request in the 550-request candidate universe receives a calibrated activity candidate for this exact resource.

Assessment: this resource has no activity row in the participant-facing stream. The earlier blanket “unrecoverable” claim should be scoped to this specific evidence gap; timing cannot link a resource that never appears in the stream.

## case_30 — `audit_record_1707`

Reported status/result context: `COMPLETE`; `reported_at=2026-08-27T12:00:00Z`; `audit_at=2026-09-15T12:00:00Z`.

No cutoff-valid `system_activity.csv` row names this resource ID.

Candidate activity competitors for this request and resource type (0):
None meet the cutoff and calibrated offset-likelihood floor.

Competing request owners for this exact resource (0):
No request in the 550-request candidate universe receives a calibrated activity candidate for this exact resource.

Assessment: this resource has no activity row in the participant-facing stream. The earlier blanket “unrecoverable” claim should be scoped to this specific evidence gap; timing cannot link a resource that never appears in the stream.

