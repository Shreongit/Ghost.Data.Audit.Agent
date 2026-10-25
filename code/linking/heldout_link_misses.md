# Held-out account and analytics link misses

Leave-one-case-out; every model is fitted on the other 31 public sample cases. The request candidate universe includes all 518 evaluation requests plus the public sample. Candidate rows list timing, result/status compatibility, provenance, and other candidate owners for the same resource. These are diagnostic leads; absence from the candidate set is not evidence of deletion.

## case_04 — `account_004` (account)

Reported status: `COMPLETE`; reported_at: `2026-08-27T08:54:00Z`; audit_at: `2026-09-07T10:20:00Z`.

No cutoff-valid activity row names this gold resource.

The gold resource has no candidate edge in this held-out fold.

Same-type candidates for the held-out request:

No same-type candidate edge was emitted for the held-out case.

## case_04 — `analytics_901` (analytics)

Reported status: `COMPLETE`; reported_at: `2026-08-27T08:54:00Z`; audit_at: `2026-09-07T10:20:00Z`.

Cutoff-valid activity rows naming the gold resource:
- `activity_3463` ANONYMIZE_RECORD at 2026-08-27T08:47:41Z; Δ=+0.105278 h; result=`SUCCESS`; status/result match=`True`; offset likelihood=0.462611 (offset:analytics_platform|ANONYMIZE_RECORD modes=3 median=0.477778h iqr=0.474583..0.480347h)

Candidates for the gold resource and competing request owners:
- `case_83` score=0.864852; signals=reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor; provenance=activity_3463, offset:analytics_platform|ANONYMIZE_RECORD modes=3 median=0.468611h iqr=-1.457083..0.477778h, delta_hours=-1.794722, burst_strength=0.5353, reported_result=SUCCESS
- `case_84` score=0.899447; signals=reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor; provenance=activity_3463, offset:analytics_platform|ANONYMIZE_RECORD modes=3 median=0.468611h iqr=-1.457083..0.477778h, delta_hours=-1.794722, burst_strength=0.6873, reported_result=SUCCESS
- `case_85` score=0.899572; signals=reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor; provenance=activity_3463, offset:analytics_platform|ANONYMIZE_RECORD modes=3 median=0.468611h iqr=-1.457083..0.477778h, delta_hours=-1.794722, burst_strength=0.8825, reported_result=SUCCESS
- `case_04` score=0.805249; signals=reported_at_offset_likelihood, reported_status_result_likelihood; provenance=activity_3463, offset:analytics_platform|ANONYMIZE_RECORD modes=3 median=0.477778h iqr=0.474583..0.480347h, delta_hours=0.105278, burst_strength=0.0000, reported_result=SUCCESS

Same-type candidates for the held-out request:

| Candidate | Score | Signals | Temporal offset/result/status | Provenance | Competing cases |
|---|---:|---|---|---|---|
| `analytics_901` | 0.805249 | reported_at_offset_likelihood, reported_status_result_likelihood | `activity_3463` ANONYMIZE_RECORD at 2026-08-27T08:47:41Z; Δ=+0.105278 h; result=`SUCCESS`; status/result match=`True`; offset likelihood=0.462611 (offset:analytics_platform|ANONYMIZE_RECORD modes=3 median=0.477778h iqr=0.474583..0.480347h) | activity_3463, offset:analytics_platform|ANONYMIZE_RECORD modes=3 median=0.477778h iqr=0.474583..0.480347h, delta_hours=0.105278, burst_strength=0.0000, reported_result=SUCCESS | case_85 (0.8996), case_84 (0.8994), case_83 (0.8649) |

## case_18 — `account_5521` (account)

Reported status: `COMPLETE`; reported_at: `2026-09-09T11:00:00Z`; audit_at: `2026-09-26T11:00:00Z`.

Cutoff-valid activity rows naming the gold resource:
- `activity_3732` DELETE_RECORD at 2026-09-09T09:52:26Z; Δ=+1.126111 h; result=`SUCCESS`; status/result match=`True`; offset likelihood=0.792281 (offset:account_service|DELETE_RECORD modes=2 median=0.866944h iqr=0.0225..0.968611h)

Candidates for the gold resource and competing request owners:
- `case_51` score=0.967269; signals=reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor; provenance=activity_3732, offset:account_service|DELETE_RECORD modes=2 median=0.866944h iqr=0.0225..0.968611h, delta_hours=1.126111, burst_strength=0.8825, reported_result=SUCCESS
- `case_18` score=0.879019; signals=reported_at_offset_likelihood, reported_status_result_likelihood; provenance=activity_3732, offset:account_service|DELETE_RECORD modes=2 median=0.866944h iqr=0.0225..0.968611h, delta_hours=1.126111, burst_strength=0.0000, reported_result=SUCCESS
- `case_20` score=0.828287; signals=reported_at_offset_likelihood, reported_status_result_likelihood; provenance=activity_3732, offset:account_service|DELETE_RECORD modes=2 median=0.866944h iqr=0.0225..0.968611h, delta_hours=1.126111, burst_strength=0.0000, reported_result=SUCCESS

Same-type candidates for the held-out request:

