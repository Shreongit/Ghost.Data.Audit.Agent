-- Ghost Data Still Exists: point-in-time database snapshot
-- Dialect: SQLite-compatible SQL
-- Captured at: 2026-09-02T23:00:00Z
-- Database topology: failover_replica
-- Compare the primary and any replica tables for replication drift.

BEGIN TRANSACTION;
CREATE TABLE customer_profiles_failover_replica (
                resource_id TEXT PRIMARY KEY, user_id TEXT NOT NULL,
                full_name TEXT NOT NULL, email TEXT NOT NULL, phone TEXT NOT NULL,
                account_status TEXT NOT NULL, updated_at TEXT NOT NULL
            );
INSERT INTO "customer_profiles_failover_replica" VALUES('account_005','user_05','Leila Haddad','leila.haddad@yahoo.com','+212 6 48 27 15 93','ACTIVE','2026-09-02T22:45:00Z');
INSERT INTO "customer_profiles_failover_replica" VALUES('account_8741','user_8741','Karim El-Masri','karim.elmasri@gmail.com','+971 50 731 6284','ACTIVE','2026-09-02T22:45:00Z');
INSERT INTO "customer_profiles_failover_replica" VALUES('account_9116','user_9116','Mateo Rios Gil','m.rios.gil@outlook.com','+34 628 491 736','ACTIVE','2026-09-02T22:45:00Z');
INSERT INTO "customer_profiles_failover_replica" VALUES('account_7204','user_7204','Priya Ramanathan','p.ramanathan@gmail.com','+91 90000 82014','ACTIVE','2026-09-02T22:45:00Z');
CREATE TABLE customer_profiles_primary (
                resource_id TEXT PRIMARY KEY, user_id TEXT NOT NULL,
                full_name TEXT NOT NULL, email TEXT NOT NULL, phone TEXT NOT NULL,
                account_status TEXT NOT NULL, updated_at TEXT NOT NULL
            );
INSERT INTO "customer_profiles_primary" VALUES('account_8741','user_8741','Karim El-Masri','karim.elmasri@gmail.com','+971 50 731 6284','ACTIVE','2026-09-02T22:45:00Z');
INSERT INTO "customer_profiles_primary" VALUES('account_9116','user_9116','Mateo Rios Gil','m.rios.gil@outlook.com','+34 628 491 736','ACTIVE','2026-09-02T22:45:00Z');
INSERT INTO "customer_profiles_primary" VALUES('account_7204','user_7204','Priya Ramanathan','p.ramanathan@gmail.com','+91 90000 82014','ACTIVE','2026-09-02T22:45:00Z');
COMMIT;
