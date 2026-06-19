"""Fix outbox table NOT NULL constraints that don't match ORM models."""
import psycopg2

conn = psycopg2.connect('host=127.0.0.1 port=5432 user=jarvis_admin password=jarvis_secure_pass dbname=jarvis_db')
cur = conn.cursor()

# Memory outbox: payload column is NOT NULL in DB but ORM defines nullable=True
cur.execute("""
    ALTER TABLE memory.outbox ALTER COLUMN payload DROP NOT NULL,
                              ALTER COLUMN correlation_id DROP NOT NULL,
                              ALTER COLUMN causation_id DROP NOT NULL
""")

# Knowledge outbox: same issue
cur.execute("""
    ALTER TABLE knowledge.outbox ALTER COLUMN payload DROP NOT NULL,
                                 ALTER COLUMN correlation_id DROP NOT NULL,
                                 ALTER COLUMN causation_id DROP NOT NULL
""")

# Policy outbox: correlation_id is NOT NULL
cur.execute("""
    ALTER TABLE policy.outbox ALTER COLUMN payload DROP NOT NULL,
                              ALTER COLUMN correlation_id DROP NOT NULL,
                              ALTER COLUMN causation_id DROP NOT NULL
""")

# Agent outbox: correlation_id is nullable already but ensure causation_id too
cur.execute("""
    ALTER TABLE agent.agent_outbox ALTER COLUMN correlation_id DROP NOT NULL,
                                   ALTER COLUMN causation_id DROP NOT NULL,
                                   ALTER COLUMN payload SET DEFAULT '{}'::jsonb,
                                   ALTER COLUMN headers SET DEFAULT '{}'::jsonb
""")

# Research outbox: ensure nullable
cur.execute("""
    ALTER TABLE research.outbox ALTER COLUMN payload DROP NOT NULL,
                                ALTER COLUMN correlation_id DROP NOT NULL,
                                ALTER COLUMN causation_id DROP NOT NULL
""")

# Planner outbox: ensure nullable
cur.execute("""
    ALTER TABLE planner.outbox ALTER COLUMN payload DROP NOT NULL,
                               ALTER COLUMN correlation_id DROP NOT NULL,
                               ALTER COLUMN causation_id DROP NOT NULL
""")

# Automation outbox: ensure nullable
cur.execute("""
    ALTER TABLE automation.outbox ALTER COLUMN payload DROP NOT NULL,
                                  ALTER COLUMN correlation_id DROP NOT NULL,
                                  ALTER COLUMN causation_id DROP NOT NULL
""")

# Notification outbox: ensure nullable
cur.execute("""
    ALTER TABLE notification.outbox ALTER COLUMN payload DROP NOT NULL,
                                    ALTER COLUMN correlation_id DROP NOT NULL,
                                    ALTER COLUMN causation_id DROP NOT NULL
""")

# Orchestration outbox: ensure nullable
cur.execute("""
    ALTER TABLE orchestration.outbox ALTER COLUMN payload DROP NOT NULL,
                                     ALTER COLUMN correlation_id DROP NOT NULL,
                                     ALTER COLUMN causation_id DROP NOT NULL
""")

# Settings outbox: ensure nullable
cur.execute("""
    ALTER TABLE settings.outbox ALTER COLUMN payload DROP NOT NULL,
                                ALTER COLUMN correlation_id DROP NOT NULL,
                                ALTER COLUMN causation_id DROP NOT NULL
""")

# Audit outbox: ensure nullable
cur.execute("""
    ALTER TABLE audit.outbox ALTER COLUMN payload DROP NOT NULL,
                             ALTER COLUMN correlation_id DROP NOT NULL,
                             ALTER COLUMN causation_id DROP NOT NULL
""")

conn.commit()

# Verify
cur.execute("""
    SELECT table_schema, column_name, is_nullable 
    FROM information_schema.columns 
    WHERE table_name='outbox' AND column_name IN ('payload', 'correlation_id', 'causation_id')
    ORDER BY table_schema, column_name
""")
print("Outbox columns after fix:")
for r in cur.fetchall():
    print(f"  {r[0]}.{r[1]}: nullable={r[2]}")

cur.execute("""
    SELECT column_name, is_nullable 
    FROM information_schema.columns 
    WHERE table_schema='agent' AND table_name='agent_outbox' AND column_name IN ('payload', 'correlation_id', 'causation_id', 'headers')
    ORDER BY column_name
""")
print("Agent outbox columns after fix:")
for r in cur.fetchall():
    print(f"  agent.agent_outbox.{r[0]}: nullable={r[2] if len(r)>2 else r[1]}")

cur.close()
conn.close()