| Candidate | Score | Signals | Temporal offset/result/status | Provenance | Competing cases |
|---|---:|---|---|---|---|
| `account_5193` | 0.970000 | reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor | `activity_3740` DELETE_RECORD at 2026-09-09T11:02:59Z; Δ=-0.049722 h; result=`SUCCESS`; status/result match=`True`; offset likelihood=0.991394 (offset:account_service|DELETE_RECORD modes=2 median=0.878889h iqr=0.753819..1.064306h) | activity_3740, offset:account_service|DELETE_RECORD modes=2 median=0.878889h iqr=0.753819..1.064306h, delta_hours=-0.049722, burst_strength=0.6065, reported_result=SUCCESS | case_37 (0.9976), case_36 (0.9700), case_37 (0.9700), case_51 (0.9700), case_13 (0.9572), case_20 (0.9216), case_535 (0.8689) |
| `account_5823` | 0.954883 | reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor | `activity_3742` DELETE_RECORD at 2026-09-09T11:13:14Z; Δ=-0.220556 h; result=`SUCCESS`; status/result match=`True`; offset likelihood=0.782197 (offset:account_service|DELETE_RECORD modes=2 median=0.878889h iqr=0.753819..1.064306h) | activity_3742, offset:account_service|DELETE_RECORD modes=2 median=0.878889h iqr=0.753819..1.064306h, delta_hours=-0.220556, burst_strength=0.7788, reported_result=SUCCESS | case_36 (0.9962), case_36 (0.9700), case_37 (0.9700), case_51 (0.9406), case_13 (0.9174), case_20 (0.8950), case_535 (0.8487) |
| `account_3610` | 0.920234 | reported_at_offset_likelihood, reported_status_result_likelihood | `activity_3733` DELETE_RECORD at 2026-09-09T10:03:41Z; Δ=+0.938611 h; result=`SUCCESS`; status/result match=`True`; offset likelihood=0.998354 (offset:account_service|DELETE_RECORD modes=2 median=0.866944h iqr=0.0225..0.968611h) | activity_3733, offset:account_service|DELETE_RECORD modes=2 median=0.866944h iqr=0.0225..0.968611h, delta_hours=0.938611, burst_strength=0.0000, reported_result=SUCCESS | case_51 (0.9976), case_51 (0.9700), case_20 (0.8695) |
| `account_9335` | 0.895823 | reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor | `activity_3739` DELETE_RECORD at 2026-09-09T10:53:28Z; Δ=+0.108889 h; result=`FAILED`; status/result match=`False`; offset likelihood=0.924139 (offset:account_service|DELETE_RECORD modes=2 median=0.878889h iqr=0.753819..1.064306h) | activity_3739, offset:account_service|DELETE_RECORD modes=2 median=0.878889h iqr=0.753819..1.064306h, delta_hours=0.108889, burst_strength=0.5353, reported_result=FAILED | case_13 (0.9960), case_13 (0.9700), case_51 (0.9409), case_20 (0.9399), case_37 (0.9284), case_36 (0.9089), case_535 (0.8905) |
| `account_5521` | 0.879019 | reported_at_offset_likelihood, reported_status_result_likelihood | `activity_3732` DELETE_RECORD at 2026-09-09T09:52:26Z; Δ=+1.126111 h; result=`SUCCESS`; status/result match=`True`; offset likelihood=0.792281 (offset:account_service|DELETE_RECORD modes=2 median=0.866944h iqr=0.0225..0.968611h) | activity_3732, offset:account_service|DELETE_RECORD modes=2 median=0.866944h iqr=0.0225..0.968611h, delta_hours=1.126111, burst_strength=0.0000, reported_result=SUCCESS | case_51 (0.9673), case_20 (0.8283) |
| `account_5037` | 0.827799 | reported_at_offset_likelihood, reported_status_result_likelihood | `activity_3734` DELETE_RECORD at 2026-09-09T10:14:55Z; Δ=+0.751389 h; result=`FAILED`; status/result match=`False`; offset likelihood=0.851670 (offset:account_service|DELETE_RECORD modes=2 median=0.878889h iqr=0.753819..1.064306h) | activity_3734, offset:account_service|DELETE_RECORD modes=2 median=0.878889h iqr=0.753819..1.064306h, delta_hours=0.751389, burst_strength=0.0000, reported_result=FAILED | case_51 (0.9160), case_20 (0.8781) |

## case_21 — `analytics_5335` (analytics)

Reported status: `COMPLETE`; reported_at: `2026-09-05T12:00:00Z`; audit_at: `2026-09-15T12:00:00Z`.

Cutoff-valid activity rows naming the gold resource:
- `activity_3665` ANONYMIZE_RECORD at 2026-09-05T11:31:34Z; Δ=+0.473889 h; result=`SUCCESS`; status/result match=`True`; offset likelihood=0.999861 (offset:analytics_platform|ANONYMIZE_RECORD modes=4 median=0.477778h iqr=0.470625..0.480347h)

