"""Fix ORM/DB schema mismatches for memory, consent, and other tables."""
import psycopg2

conn = psycopg2.connect('host=127.0.0.1 port=5432 user=jarvis_admin password=jarvis_secure_pass dbname=jarvis_db')
cur = conn.cursor()

# 1. Fix memory.memories - add missing columns to match ORM
cur.execute("""
    ALTER TABLE memory.memories 
    ADD COLUMN IF NOT EXISTS content TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS category VARCHAR(32) NOT NULL DEFAULT 'GENERAL',
    ADD COLUMN IF NOT EXISTS provenance_actor_id VARCHAR(256),
    ADD COLUMN IF NOT EXISTS provenance_timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS classification VARCHAR(16) NOT NULL DEFAULT 'public',
    ADD COLUMN IF NOT EXISTS retention_status VARCHAR(16) NOT NULL DEFAULT 'active',
    ADD COLUMN IF NOT EXISTS revision INTEGER NOT NULL DEFAULT 1
""")

# 2. Fix memory.consent_records - rename to consents (or keep both)
# The ORM uses table "consents" but migration created "consent_records"
# Create the "consents" table matching ORM model
cur.execute("""
    CREATE TABLE IF NOT EXISTS memory.consents (
        consent_id VARCHAR(256) PRIMARY KEY,
        status VARCHAR(16) NOT NULL DEFAULT 'PROPOSED',
        granted_at TIMESTAMPTZ,
        expires_at TIMESTAMPTZ,
        revoked_at TIMESTAMPTZ,
        policy_version VARCHAR(16) NOT NULL DEFAULT '1.0'
    )
""")

# 3. Fix knowledge.knowledge_sources - ensure location is nullable with default
cur.execute("""
    ALTER TABLE knowledge.knowledge_sources 
    ALTER COLUMN location SET DEFAULT '',
    ALTER COLUMN classification SET DEFAULT 'public'
""")

# 4. Fix knowledge.knowledge_documents - add content column for document body
cur.execute("""
    ALTER TABLE knowledge.knowledge_documents 
    ADD COLUMN IF NOT EXISTS content TEXT DEFAULT ''
""")

# 5. Ensure agent outbox has proper defaults
cur.execute("""
    ALTER TABLE agent.agent_outbox 
    ALTER COLUMN created_at SET DEFAULT now(),
    ALTER COLUMN payload SET DEFAULT '{}'::jsonb,
    ALTER COLUMN headers SET DEFAULT '{}'::jsonb,
    ALTER COLUMN attempts SET DEFAULT 0
""")

conn.commit()
print("Schema fixes applied successfully")

# Verify
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='memory' AND table_name='memories' ORDER BY ordinal_position")
cols = [r[0] for r in cur.fetchall()]
print(f"\nmemory.memories columns: {cols}")

cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='memory' AND table_name='consents' ORDER BY ordinal_position")
cols = [r[0] for r in cur.fetchall()]
print(f"memory.consents columns: {cols}")

cur.close()
conn.close()
