import os
import re
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def _clean_query(query):
    """Traduz a sintaxe do SQLite e converte tipos para o PostgreSQL de forma segura."""
    # 1. Substitui marcadores de parâmetro '?' por '%s'
    query = query.replace('?', '%s')
    
    # 2. Converte AUTOINCREMENT do SQLite para SERIAL do PostgreSQL
    query = re.sub(r"(?i)\binteger\s+primary\s+key\s+autoincrement\b", "SERIAL PRIMARY KEY", query)
    query = re.sub(r"(?i)\bautoincrement\b", "", query)
    
    # 3. Converte apelidos AS 'Nome' para AS "Nome"
    query = re.sub(r"(?i)\bas\s+'([^']+)'", r'AS "\1"', query)
    
    # 4. Ajusta relacionamentos de setor_id garantindo conversão ::text para o LOWER
    query = re.sub(
        r"(?i)\b(\w+)\.setor_id\s*=\s*s\.id\b",
        r"(\1.setor_id::text = s.id::text OR LOWER(\1.setor_id::text) = LOWER(s.nome))",
        query
    )
    return query

def _expand_keys(row_dict):
    """Garante compatibilidade de chaves maiúsculas/minúsculas."""
    expanded = {}
    for k, v in row_dict.items():
        if isinstance(k, str):
            expanded[k] = v
            expanded[k.lower()] = v
            expanded[k.upper()] = v
            expanded[k.capitalize()] = v
            expanded[k.title()] = v
            expanded[k.replace('_', ' ')] = v
            expanded[k.replace('_', ' ').title()] = v
        else:
            expanded[k] = v
    return expanded

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''CREATE TABLE IF NOT EXISTS setores (id SERIAL PRIMARY KEY, nome TEXT NOT NULL UNIQUE)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS impressoras (id SERIAL PRIMARY KEY, modelo TEXT NOT NULL, usuario_responsavel TEXT NOT NULL, setor_id INTEGER, tipo_conexao TEXT, endereco_rede TEXT, dados_acesso TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS suprimentos (id SERIAL PRIMARY KEY, categoria TEXT NOT NULL, cor_tipo TEXT NOT NULL, UNIQUE(categoria, cor_tipo))''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS estoque_suprimentos (id SERIAL PRIMARY KEY, suprimento_id INTEGER UNIQUE, quantidade INTEGER NOT NULL, obs_solicitacao TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS computadores (id SERIAL PRIMARY KEY, usuario TEXT NOT NULL, codigo_mesa TEXT, setor_id TEXT, processador TEXT, memoria_ram TEXT, armazenamento TEXT, observacoes TEXT, email_usuario TEXT, sistema_operacional TEXT, nome_equipamento TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS historico_manutencao (id SERIAL PRIMARY KEY, computador_id INTEGER, data_manutencao TEXT NOT NULL, descricao TEXT NOT NULL, tecnico TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS tecnicos (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, usuario TEXT NOT NULL UNIQUE, senha TEXT NOT NULL, perfil TEXT)''')
        
        cursor.execute("SELECT COUNT(*) FROM tecnicos")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO tecnicos (nome, usuario, senha, perfil) VALUES (%s, %s, %s, %s)", ("ADMINISTRADOR", "admin", "102030", "admin"))
        
        cursor.execute("ALTER TABLE computadores ADD COLUMN IF NOT EXISTS email_usuario TEXT")
        cursor.execute("ALTER TABLE computadores ADD COLUMN IF NOT EXISTS sistema_operacional TEXT")
        cursor.execute("ALTER TABLE computadores ADD COLUMN IF NOT EXISTS nome_equipamento TEXT")
        cursor.execute("ALTER TABLE suprimentos ADD COLUMN IF NOT EXISTS departamentos_uso TEXT")
        cursor.execute("ALTER TABLE estoque_suprimentos ADD COLUMN IF NOT EXISTS obs_solicitacao TEXT")
        cursor.execute("ALTER TABLE tecnicos ADD COLUMN IF NOT EXISTS perfil TEXT")
        
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def execute_query(query, params=()):
    query = _clean_query(query)
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def fetch_data(query, params=()):
    query = _clean_query(query)
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [_expand_keys(dict(row)) for row in rows]
    finally:
        cursor.close()
        conn.close()

def delete_data(query, params=()):
    execute_query(query, params)