Candidates for the gold resource and competing request owners:
- `case_536` score=0.869803; signals=reported_at_offset_likelihood, reported_status_result_likelihood; provenance=activity_3665, offset:analytics_platform|ANONYMIZE_RECORD modes=4 median=0.477778h iqr=0.470625..0.480347h, delta_hours=0.473889, burst_strength=0.0000, reported_result=SUCCESS
- `case_546` score=0.919137; signals=reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor; provenance=activity_3665, offset:analytics_platform|ANONYMIZE_RECORD modes=4 median=0.477778h iqr=0.470625..0.480347h, delta_hours=0.473889, burst_strength=0.6873, reported_result=SUCCESS
- `case_547` score=0.969173; signals=reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor; provenance=activity_3665, offset:analytics_platform|ANONYMIZE_RECORD modes=4 median=0.477778h iqr=0.470625..0.480347h, delta_hours=0.473889, burst_strength=0.9937, reported_result=SUCCESS
- `case_548` score=0.923333; signals=reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor; provenance=activity_3665, offset:analytics_platform|ANONYMIZE_RECORD modes=4 median=0.477778h iqr=0.470625..0.480347h, delta_hours=0.473889, burst_strength=0.5353, reported_result=SUCCESS
- `case_21` score=0.911439; signals=reported_at_offset_likelihood, reported_status_result_likelihood; provenance=activity_3665, offset:analytics_platform|ANONYMIZE_RECORD modes=4 median=0.477778h iqr=0.470625..0.480347h, delta_hours=0.473889, burst_strength=0.0000, reported_result=SUCCESS
- `case_23` score=0.947683; signals=reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor; provenance=activity_3665, offset:analytics_platform|ANONYMIZE_RECORD modes=4 median=0.477778h iqr=0.470625..0.480347h, delta_hours=0.473889, burst_strength=0.7788, reported_result=SUCCESS

Same-type candidates for the held-out request:

| Candidate | Score | Signals | Temporal offset/result/status | Provenance | Competing cases |
|---|---:|---|---|---|---|
| `analytics_5335` | 0.911439 | reported_at_offset_likelihood, reported_status_result_likelihood | `activity_3665` ANONYMIZE_RECORD at 2026-09-05T11:31:34Z; Δ=+0.473889 h; result=`SUCCESS`; status/result match=`True`; offset likelihood=0.999861 (offset:analytics_platform|ANONYMIZE_RECORD modes=4 median=0.477778h iqr=0.470625..0.480347h) | activity_3665, offset:analytics_platform|ANONYMIZE_RECORD modes=4 median=0.477778h iqr=0.470625..0.480347h, delta_hours=0.473889, burst_strength=0.0000, reported_result=SUCCESS | case_547 (0.9692), case_23 (0.9477), case_548 (0.9233), case_546 (0.9191), case_536 (0.8698) |

## case_23 — `account_410` (account)

Reported status: `NOT_STARTED`; reported_at: `2026-09-05T12:00:00Z`; audit_at: `2026-09-15T12:00:00Z`.

Cutoff-valid activity rows naming the gold resource:
- `activity_3662` DELETE_RECORD at 2026-09-05T11:10:55Z; Δ=+0.818056 h; result=`FAILED`; status/result match=`True`; offset likelihood=0.881679 (offset:account_service|DELETE_RECORD modes=2 median=0.897917h iqr=0.753819..1.076667h)

Candidates for the gold resource and competing request owners:
- `case_536` score=0.878223; signals=reported_at_offset_likelihood, reported_status_result_likelihood; provenance=activity_3662, offset:account_service|DELETE_RECORD modes=2 median=0.897917h iqr=0.753819..1.076667h, delta_hours=0.818056, burst_strength=0.0000, reported_result=FAILED
- `case_546` score=0.910532; signals=reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor; provenance=activity_3662, offset:account_service|DELETE_RECORD modes=2 median=0.897917h iqr=0.753819..1.076667h, delta_hours=0.818056, burst_strength=0.4724, reported_result=FAILED
- `case_547` score=0.956103; signals=reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor; provenance=activity_3662, offset:account_service|DELETE_RECORD modes=2 median=0.897917h iqr=0.753819..1.076667h, delta_hours=0.818056, burst_strength=0.7788, reported_result=FAILED
- `case_548` score=0.915013; signals=reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor; provenance=activity_3662, offset:account_service|DELETE_RECORD modes=2 median=0.897917h iqr=0.753819..1.076667h, delta_hours=0.818056, burst_strength=0.3679, reported_result=FAILED
- `case_21` score=0.840640; signals=reported_at_offset_likelihood, reported_status_result_likelihood; provenance=activity_3662, offset:account_service|DELETE_RECORD modes=2 median=0.897917h iqr=0.753819..1.076667h, delta_hours=0.818056, burst_strength=0.0000, reported_result=FAILED
- `case_23` score=0.931753; signals=reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor; provenance=activity_3662, offset:account_service|DELETE_RECORD modes=2 median=0.897917h iqr=0.753819..1.076667h, delta_hours=0.818056, burst_strength=0.5353, reported_result=FAILED

Same-type candidates for the held-out request:

