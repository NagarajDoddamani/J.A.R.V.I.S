# JARVIS Restore Workflow

## PostgreSQL Restore
1. Ensure the database is running.
2. Run: `psql <database_url> < backup_file.sql`

## Redis Restore
1. Stop Redis service.
2. Replace `dump.rdb` with the backup file.
3. Start Redis service.

## Qdrant Restore
1. Use the Qdrant Snapshot API:
   `POST /collections/{collection_name}/snapshots/recover`
   with the snapshot file location.

## Security Note
All backups are stored locally. Do not upload to cloud storage.
Ensure backup directory permissions are restricted to the local user.
