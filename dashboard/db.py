#!/usr/bin/env python3
"""Módulo de armazenamento PostgreSQL para o dashboard.
Usa Neon (serverless PostgreSQL) para persistir dados entre deploys."""
import json
import os
import psycopg2
import psycopg2.extras
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager

DATABASE_URL = os.environ.get('DATABASE_URL', '')

def get_conn_params():
    """Parse DATABASE_URL into connection params."""
    if not DATABASE_URL:
        return None
    # Handle postgres:// -> postgresql://
    url = DATABASE_URL.replace('postgres://', 'postgresql://')
    return url

@contextmanager
def get_conn():
    """Context manager for PostgreSQL connection."""
    url = get_conn_params()
    if not url:
        raise RuntimeError("DATABASE_URL não configurada")
    
    conn = psycopg2.connect(url, sslmode='require')
    conn.autocommit = False
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Create tables if they don't exist."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ideas (
                    id SERIAL PRIMARY KEY,
                    idea_id INTEGER UNIQUE,
                    title TEXT,
                    keyword TEXT,
                    category TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT,
                    cpm_estimate TEXT,
                    source TEXT
                );
                
                CREATE TABLE IF NOT EXISTS pipeline_history (
                    id SERIAL PRIMARY KEY,
                    keyword TEXT,
                    article TEXT,
                    title TEXT,
                    image TEXT,
                    image_url TEXT,
                    post_url TEXT,
                    steps JSONB,
                    completed_at TEXT
                );
                
                CREATE TABLE IF NOT EXISTS verify_history (
                    id SERIAL PRIMARY KEY,
                    filename TEXT,
                    score INTEGER,
                    status TEXT,
                    issues_count INTEGER,
                    warnings_count INTEGER,
                    verified_at TEXT
                );
                
                CREATE TABLE IF NOT EXISTS config (
                    id SERIAL PRIMARY KEY,
                    config_key TEXT UNIQUE,
                    config_value JSONB,
                    updated_at TEXT
                );
                
                CREATE TABLE IF NOT EXISTS checkpoints (
                    id SERIAL PRIMARY KEY,
                    slug TEXT,
                    step TEXT,
                    data JSONB,
                    created_at TEXT,
                    UNIQUE(slug, step)
                );
                
                CREATE INDEX IF NOT EXISTS idx_ideas_status ON ideas(status);
                CREATE INDEX IF NOT EXISTS idx_pipeline_completed ON pipeline_history(completed_at);
                CREATE INDEX IF NOT EXISTS idx_verify_verified ON verify_history(verified_at);
            """)

# ═══════════════════════════════════════════════════════════════════
# Ideas
# ═══════════════════════════════════════════════════════════════════

def get_ideas(status=None, limit=100):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if status:
                cur.execute("SELECT * FROM ideas WHERE status=%s ORDER BY created_at DESC LIMIT %s", (status, limit))
            else:
                cur.execute("SELECT * FROM ideas ORDER BY created_at DESC LIMIT %s", (limit,))
            return [dict(r) for r in cur.fetchall()]

def save_idea(idea):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO ideas (idea_id, title, keyword, category, status, created_at, cpm_estimate, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (idea_id) DO UPDATE SET
                    title=EXCLUDED.title, keyword=EXCLUDED.keyword, category=EXCLUDED.category, status=EXCLUDED.status
            """, (idea.get('id'), idea.get('title'), idea.get('keyword'), idea.get('category'),
                  idea.get('status', 'pending'), idea.get('created_at', datetime.now().isoformat()),
                  idea.get('cpm_estimate'), idea.get('source')))

def update_idea_status(idea_id, status):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE ideas SET status=%s WHERE idea_id=%s", (status, idea_id))

# ═══════════════════════════════════════════════════════════════════
# Pipeline History
# ═══════════════════════════════════════════════════════════════════

def get_pipeline_history(limit=50):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM pipeline_history ORDER BY completed_at DESC LIMIT %s", (limit,))
            result = []
            for r in cur.fetchall():
                d = dict(r)
                d['steps'] = json.loads(d['steps']) if d['steps'] else []
                result.append(d)
            return result