| Candidate | Score | Signals | Temporal offset/result/status | Provenance | Competing cases |
|---|---:|---|---|---|---|
| `account_7015` | 0.943577 | reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor | `activity_3660` DELETE_RECORD at 2026-09-05T11:01:52Z; Δ=+0.968889 h; result=`FAILED`; status/result match=`True`; offset likelihood=1.000000 (offset:account_service|DELETE_RECORD modes=2 median=0.897917h iqr=0.753819..1.076667h) | activity_3660, offset:account_service|DELETE_RECORD modes=2 median=0.897917h iqr=0.753819..1.076667h, delta_hours=0.968889, burst_strength=0.4169, reported_result=FAILED | case_547 (0.9625), case_546 (0.9237), case_536 (0.9019), case_548 (0.9019), case_21 (0.8643) |
| `account_410` | 0.931753 | reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor | `activity_3662` DELETE_RECORD at 2026-09-05T11:10:55Z; Δ=+0.818056 h; result=`FAILED`; status/result match=`True`; offset likelihood=0.881679 (offset:account_service|DELETE_RECORD modes=2 median=0.897917h iqr=0.753819..1.076667h) | activity_3662, offset:account_service|DELETE_RECORD modes=2 median=0.897917h iqr=0.753819..1.076667h, delta_hours=0.818056, burst_strength=0.5353, reported_result=FAILED | case_547 (0.9561), case_548 (0.9150), case_546 (0.9105), case_536 (0.8782), case_21 (0.8406) |
| `account_9155` | 0.930054 | reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor | `activity_3663` DELETE_RECORD at 2026-09-05T11:12:36Z; Δ=+0.790000 h; result=`FAILED`; status/result match=`True`; offset likelihood=0.837585 (offset:account_service|DELETE_RECORD modes=2 median=0.897917h iqr=0.753819..1.076667h) | activity_3663, offset:account_service|DELETE_RECORD modes=2 median=0.897917h iqr=0.753819..1.076667h, delta_hours=0.790000, burst_strength=0.6065, reported_result=FAILED | case_547 (0.9577), case_548 (0.9111), case_546 (0.9080), case_536 (0.8694), case_21 (0.8318) |
| `account_6440` | 0.922712 | reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor | `activity_3661` DELETE_RECORD at 2026-09-05T11:01:53Z; Δ=+0.968611 h; result=`SUCCESS`; status/result match=`False`; offset likelihood=1.000000 (offset:account_service|DELETE_RECORD modes=2 median=0.897917h iqr=0.753819..1.076667h) | activity_3661, offset:account_service|DELETE_RECORD modes=2 median=0.897917h iqr=0.753819..1.076667h, delta_hours=0.968611, burst_strength=0.4724, reported_result=SUCCESS | case_547 (0.9442), case_21 (0.9139), case_546 (0.8921), case_536 (0.8755), case_548 (0.8755) |
| `account_8832` | 0.810111 | reported_at_offset_likelihood, reported_status_result_likelihood | `activity_3658` DELETE_RECORD at 2026-09-05T10:52:20Z; Δ=+1.127778 h; result=`PARTIAL`; status/result match=`False`; offset likelihood=0.937348 (offset:account_service|DELETE_RECORD modes=2 median=0.9125h iqr=0.414167..1.019861h) | activity_3658, offset:account_service|DELETE_RECORD modes=2 median=0.9125h iqr=0.414167..1.019861h, delta_hours=1.127778, burst_strength=0.0000, reported_result=PARTIAL | case_547 (0.8574), case_546 (0.8501), case_536 (0.8101), case_548 (0.8101), case_21 (0.8092) |
| `account_294` | 0.800871 | reported_at_offset_likelihood, reported_status_result_likelihood | `activity_3657` DELETE_RECORD at 2026-09-05T10:50:10Z; Δ=+1.163889 h; result=`PARTIAL`; status/result match=`False`; offset likelihood=0.891148 (offset:account_service|DELETE_RECORD modes=2 median=0.9125h iqr=0.414167..1.019861h) | activity_3657, offset:account_service|DELETE_RECORD modes=2 median=0.9125h iqr=0.414167..1.019861h, delta_hours=1.163889, burst_strength=0.0000, reported_result=PARTIAL | case_547 (0.8426), case_546 (0.8408), case_536 (0.8009), case_548 (0.8009), case_21 (0.8000) |

## case_24 — `account_5334` (account)

Reported status: `COMPLETE`; reported_at: `2026-09-02T12:00:00Z`; audit_at: `2026-09-15T12:00:00Z`.

Cutoff-valid activity rows naming the gold resource:
- `activity_3599` DELETE_RECORD at 2026-09-02T10:59:41Z; Δ=+1.005278 h; result=`SUCCESS`; status/result match=`True`; offset likelihood=0.961658 (offset:account_service|DELETE_RECORD modes=2 median=0.866944h iqr=0.0225..0.968611h)
- `activity_3608` SYNC_RECORD at 2026-09-02T12:45:33Z; Δ=-0.759167 h; result=`SUCCESS`; status/result match=`True`; offset likelihood=0.000000 (no_calibration_group)

