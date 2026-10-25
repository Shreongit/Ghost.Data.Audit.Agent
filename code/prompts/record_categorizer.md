# Record categorizer

Classify a single evidence-backed record using its collection, table, field names, and attachment metadata. Choose only one category from the provided policy table. A support attachment is a separate file/object linked to a support conversation; shared conversation context is a support message. Use record contents and collection metadata, never system name alone. Explain the exact condition from the policy table and quote the evidence that supports it. If the record is ambiguous, return `UNKNOWN` rather than guessing.
