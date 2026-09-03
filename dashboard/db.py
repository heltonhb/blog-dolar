#!/usr/bin/env python3
"""Módulo de armazenamento SQLite para o dashboard.
Substitui arquivos JSON por banco SQLite local.
Dados sobrevivem a deploys mas não a restarts (aceitável para dashboard)."""
import json
import sqlite3
import os
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager

DB_PATH = Path(os.environ.get('DASHBOARD_DB_PATH', 
    Path(__file__).parent.parent / 'dashboard' / 'data' / 'dashboard.db'))

def get_db_path():
    """Retorna o caminho do banco SQLite."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return str(DB_PATH)

@contextmanager
def get_conn():
    """Context manager para conexão SQLite."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Cria as tabelas necessárias."""
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS ideas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT,
                article TEXT,
                title TEXT,
                image TEXT,
                image_url TEXT,
                post_url TEXT,
                steps TEXT,
                completed_at TEXT
            );
            
            CREATE TABLE IF NOT EXISTS verify_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                score INTEGER,
                status TEXT,
                issues_count INTEGER,
                warnings_count INTEGER,
                verified_at TEXT
            );
            
            CREATE TABLE IF NOT EXISTS config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_key TEXT UNIQUE,
                config_value TEXT,
                updated_at TEXT
            );
            
            CREATE TABLE IF NOT EXISTS checkpoints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT,
                step TEXT,
                data TEXT,
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
    """Retorna ideias do banco."""
    with get_conn() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM ideas WHERE status=? ORDER BY created_at DESC LIMIT ?",
                (status, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM ideas ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

def save_idea(idea):
    """Salva uma ideia no banco."""
    with get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO ideas (idea_id, title, keyword, category, status, created_at, cpm_estimate, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            idea.get('id'),
            idea.get('title'),
            idea.get('keyword'),
            idea.get('category'),
            idea.get('status', 'pending'),
            idea.get('created_at', datetime.now().isoformat()),
            idea.get('cpm_estimate'),
            idea.get('source')
        ))

def update_idea_status(idea_id, status):
    """Atualiza o status de uma ideia."""
    with get_conn() as conn:
        conn.execute("UPDATE ideas SET status=? WHERE idea_id=?", (status, idea_id))

# ═══════════════════════════════════════════════════════════════════
# Pipeline History
# ═══════════════════════════════════════════════════════════════════

def get_pipeline_history(limit=50):
    """Retorna histórico do pipeline."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM pipeline_history ORDER BY completed_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d['steps'] = json.loads(d['steps']) if d['steps'] else []
            result.append(d)
        return result

def save_pipeline_history(entry):
    """Salva entrada no histórico do pipeline."""
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO pipeline_history (keyword, article, title, image, image_url, post_url, steps, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.get('keyword'),
            entry.get('article'),
            entry.get('title'),
            entry.get('image'),
            entry.get('image_url'),
            entry.get('post_url'),
            json.dumps(entry.get('steps', [])),
            entry.get('completed_at', datetime.now().isoformat())
        ))

# ═══════════════════════════════════════════════════════════════════
# Verify History
# ═══════════════════════════════════════════════════════════════════

def get_verify_history(limit=50):
    """Retorna histórico de verificação."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM verify_history ORDER BY verified_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

def save_verify_history(entry):
    """Salva entrada de verificação."""
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO verify_history (filename, score, status, issues_count, warnings_count, verified_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            entry.get('filename'),
            entry.get('score'),
            entry.get('status'),
            entry.get('issues_count'),
            entry.get('warnings_count'),
            entry.get('verified_at', datetime.now().isoformat())
        ))

# ═══════════════════════════════════════════════════════════════════
# Config
# ═══════════════════════════════════════════════════════════════════

def get_config(key, default=None):
    """Retorna configuração do banco."""
    with get_conn() as conn:
        row = conn.execute("SELECT config_value FROM config WHERE config_key=?", (key,)).fetchone()
        if row:
            return json.loads(row['config_value'])
        return default

def save_config(key, value):
    """Salva configuração no banco."""
    with get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO config (config_key, config_value, updated_at)
            VALUES (?, ?, ?)
        """, (key, json.dumps(value), datetime.now().isoformat()))

# ═══════════════════════════════════════════════════════════════════
# Checkpoints
# ═══════════════════════════════════════════════════════════════════

def get_checkpoint(slug, step):
    """Retorna checkpoint do pipeline."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT data FROM checkpoints WHERE slug=? AND step=?",
            (slug, step)
        ).fetchone()
        if row:
            return json.loads(row['data'])
        return None

def save_checkpoint(slug, step, data):
    """Salva checkpoint do pipeline."""
    with get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO checkpoints (slug, step, data, created_at)
            VALUES (?, ?, ?, ?)
        """, (slug, step, json.dumps(data), datetime.now().isoformat()))

def clear_checkpoints(slug):
    """Remove checkpoints de um slug."""
    with get_conn() as conn:
        conn.execute("DELETE FROM checkpoints WHERE slug=?", (slug,))

# ═══════════════════════════════════════════════════════════════════
# Migrate from JSON
# ═══════════════════════════════════════════════════════════════════

def migrate_from_json(data_dir):
    """Migra dados de arquivos JSON para SQLite."""
    data_dir = Path(data_dir)
    
    # Migrate ideas
    ideas_file = data_dir / 'ideas.json'
    if ideas_file.exists():
        with open(ideas_file) as f:
            ideas = json.load(f)
        for idea in ideas:
            save_idea(idea)
        print(f"✅ {len(ideas)} ideias migradas")
    
    # Migrate pipeline history
    history_file = data_dir / 'pipeline_history.json'
    if history_file.exists():
        with open(history_file) as f:
            history = json.load(f)
        for entry in history:
            save_pipeline_history(entry)
        print(f"✅ {len(history)} registros de pipeline migrados")
    
    # Migrate verify history
    verify_file = data_dir / 'verify_history.json'
    if verify_file.exists():
        with open(verify_file) as f:
            history = json.load(f)
        for entry in history:
            save_verify_history(entry)
        print(f"✅ {len(history)} registros de verificação migrados")
    
    # Migrate configs
    for key in ['pinterest_config', 'adcash_config', 'adcash_stats']:
        config_file = data_dir / f'{key}.json'
        if config_file.exists():
            with open(config_file) as f:
                config = json.load(f)
            save_config(key, config)
            print(f"✅ Config '{key}' migrada")

# Initialize database on import
init_db()