Candidates for the gold resource and competing request owners:
- `case_24` score=0.996807; signals=activity_time_case_assignment, same_record_identity_resource; provenance=activity_3599, delta_hours=1.005278, evidence_92, offset:account_service|DELETE_RECORD modes=2 median=0.866944h iqr=0.0225..0.968611h
- `case_549` score=0.957328; signals=reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor; provenance=activity_3599, offset:account_service|DELETE_RECORD modes=2 median=0.866944h iqr=0.0225..0.968611h, delta_hours=1.005278, burst_strength=0.5353, reported_result=SUCCESS
- `case_550` score=0.903798; signals=reported_at_offset_likelihood, reported_status_result_likelihood; provenance=activity_3599, offset:account_service|DELETE_RECORD modes=2 median=0.866944h iqr=0.0225..0.968611h, delta_hours=1.005278, burst_strength=0.0000, reported_result=SUCCESS
- `case_24` score=0.970000; signals=reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor; provenance=activity_3599, offset:account_service|DELETE_RECORD modes=2 median=0.866944h iqr=0.0225..0.968611h, delta_hours=1.005278, burst_strength=1.0000, reported_result=SUCCESS
- `case_25` score=0.862162; signals=reported_at_offset_likelihood, reported_status_result_likelihood; provenance=activity_3599, offset:account_service|DELETE_RECORD modes=2 median=0.866944h iqr=0.0225..0.968611h, delta_hours=1.005278, burst_strength=0.0000, reported_result=SUCCESS
- `case_26` score=0.909402; signals=reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor; provenance=activity_3599, offset:account_service|DELETE_RECORD modes=2 median=0.866944h iqr=0.0225..0.968611h, delta_hours=1.005278, burst_strength=0.4724, reported_result=SUCCESS

Same-type candidates for the held-out request:

| Candidate | Score | Signals | Temporal offset/result/status | Provenance | Competing cases |
|---|---:|---|---|---|---|
| `account_5334` | 0.996807 | activity_time_case_assignment, same_record_identity_resource | `activity_3599` DELETE_RECORD at 2026-09-02T10:59:41Z; Δ=+1.005278 h; result=`SUCCESS`; status/result match=`True`; offset likelihood=0.961658 (offset:account_service|DELETE_RECORD modes=2 median=0.866944h iqr=0.0225..0.968611h) | activity_3599, delta_hours=1.005278, evidence_92, offset:account_service|DELETE_RECORD modes=2 median=0.866944h iqr=0.0225..0.968611h | case_549 (0.9573), case_26 (0.9094), case_550 (0.9038), case_25 (0.8622) |
| `account_5334` | 0.970000 | reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor | `activity_3599` DELETE_RECORD at 2026-09-02T10:59:41Z; Δ=+1.005278 h; result=`SUCCESS`; status/result match=`True`; offset likelihood=0.961658 (offset:account_service|DELETE_RECORD modes=2 median=0.866944h iqr=0.0225..0.968611h) | activity_3599, offset:account_service|DELETE_RECORD modes=2 median=0.866944h iqr=0.0225..0.968611h, delta_hours=1.005278, burst_strength=1.0000, reported_result=SUCCESS | case_549 (0.9573), case_26 (0.9094), case_550 (0.9038), case_25 (0.8622) |
| `account_7225` | 0.970000 | reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor | `activity_3601` DELETE_RECORD at 2026-09-02T11:10:25Z; Δ=+0.826389 h; result=`SUCCESS`; status/result match=`True`; offset likelihood=0.951097 (offset:account_service|DELETE_RECORD modes=2 median=0.866944h iqr=0.0225..0.968611h) | activity_3601, offset:account_service|DELETE_RECORD modes=2 median=0.866944h iqr=0.0225..0.968611h, delta_hours=0.826389, burst_strength=0.7878, reported_result=SUCCESS | case_549 (0.9700), case_550 (0.9385), case_26 (0.9207), case_25 (0.8600) |
| `account_5684` | 0.950039 | reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor | `activity_3600` DELETE_RECORD at 2026-09-02T11:08:43Z; Δ=+0.854722 h; result=`FAILED`; status/result match=`False`; offset likelihood=0.975611 (offset:account_service|DELETE_RECORD modes=2 median=0.878889h iqr=0.753819..1.076667h) | activity_3600, offset:account_service|DELETE_RECORD modes=2 median=0.878889h iqr=0.753819..1.076667h, delta_hours=0.854722, burst_strength=0.8825, reported_result=FAILED | case_26 (0.9564), case_549 (0.9224), case_25 (0.9029), case_550 (0.8618) |
| `account_4842` | 0.943869 | reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor | `activity_3598` DELETE_RECORD at 2026-09-02T10:50:09Z; Δ=+1.164167 h; result=`SUCCESS`; status/result match=`True`; offset likelihood=0.720759 (offset:account_service|DELETE_RECORD modes=2 median=0.866944h iqr=0.0225..0.968611h) | activity_3598, offset:account_service|DELETE_RECORD modes=2 median=0.866944h iqr=0.0225..0.968611h, delta_hours=1.164167, burst_strength=0.8825, reported_result=SUCCESS | case_549 (0.9029), case_26 (0.8557), case_550 (0.8556), case_25 (0.8140) |
| `account_3136` | 0.900660 | reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor | `activity_3597` DELETE_RECORD at 2026-09-02T10:48:27Z; Δ=+1.192500 h; result=`FAILED`; status/result match=`False`; offset likelihood=0.780418 (offset:account_service|DELETE_RECORD modes=2 median=0.98125h iqr=0.827222..1.143681h) | activity_3597, offset:account_service|DELETE_RECORD modes=2 median=0.98125h iqr=0.827222..1.143681h, delta_hours=1.192500, burst_strength=0.7791, reported_result=FAILED | case_26 (0.9007), case_549 (0.8644), case_25 (0.8639), case_550 (0.8227) |

## case_25 — `analytics_1895` (analytics)

Reported status: `NOT_STARTED`; reported_at: `2026-09-02T12:00:00Z`; audit_at: `2026-09-15T12:00:00Z`.

