import sqlite3

DB_NAME = "impressoras.db"

def init_db():
    """Inicializa o banco de dados e cria as tabelas se não existirem."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS setores (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL UNIQUE)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS impressoras (id INTEGER PRIMARY KEY AUTOINCREMENT, modelo TEXT NOT NULL, usuario_responsavel TEXT NOT NULL, setor_id INTEGER, tipo_conexao TEXT, endereco_rede TEXT, dados_acesso TEXT, FOREIGN KEY (setor_id) REFERENCES setores(id))''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS suprimentos (id INTEGER PRIMARY KEY AUTOINCREMENT, categoria TEXT NOT NULL, cor_tipo TEXT NOT NULL, UNIQUE(categoria, cor_tipo))''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS estoque_suprimentos (id INTEGER PRIMARY KEY AUTOINCREMENT, suprimento_id INTEGER UNIQUE, quantidade INTEGER NOT NULL, FOREIGN KEY (suprimento_id) REFERENCES suprimentos(id))''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS computadores (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT NOT NULL, codigo_mesa TEXT, setor_id INTEGER, processador TEXT, memoria_ram TEXT, armazenamento TEXT, observacoes TEXT, FOREIGN KEY (setor_id) REFERENCES setores(id))''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS historico_manutencao (id INTEGER PRIMARY KEY AUTOINCREMENT, computador_id INTEGER, data_manutencao TEXT NOT NULL, descricao TEXT NOT NULL, tecnico TEXT, FOREIGN KEY (computador_id) REFERENCES computadores(id))''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS tecnicos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, usuario TEXT NOT NULL UNIQUE, senha TEXT NOT NULL)''')
    
    cursor.execute("SELECT COUNT(*) FROM tecnicos")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO tecnicos (nome, usuario, senha) VALUES (?, ?, ?)", ("ADMINISTRADOR", "admin", "102030"))
    
    # --- ATUALIZAÇÕES DE COLUNAS ---
    try: cursor.execute("ALTER TABLE computadores ADD COLUMN email_usuario TEXT")
    except sqlite3.OperationalError: pass

    # NOVA COLUNA: Departamentos que usam o suprimento
    try: cursor.execute("ALTER TABLE suprimentos ADD COLUMN departamentos_uso TEXT")
    except sqlite3.OperationalError: pass
    
    conn.commit()
    conn.close()

def execute_query(query, params=()):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    conn.close()

def fetch_data(query, params=()):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    result = [dict(row) for row in rows]
    conn.close()
    return result

def delete_data(query, params=()):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    conn.close()