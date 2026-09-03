#!/usr/bin/env python3
"""Migra dados do dashboard de JSON para MySQL."""
import json
import os
import sys
from pathlib import Path

# Adicionar path do projeto
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import pymysql

DB_CONFIG = {
    'host': os.getenv('WP_DB_HOST', 'sql310.byetcluster.com'),
    'user': os.getenv('WP_DB_USER', '42799195_1'),
    'password': os.getenv('WP_DB_PASS', ''),
    'database': os.getenv('WP_DB_NAME', 'b442799195_wp909'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

DATA_DIR = Path(__file__).parent.parent / 'dashboard' / 'data'

def get_connection():
    return pymysql.connect(**DB_CONFIG)

def create_tables():
    """Cria as tabelas necessárias."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Tabela de ideias
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dashboard_ideas (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    idea_id INT UNIQUE,
                    title TEXT,
                    keyword TEXT,
                    category VARCHAR(100),
                    status VARCHAR(50),
                    created_at DATETIME,
                    cpm_estimate VARCHAR(50),
                    source VARCHAR(50),
                    INDEX idx_status (status),
                    INDEX idx_category (category)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            
            # Tabela de histórico do pipeline
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dashboard_pipeline_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    keyword TEXT,
                    article TEXT,
                    title TEXT,
                    image TEXT,
                    image_url TEXT,
                    post_url TEXT,
                    steps JSON,
                    completed_at DATETIME,
                    INDEX idx_completed (completed_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            
            # Tabela de verificação de artigos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dashboard_verify_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    filename TEXT,
                    score INT,
                    status VARCHAR(50),
                    issues_count INT,
                    warnings_count INT,
                    verified_at DATETIME,
                    INDEX idx_verified (verified_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            
            # Tabela de configurações
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dashboard_config (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    config_key VARCHAR(100) UNIQUE,
                    config_value JSON,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            
            # Tabela de checkpoints do pipeline
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dashboard_checkpoints (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    slug VARCHAR(200),
                    step VARCHAR(50),
                    data JSON,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_slug_step (slug, step)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            
        conn.commit()
        print("✅ Tabelas criadas com sucesso!")
    finally:
        conn.close()

def migrate_ideas():
    """Migra ideias de JSON para MySQL."""
    filepath = DATA_DIR / 'ideas.json'
    if not filepath.exists():
        print("⚠️  ideas.json não encontrado, pulando...")
        return
    
    with open(filepath) as f:
        ideas = json.load(f)
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            for idea in ideas:
                cursor.execute("""
                    INSERT INTO dashboard_ideas (idea_id, title, keyword, category, status, created_at, cpm_estimate, source)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        title = VALUES(title),
                        keyword = VALUES(keyword),
                        category = VALUES(category),
                        status = VALUES(status)
                """, (
                    idea.get('id'),
                    idea.get('title'),
                    idea.get('keyword'),
                    idea.get('category'),
                    idea.get('status'),
                    idea.get('created_at'),
                    idea.get('cpm_estimate'),
                    idea.get('source')
                ))
        conn.commit()
        print(f"✅ {len(ideas)} ideias migradas!")
    finally:
        conn.close()

def migrate_pipeline_history():
    """Migra histórico do pipeline de JSON para MySQL."""
    filepath = DATA_DIR / 'pipeline_history.json'
    if not filepath.exists():
        print("⚠️  pipeline_history.json não encontrado, pulando...")
        return
    
    with open(filepath) as f:
        history = json.load(f)
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            for entry in history:
                cursor.execute("""
                    INSERT INTO dashboard_pipeline_history (keyword, article, title, image, image_url, post_url, steps, completed_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    entry.get('keyword'),
                    entry.get('article'),
                    entry.get('title'),
                    entry.get('image'),
                    entry.get('image_url'),
                    entry.get('post_url'),
                    json.dumps(entry.get('steps', [])),
                    entry.get('completed_at')
                ))
        conn.commit()
        print(f"✅ {len(history)} registros de pipeline migrados!")
    finally:
        conn.close()

def migrate_verify_history():
    """Migra histórico de verificação de JSON para MySQL."""
    filepath = DATA_DIR / 'verify_history.json'
    if not filepath.exists():
        print("⚠️  verify_history.json não encontrado, pulando...")
        return
    
    with open(filepath) as f:
        history = json.load(f)
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            for entry in history:
                cursor.execute("""
                    INSERT INTO dashboard_verify_history (filename, score, status, issues_count, warnings_count, verified_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    entry.get('filename'),
                    entry.get('score'),
                    entry.get('status'),
                    entry.get('issues_count'),
                    entry.get('warnings_count'),
                    entry.get('verified_at')
                ))
        conn.commit()
        print(f"✅ {len(history)} registros de verificação migrados!")
    finally:
        conn.close()

def migrate_configs():
    """Migra configurações de JSON para MySQL."""
    config_files = {
        'pinterest_config': 'pinterest_config.json',
        'adcash_config': 'adcash_config.json',
        'adcash_stats': 'adcash_stats.json'
    }
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            for key, filename in config_files.items():
                filepath = DATA_DIR / filename
                if filepath.exists():
                    with open(filepath) as f:
                        config_data = json.load(f)
                    cursor.execute("""
                        INSERT INTO dashboard_config (config_key, config_value)
                        VALUES (%s, %s)
                        ON DUPLICATE KEY UPDATE config_value = VALUES(config_value)
                    """, (key, json.dumps(config_data)))
                    print(f"✅ Configuração '{key}' migrada!")
        conn.commit()
    finally:
        conn.close()

if __name__ == '__main__':
    print("🚀 Iniciando migração de dados para MySQL...\n")
    
    create_tables()
    print()
    
    migrate_ideas()
    migrate_pipeline_history()
    migrate_verify_history()
    migrate_configs()
    
    print("\n✅ Migração concluída com sucesso!")
    print("Os dados agora estão armazenados no MySQL e sobreviverão a deploys/restarts.")