Cutoff-valid activity rows naming the gold resource:
- `activity_3602` ANONYMIZE_RECORD at 2026-09-02T11:31:08Z; Δ=+0.481111 h; result=`SUCCESS`; status/result match=`False`; offset likelihood=0.999890 (offset:analytics_platform|ANONYMIZE_RECORD modes=4 median=0.475278h iqr=0.469931..0.478333h)

Candidates for the gold resource and competing request owners:
- `case_549` score=0.970000; signals=reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor; provenance=activity_3602, offset:analytics_platform|ANONYMIZE_RECORD modes=4 median=0.475278h iqr=0.469931..0.478333h, delta_hours=0.481111, burst_strength=0.9849, reported_result=SUCCESS
- `case_550` score=0.955592; signals=reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor; provenance=activity_3602, offset:analytics_platform|ANONYMIZE_RECORD modes=4 median=0.475278h iqr=0.469931..0.478333h, delta_hours=0.481111, burst_strength=0.4169, reported_result=SUCCESS
- `case_10` score=0.917248; signals=reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor; provenance=activity_3602, offset:analytics_platform|ANONYMIZE_RECORD modes=4 median=0.105278h iqr=-1.457083..0.475278h, delta_hours=-1.385556, burst_strength=0.4724, reported_result=SUCCESS
- `case_24` score=0.970000; signals=reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor; provenance=activity_3602, offset:analytics_platform|ANONYMIZE_RECORD modes=4 median=0.475278h iqr=0.469931..0.478333h, delta_hours=0.481111, burst_strength=0.6873, reported_result=SUCCESS
- `case_25` score=0.868342; signals=reported_at_offset_likelihood, reported_status_result_likelihood; provenance=activity_3602, offset:analytics_platform|ANONYMIZE_RECORD modes=4 median=0.475278h iqr=0.469931..0.478333h, delta_hours=0.481111, burst_strength=0.0000, reported_result=SUCCESS
- `case_26` score=0.952522; signals=reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor; provenance=activity_3602, offset:analytics_platform|ANONYMIZE_RECORD modes=4 median=0.475278h iqr=0.469931..0.478333h, delta_hours=0.481111, burst_strength=0.8418, reported_result=SUCCESS

Same-type candidates for the held-out request:

| Candidate | Score | Signals | Temporal offset/result/status | Provenance | Competing cases |
|---|---:|---|---|---|---|
| `analytics_4566` | 0.868364 | reported_at_offset_likelihood, reported_status_result_likelihood | `activity_3603` ANONYMIZE_RECORD at 2026-09-02T11:31:24Z; Δ=+0.476667 h; result=`SUCCESS`; status/result match=`False`; offset likelihood=1.000000 (offset:analytics_platform|ANONYMIZE_RECORD modes=4 median=0.475278h iqr=0.469931..0.478333h) | activity_3603, offset:analytics_platform|ANONYMIZE_RECORD modes=4 median=0.475278h iqr=0.469931..0.478333h, delta_hours=0.476667, burst_strength=0.0000, reported_result=SUCCESS | case_24 (0.9700), case_549 (0.9700), case_550 (0.9612), case_26 (0.9530), case_10 (0.9133) |
| `analytics_1895` | 0.868342 | reported_at_offset_likelihood, reported_status_result_likelihood | `activity_3602` ANONYMIZE_RECORD at 2026-09-02T11:31:08Z; Δ=+0.481111 h; result=`SUCCESS`; status/result match=`False`; offset likelihood=0.999890 (offset:analytics_platform|ANONYMIZE_RECORD modes=4 median=0.475278h iqr=0.469931..0.478333h) | activity_3602, offset:analytics_platform|ANONYMIZE_RECORD modes=4 median=0.475278h iqr=0.469931..0.478333h, delta_hours=0.481111, burst_strength=0.0000, reported_result=SUCCESS | case_24 (0.9700), case_549 (0.9700), case_550 (0.9556), case_26 (0.9525), case_10 (0.9172) |

## case_26 — `analytics_4566` (analytics)

Reported status: `NOT_STARTED`; reported_at: `2026-09-02T12:00:00Z`; audit_at: `2026-09-15T12:00:00Z`.

Cutoff-valid activity rows naming the gold resource:
- `activity_3603` ANONYMIZE_RECORD at 2026-09-02T11:31:24Z; Δ=+0.476667 h; result=`SUCCESS`; status/result match=`False`; offset likelihood=0.999973 (offset:analytics_platform|ANONYMIZE_RECORD modes=4 median=0.476389h iqr=0.469931..0.480347h)

