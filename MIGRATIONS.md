# Database Migration Strategy

## Overview

This document describes the database migration strategy for the Claude Multi-Agent Bridge. The system uses SQLite for persistence (collaboration rooms, messages, files, auth tokens).

## Current Schema Version

**Version**: 1.0.0
**Schema Files**:
- `collab_persistence.py` - Collaboration database schema
- `auth.py` - Token storage schema

## Migration Approach

### Manual Migrations (Current)

Until we integrate Alembic or similar, follow this manual migration process:

#### 1. Schema Changes

When modifying database schema:

1. **Backup existing database**:
   ```bash
   cp data/collab.db data/collab.db.backup.$(date +%Y%m%d_%H%M%S)
   cp data/tokens.json data/tokens.json.backup.$(date +%Y%m%d_%H%M%S)
   ```

2. **Document the change** in this file (see Migration Log below)

3. **Create migration script** in `migrations/` directory:
   ```python
   # migrations/001_add_user_preferences.py
   import sqlite3

   def upgrade(db_path):
       conn = sqlite3.connect(db_path)
       cursor = conn.cursor()

       # Add new column
       cursor.execute("""
           ALTER TABLE rooms ADD COLUMN preferences TEXT DEFAULT '{}'
       """)

       conn.commit()
       conn.close()

   def downgrade(db_path):
       # SQLite doesn't support DROP COLUMN easily
       # Document the rollback process
       pass
   ```

4. **Run migration manually**:
   ```bash
   python -c "from migrations.001_add_user_preferences import upgrade; upgrade('data/collab.db')"
   ```

5. **Test thoroughly** with backup data

#### 2. Data Migrations

For data transformations:

```python
# migrations/002_normalize_timestamps.py
import sqlite3
from datetime import datetime, timezone

def upgrade(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Update timestamps to UTC format
    cursor.execute("SELECT id, timestamp FROM messages WHERE timestamp NOT LIKE '%+00:00'")

    for row in cursor.fetchall():
        msg_id, old_ts = row
        # Convert to UTC
        new_ts = datetime.fromisoformat(old_ts).astimezone(timezone.utc).isoformat()
        cursor.execute("UPDATE messages SET timestamp = ? WHERE id = ?", (new_ts, msg_id))

    conn.commit()
    conn.close()
```

### Future: Alembic Integration

When the project scales, integrate Alembic:

```bash
pip install alembic
alembic init migrations
```

**alembic.ini**:
```ini
sqlalchemy.url = sqlite:///data/collab.db
```

**env.py**:
```python
from collab_persistence import CollabPersistence
target_metadata = CollabPersistence.metadata
```

**Create migration**:
```bash
alembic revision --autogenerate -m "Add user preferences"
alembic upgrade head
```

## Migration Log

### Version 1.0.0 (2026-02-22)
- Initial schema
- Tables: rooms, members, messages, files, decisions, votes
- Auth: JSON file storage for tokens

### Planned Migrations

**v1.1.0** (Future):
- Add `preferences` column to `rooms` table
- Add `metadata` column to `members` table
- Migrate auth tokens from JSON to SQLite

**v1.2.0** (Future):
- Add message threading support
- Add reactions table
- Add message edits/deletes tracking

## Rollback Procedures

### Emergency Rollback

If a migration fails:

1. **Stop the server**:
   ```bash
   pkill -f server_ws.py
   ```

2. **Restore from backup**:
   ```bash
   cp data/collab.db.backup.YYYYMMDD_HHMMSS data/collab.db
   ```

3. **Restart server** with previous code version

### Partial Rollback

If only some records are affected:

```sql
-- Example: Revert specific records
UPDATE messages
SET timestamp = old_timestamp_value
WHERE id IN (SELECT id FROM migration_affected_records);
```

## Testing Migrations

### Pre-Migration Checklist

- [ ] Backup database
- [ ] Test migration on copy of production data
- [ ] Verify application still works with new schema
- [ ] Document rollback procedure
- [ ] Update schema version in code

### Test Script

```python
# test_migration.py
import shutil
import sqlite3

def test_migration(migration_module):
    # Copy production db to test
    shutil.copy('data/collab.db', 'data/test_migration.db')

    # Run migration
    migration_module.upgrade('data/test_migration.db')

    # Verify schema
    conn = sqlite3.connect('data/test_migration.db')
    cursor = conn.cursor()

    # Check new column exists
    cursor.execute("PRAGMA table_info(rooms)")
    columns = [col[1] for col in cursor.fetchall()]
    assert 'preferences' in columns

    # Test application with new schema
    # ... (run key queries)

    conn.close()
    print("✅ Migration test passed")
```

## Best Practices

1. **Always backup** before migrations
2. **Test migrations** on production copy first
3. **Document rollback** for every migration
4. **Keep migrations small** and focused
5. **Version migrations** sequentially (001, 002, 003...)
6. **Never edit applied migrations** - create new ones
7. **Handle NULL values** when adding columns
8. **Consider data size** for large tables (batch updates)

## Schema Versioning

Track schema version in database:

```sql
CREATE TABLE IF NOT EXISTS schema_version (
    version TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL,
    migration_file TEXT NOT NULL
);

INSERT INTO schema_version VALUES ('1.0.0', datetime('now'), 'initial');
```

Query current version:
```python
def get_schema_version(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1")
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None
```

## Multi-Server Migrations

For distributed deployments:

1. **Blue-Green Deployment**:
   - Run migration on blue environment
   - Test thoroughly
   - Switch traffic to blue
   - Update green environment

2. **Rolling Updates**:
   - Ensure backward-compatible schemas
   - Add columns as NULL initially
   - Backfill data in background
   - Make columns NOT NULL in later migration

3. **Coordination**:
   - Use migration lock file
   - Only one server runs migration
   - Others wait for completion

```python
import fcntl

def run_migration_with_lock(migration_func):
    with open('/tmp/migration.lock', 'w') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        migration_func()
        fcntl.flock(f, fcntl.LOCK_UN)
```

## Support

For migration issues:
- Check logs in `logs/migration_*.log`
- Restore from backup if critical
- Contact maintainers with error details
