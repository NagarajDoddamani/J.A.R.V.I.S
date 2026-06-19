"""Check database table schemas."""
import psycopg2

conn = psycopg2.connect('host=127.0.0.1 port=5432 user=jarvis_admin password=jarvis_secure_pass dbname=jarvis_db')
cur = conn.cursor()

schemas = {
    'memory': ['memories', 'consent_records', 'outbox'],
    'agent': ['agents', 'agent_tasks', 'agent_executions', 'agent_outbox'],
    'automation': ['automations', 'triggers', 'executions'],
    'policy': ['policies', 'rules', 'evaluations'],
    'research': ['research_requests', 'research_jobs', 'research_sources'],
    'knowledge': ['knowledge_sources', 'knowledge_documents', 'knowledge_chunks', 'ingestion_jobs'],
}

for schema, tables in schemas.items():
    for table in tables:
        try:
            cur.execute(
                "SELECT column_name, data_type, is_nullable "
                "FROM information_schema.columns "
                "WHERE table_schema=%s AND table_name=%s "
                "ORDER BY ordinal_position",
                (schema, table)
            )
            cols = cur.fetchall()
            print(f"\n{schema}.{table}:")
            for c in cols:
                print(f"  {c[0]} ({c[1]}, nullable={c[2]})")
        except Exception as e:
            print(f"\n{schema}.{table}: ERROR - {e}")

cur.close()
conn.close()
