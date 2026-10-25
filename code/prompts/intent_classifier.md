# Intent classification prompt contract

Classify only the request text. Determine whether the person authorizes deletion of their account or personal data. Access, correction, export, portability, marketing opt-out, and unsubscribe are not deletion requests. Explicit negation overrides a deletion keyword unless a later clause clearly requests deletion. Never infer authorization from reported status, identity, or workflow events.

Return a single JSON object with: `authorizes_deletion` (boolean), `action_type` (`deletion`, `access`, `correction`, `export`, `marketing_opt_out`, or `other`), `language` (language name or `unknown`), `confidence` (0–1), and `rationale_quote` (a verbatim substring from the request). If the quote cannot be copied exactly, return low confidence.

The deterministic multilingual classifier runs first. This model is called only for uncertain or negated language, at temperature zero. Its JSON schema is verified and its rationale quote must match the request text before it can change the deterministic decision.