def save_pipeline_history(entry):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO pipeline_history (keyword, article, title, image, image_url, post_url, steps, completed_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (entry.get('keyword'), entry.get('article'), entry.get('title'),
                  entry.get('image'), entry.get('image_url'), entry.get('post_url'),
                  json.dumps(entry.get('steps', [])), entry.get('completed_at', datetime.now().isoformat())))

# ═══════════════════════════════════════════════════════════════════
# Verify History
# ═══════════════════════════════════════════════════════════════════

def get_verify_history(limit=50):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM verify_history ORDER BY verified_at DESC LIMIT %s", (limit,))
            return [dict(r) for r in cur.fetchall()]

def save_verify_history(entry):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO verify_history (filename, score, status, issues_count, warnings_count, verified_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (entry.get('filename'), entry.get('score'), entry.get('status'),
                  entry.get('issues_count'), entry.get('warnings_count'),
                  entry.get('verified_at', datetime.now().isoformat())))

# ═══════════════════════════════════════════════════════════════════
# Config
# ═══════════════════════════════════════════════════════════════════

def get_config(key, default=None):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT config_value FROM config WHERE config_key=%s", (key,))
            row = cur.fetchone()
            if row:
                return json.loads(row['config_value']) if isinstance(row['config_value'], str) else row['config_value']
            return default

def save_config(key, value):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO config (config_key, config_value, updated_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (config_key) DO UPDATE SET
                    config_value=EXCLUDED.config_value, updated_at=EXCLUDED.updated_at
            """, (key, json.dumps(value), datetime.now().isoformat()))

# ═══════════════════════════════════════════════════════════════════
# Checkpoints
# ═══════════════════════════════════════════════════════════════════

def get_checkpoint(slug, step):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT data FROM checkpoints WHERE slug=%s AND step=%s", (slug, step))
            row = cur.fetchone()
            if row:
                return json.loads(row['data']) if isinstance(row['data'], str) else row['data']
            return None

def save_checkpoint(slug, step, data):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO checkpoints (slug, step, data, created_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (slug, step) DO UPDATE SET
                    data=EXCLUDED.data, created_at=EXCLUDED.created_at
            """, (slug, step, json.dumps(data), datetime.now().isoformat()))

def clear_checkpoints(slug):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM checkpoints WHERE slug=%s", (slug,))

# Initialize database on import
try:
    if DATABASE_URL:
        init_db()
except Exception as e:
    print(f"⚠️ Erro ao inicializar banco: {e}")


# ═══════════════════════════════════════════════════════════════════
# Migrate from JSON (one-time)
# ═══════════════════════════════════════════════════════════════════

def migrate_from_json(data_dir):
    """Migrate data from JSON files to PostgreSQL (one-time use)."""
    data_dir = Path(data_dir)
    
    ideas_file = data_dir / 'ideas.json'
    if ideas_file.exists():
        with open(ideas_file) as f:
            ideas = json.load(f)
        for idea in ideas:
            save_idea(idea)
        print(f"✅ {len(ideas)} ideias migradas")
    
    history_file = data_dir / 'pipeline_history.json'
    if history_file.exists():
        with open(history_file) as f:
            history = json.load(f)
        for entry in history:
            save_pipeline_history(entry)
        print(f"✅ {len(history)} pipeline records migrados")
    
    verify_file = data_dir / 'verify_history.json'
    if verify_file.exists():
        with open(verify_file) as f:
            history = json.load(f)
        for entry in history:
            save_verify_history(entry)
        print(f"✅ {len(history)} verify records migrados")
    
    for key in ['pinterest_config', 'adcash_config', 'adcash_stats']:
        config_file = data_dir / f'{key}.json'
        if config_file.exists():
            with open(config_file) as f:
                config = json.load(f)
            save_config(key, config)
            print(f"✅ Config '{key}' migrada")
