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

        # --- Tabelas que antes eram criadas dentro das telas do app.py ---
        cursor.execute('''CREATE TABLE IF NOT EXISTS historico_saidas (id SERIAL PRIMARY KEY, item TEXT, quantidade INTEGER, departamento TEXT, data_saida TIMESTAMP DEFAULT CURRENT_TIMESTAMP, observacao TEXT DEFAULT '')''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS estoque_perifericos (id SERIAL PRIMARY KEY, item TEXT NOT NULL UNIQUE, qtd_atual INTEGER DEFAULT 0, qtd_minima INTEGER DEFAULT 0)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS laptops (id SERIAL PRIMARY KEY, nome_pc TEXT, modelo TEXT NOT NULL, service_tag TEXT, patrimonio TEXT, responsavel TEXT NOT NULL, localizacao TEXT, data_entrega TEXT, senha_sistema TEXT, senha_bios TEXT, usuario_ksc TEXT, senha_kaspersky TEXT, senha_adm TEXT, observacoes TEXT, status TEXT DEFAULT '🟢 EM USO')''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS fluxo_rh (id SERIAL PRIMARY KEY, colaborador TEXT NOT NULL, tipo TEXT NOT NULL, setor TEXT NOT NULL, data_evento TEXT, t1_ok INTEGER DEFAULT 0, t2_ok INTEGER DEFAULT 0, t3_ok INTEGER DEFAULT 0, t4_ok INTEGER DEFAULT 0)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS emprestimos (id SERIAL PRIMARY KEY, usuario TEXT NOT NULL, email TEXT, item TEXT NOT NULL, modelo TEXT, service_tag TEXT, lacre TEXT, patrimonio TEXT, acessorios TEXT, data_retirada TEXT NOT NULL, data_prevista TEXT, data_devolucao TEXT, status TEXT DEFAULT 'PENDENTE')''')

        # Colunas adicionadas ao longo do tempo (idempotente em bancos antigos)
        colunas_extras = {
            "historico_saidas": ["data_saida TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "observacao TEXT DEFAULT ''"],
            "computadores": ["sistema_operacional TEXT", "nome_equipamento TEXT"],
            "laptops": ["nome_pc TEXT", "data_entrega TEXT", "senha_sistema TEXT", "senha_bios TEXT", "usuario_ksc TEXT", "senha_kaspersky TEXT", "senha_adm TEXT", "observacoes TEXT"],
            "fluxo_rh": ["matricula TEXT", "ramal TEXT", "usuario_totvs TEXT", "senha_totvs TEXT", "user_ad TEXT", "senha_ad TEXT", "user_email TEXT", "senha_email TEXT", "user_office TEXT", "senha_office TEXT", "observacoes TEXT", "data_conclusao TEXT"],
            "emprestimos": ["modelo TEXT", "service_tag TEXT", "lacre TEXT", "patrimonio TEXT", "email TEXT", "acessorios TEXT"],
        }
        for tabela, colunas in colunas_extras.items():
            for coluna in colunas:
                cursor.execute(f"ALTER TABLE {tabela} ADD COLUMN IF NOT EXISTS {coluna}")

        # Itens básicos de periféricos (somente se a tabela estiver vazia)
        cursor.execute("SELECT COUNT(*) FROM estoque_perifericos")
        if cursor.fetchone()[0] == 0:
            itens_iniciais = [("Monitor", 0, 2), ("Teclado", 0, 5), ("Mouse", 0, 5), ("Telefone Fixo", 0, 2), ("Telefone Sem Fio", 0, 2), ("Headset", 0, 3)]
            for item, qtd, minimo in itens_iniciais:
                cursor.execute("INSERT INTO estoque_perifericos (item, qtd_atual, qtd_minima) VALUES (%s, %s, %s) ON CONFLICT (item) DO NOTHING", (item, qtd, minimo))
        
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