Candidates for the gold resource and competing request owners:
- `case_549` score=0.970000; signals=reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor; provenance=activity_3603, offset:analytics_platform|ANONYMIZE_RECORD modes=4 median=0.476389h iqr=0.469931..0.480347h, delta_hours=0.476667, burst_strength=0.9908, reported_result=SUCCESS
- `case_550` score=0.961159; signals=reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor; provenance=activity_3603, offset:analytics_platform|ANONYMIZE_RECORD modes=4 median=0.476389h iqr=0.469931..0.480347h, delta_hours=0.476667, burst_strength=0.4724, reported_result=SUCCESS
- `case_10` score=0.913317; signals=reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor; provenance=activity_3603, offset:analytics_platform|ANONYMIZE_RECORD modes=4 median=0.105278h iqr=-1.457083..0.476389h, delta_hours=-1.390000, burst_strength=0.4169, reported_result=SUCCESS
- `case_24` score=0.970000; signals=reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor; provenance=activity_3603, offset:analytics_platform|ANONYMIZE_RECORD modes=4 median=0.476389h iqr=0.469931..0.480347h, delta_hours=0.476667, burst_strength=0.6065, reported_result=SUCCESS
- `case_25` score=0.857137; signals=reported_at_offset_likelihood, reported_status_result_likelihood; provenance=activity_3603, offset:analytics_platform|ANONYMIZE_RECORD modes=4 median=0.476389h iqr=0.469931..0.480347h, delta_hours=0.476667, burst_strength=0.0000, reported_result=SUCCESS
- `case_26` score=0.941817; signals=reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor; provenance=activity_3603, offset:analytics_platform|ANONYMIZE_RECORD modes=4 median=0.476389h iqr=0.469931..0.480347h, delta_hours=0.476667, burst_strength=0.8468, reported_result=SUCCESS

Same-type candidates for the held-out request:

| Candidate | Score | Signals | Temporal offset/result/status | Provenance | Competing cases |
|---|---:|---|---|---|---|
| `analytics_4566` | 0.941817 | reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor | `activity_3603` ANONYMIZE_RECORD at 2026-09-02T11:31:24Z; Δ=+0.476667 h; result=`SUCCESS`; status/result match=`False`; offset likelihood=0.999973 (offset:analytics_platform|ANONYMIZE_RECORD modes=4 median=0.476389h iqr=0.469931..0.480347h) | activity_3603, offset:analytics_platform|ANONYMIZE_RECORD modes=4 median=0.476389h iqr=0.469931..0.480347h, delta_hours=0.476667, burst_strength=0.8468, reported_result=SUCCESS | case_24 (0.9700), case_549 (0.9700), case_550 (0.9612), case_10 (0.9133), case_25 (0.8571) |
| `analytics_1895` | 0.941317 | reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor | `activity_3602` ANONYMIZE_RECORD at 2026-09-02T11:31:08Z; Δ=+0.481111 h; result=`SUCCESS`; status/result match=`False`; offset likelihood=0.999973 (offset:analytics_platform|ANONYMIZE_RECORD modes=4 median=0.476389h iqr=0.469931..0.480347h) | activity_3602, offset:analytics_platform|ANONYMIZE_RECORD modes=4 median=0.476389h iqr=0.469931..0.480347h, delta_hours=0.481111, burst_strength=0.8418, reported_result=SUCCESS | case_24 (0.9700), case_549 (0.9700), case_550 (0.9556), case_10 (0.9172), case_25 (0.8571) |

## case_28 — `account_5482` (account)

Reported status: `NOT_STARTED`; reported_at: `2026-08-30T12:00:00Z`; audit_at: `2026-09-15T12:00:00Z`.

Cutoff-valid activity rows naming the gold resource:
- `activity_3529` DELETE_RECORD at 2026-08-30T10:46:13Z; Δ=+1.229722 h; result=`FAILED`; status/result match=`True`; offset likelihood=0.589687 (offset:account_service|DELETE_RECORD modes=2 median=0.878889h iqr=0.753819..1.064306h)

Candidates for the gold resource and competing request owners:
- `case_539` score=0.837937; signals=reported_at_offset_likelihood, reported_status_result_likelihood; provenance=activity_3529, offset:account_service|DELETE_RECORD modes=2 median=0.878889h iqr=0.753819..1.064306h, delta_hours=1.229722, burst_strength=0.0000, reported_result=FAILED
- `case_27` score=0.823931; signals=reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor; provenance=activity_3529, offset:account_service|DELETE_RECORD modes=2 median=0.878889h iqr=0.753819..1.064306h, delta_hours=1.229722, burst_strength=0.4169, reported_result=FAILED
- `case_28` score=0.885177; signals=reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor; provenance=activity_3529, offset:account_service|DELETE_RECORD modes=2 median=0.878889h iqr=0.753819..1.064306h, delta_hours=1.229722, burst_strength=0.4724, reported_result=FAILED
- `case_29` score=0.837937; signals=reported_at_offset_likelihood, reported_status_result_likelihood; provenance=activity_3529, offset:account_service|DELETE_RECORD modes=2 median=0.878889h iqr=0.753819..1.064306h, delta_hours=1.229722, burst_strength=0.0000, reported_result=FAILED

Same-type candidates for the held-out request:

