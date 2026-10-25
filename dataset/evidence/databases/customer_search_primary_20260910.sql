-- Ghost Data Still Exists: point-in-time database snapshot
-- Dialect: SQLite-compatible SQL
-- Captured at: 2026-09-10T08:45:00Z
-- Database topology: primary_only
-- Compare the primary and any replica tables for replication drift.

BEGIN TRANSACTION;
CREATE TABLE search_documents_primary (resource_id TEXT PRIMARY KEY, display_name TEXT, email TEXT, source_resource_id TEXT, indexed_at TEXT);
INSERT INTO "search_documents_primary" VALUES('search_001','Jonas Berg','jonas.berg@outlook.com','account_006','2026-09-09T22:12:00Z');
INSERT INTO "search_documents_primary" VALUES('search_8814','Jonas Berglund','jonas.berglund@outlook.com','account_8814','2026-09-09T22:13:00Z');
INSERT INTO "search_documents_primary" VALUES('search_4203','Joana Berg','joana.berg@outlook.com','account_4203','2026-09-09T22:13:00Z');
COMMIT;
