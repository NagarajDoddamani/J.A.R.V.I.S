"""Create missing agent schema tables."""
import psycopg2

conn = psycopg2.connect(host='127.0.0.1', port=5432, user='jarvis_admin', password='jarvis_secure_pass', dbname='jarvis_db')
cur = conn.cursor()

cur.execute("CREATE SCHEMA IF NOT EXISTS agent")
cur.execute("""
    CREATE TABLE IF NOT EXISTS agent.agents (
        agent_id VARCHAR(256) PRIMARY KEY,
        agent_type VARCHAR(16) NOT NULL,
        name TEXT,
        status VARCHAR(16) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ
    )
""")
cur.execute("""
    CREATE TABLE IF NOT EXISTS agent.agent_tasks (
        task_id VARCHAR(256) PRIMARY KEY,
        agent_id VARCHAR(256),
        goal TEXT,
        instruction TEXT,
        status VARCHAR(16) NOT NULL,
        result TEXT,
        failure_reason TEXT
    )
""")
cur.execute("""
    CREATE TABLE IF NOT EXISTS agent.agent_executions (
        execution_id VARCHAR(256) PRIMARY KEY,
        agent_id VARCHAR(256),
        task_id VARCHAR(256),
        status VARCHAR(16) NOT NULL,
        result TEXT,
        failure_reason TEXT
    )
""")
cur.execute("""
    CREATE TABLE IF NOT EXISTS agent.agent_outbox (
        message_id UUID PRIMARY KEY,
        subject VARCHAR(512) NOT NULL,
        aggregate_id UUID,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        payload JSONB NOT NULL DEFAULT '{}',
        published_at TIMESTAMPTZ,
        headers JSONB NOT NULL DEFAULT '{}',
        attempts INTEGER NOT NULL DEFAULT 0,
        last_error TEXT,
        correlation_id UUID,
        causation_id UUID
    )
""")
conn.commit()
cur.close()
conn.close()
print("Agent schema tables created")
