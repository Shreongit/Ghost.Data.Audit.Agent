# Custom classifier cases

All cases are synthetic and independent of dataset labels.

| Input | Expected deletion intent | Deterministic classifier |
|---|---:|---:|
| `Je demande la suppression définitive de mon compte.` | true | pass |
| `Please export and download a copy of my data.` | false | pass |
| `Do not delete my account; only send me an export.` | false | pass |

The evaluation command runs these directly and records their results in `evaluation_report.md`.