| Candidate | Score | Signals | Temporal offset/result/status | Provenance | Competing cases |
|---|---:|---|---|---|---|
| `account_7012` | 0.970000 | reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor | `activity_3532` DELETE_RECORD at 2026-08-30T11:06:57Z; Δ=+0.884167 h; result=`FAILED`; status/result match=`True`; offset likelihood=1.000000 (offset:account_service|DELETE_RECORD modes=2 median=0.884167h iqr=0.818056..1.108889h) | activity_3532, offset:account_service|DELETE_RECORD modes=2 median=0.884167h iqr=0.818056..1.108889h, delta_hours=0.884167, burst_strength=0.6873, reported_result=FAILED | case_27 (0.9250), case_29 (0.9200), case_539 (0.9200) |
| `account_3866` | 0.900441 | reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor | `activity_3530` DELETE_RECORD at 2026-08-30T10:57:28Z; Δ=+1.042222 h; result=`SUCCESS`; status/result match=`False`; offset likelihood=0.948843 (offset:account_service|DELETE_RECORD modes=2 median=0.870278h iqr=0.032153..0.996111h) | activity_3530, offset:account_service|DELETE_RECORD modes=2 median=0.870278h iqr=0.032153..0.996111h, delta_hours=1.042222, burst_strength=0.5353, reported_result=SUCCESS | case_27 (0.9509), case_29 (0.8469), case_539 (0.8469) |
| `account_5482` | 0.885177 | reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor | `activity_3529` DELETE_RECORD at 2026-08-30T10:46:13Z; Δ=+1.229722 h; result=`FAILED`; status/result match=`True`; offset likelihood=0.589687 (offset:account_service|DELETE_RECORD modes=2 median=0.878889h iqr=0.753819..1.064306h) | activity_3529, offset:account_service|DELETE_RECORD modes=2 median=0.878889h iqr=0.753819..1.064306h, delta_hours=1.229722, burst_strength=0.4724, reported_result=FAILED | case_29 (0.8379), case_539 (0.8379), case_27 (0.8239) |

## case_29 — `account_7012` (account)

Reported status: `NOT_STARTED`; reported_at: `2026-08-30T12:00:00Z`; audit_at: `2026-09-15T12:00:00Z`.

Cutoff-valid activity rows naming the gold resource:
- `activity_3532` DELETE_RECORD at 2026-08-30T11:06:57Z; Δ=+0.884167 h; result=`FAILED`; status/result match=`True`; offset likelihood=0.961159 (offset:account_service|DELETE_RECORD modes=2 median=0.892639h iqr=0.753819..1.076667h)

Candidates for the gold resource and competing request owners:
- `case_539` score=0.891840; signals=reported_at_offset_likelihood, reported_status_result_likelihood; provenance=activity_3532, offset:account_service|DELETE_RECORD modes=2 median=0.892639h iqr=0.753819..1.076667h, delta_hours=0.884167, burst_strength=0.0000, reported_result=FAILED
- `case_27` score=0.917186; signals=reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor; provenance=activity_3532, offset:account_service|DELETE_RECORD modes=2 median=0.892639h iqr=0.753819..1.076667h, delta_hours=0.884167, burst_strength=0.6065, reported_result=FAILED
- `case_28` score=0.960570; signals=reported_at_offset_likelihood, reported_status_result_likelihood, same_burst_activity_anchor; provenance=activity_3532, offset:account_service|DELETE_RECORD modes=2 median=0.892639h iqr=0.753819..1.076667h, delta_hours=0.884167, burst_strength=0.6873, reported_result=FAILED
- `case_29` score=0.891840; signals=reported_at_offset_likelihood, reported_status_result_likelihood; provenance=activity_3532, offset:account_service|DELETE_RECORD modes=2 median=0.892639h iqr=0.753819..1.076667h, delta_hours=0.884167, burst_strength=0.0000, reported_result=FAILED

Same-type candidates for the held-out request:

| Candidate | Score | Signals | Temporal offset/result/status | Provenance | Competing cases |
|---|---:|---|---|---|---|
| `account_7012` | 0.891840 | reported_at_offset_likelihood, reported_status_result_likelihood | `activity_3532` DELETE_RECORD at 2026-08-30T11:06:57Z; Δ=+0.884167 h; result=`FAILED`; status/result match=`True`; offset likelihood=0.961159 (offset:account_service|DELETE_RECORD modes=2 median=0.892639h iqr=0.753819..1.076667h) | activity_3532, offset:account_service|DELETE_RECORD modes=2 median=0.892639h iqr=0.753819..1.076667h, delta_hours=0.884167, burst_strength=0.0000, reported_result=FAILED | case_28 (0.9606), case_27 (0.9172), case_539 (0.8918) |
| `account_5482` | 0.875697 | reported_at_offset_likelihood, reported_status_result_likelihood | `activity_3529` DELETE_RECORD at 2026-08-30T10:46:13Z; Δ=+1.229722 h; result=`FAILED`; status/result match=`True`; offset likelihood=0.880447 (offset:account_service|DELETE_RECORD modes=2 median=1.078333h iqr=0.818056..1.155278h) | activity_3529, offset:account_service|DELETE_RECORD modes=2 median=1.078333h iqr=0.818056..1.155278h, delta_hours=1.229722, burst_strength=0.0000, reported_result=FAILED | case_28 (0.9229), case_27 (0.8821), case_539 (0.8757) |
| `account_3866` | 0.871716 | reported_at_offset_likelihood, reported_status_result_likelihood | `activity_3530` DELETE_RECORD at 2026-08-30T10:57:28Z; Δ=+1.042222 h; result=`SUCCESS`; status/result match=`False`; offset likelihood=0.970345 (offset:account_service|DELETE_RECORD modes=2 median=0.892639h iqr=0.753819..1.076667h) | activity_3530, offset:account_service|DELETE_RECORD modes=2 median=0.892639h iqr=0.753819..1.076667h, delta_hours=1.042222, burst_strength=0.0000, reported_result=SUCCESS | case_27 (0.9552), case_28 (0.9252), case_539 (0.8717) |

