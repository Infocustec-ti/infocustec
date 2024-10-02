import sqlite3
import bcrypt
import logging
import os

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("database.log"),
        logging.StreamHandler()
    ]
)

# Função para criar as tabelas de inventário, setores, UBSs, peças usadas e usuários, se elas não existirem
def create_tables():
    try:
        with sqlite3.connect('chamados.db') as conn:
            cursor = conn.cursor()

            # Tabela inventário
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS inventario (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero_patrimonio TEXT UNIQUE,
                    tipo TEXT,
                    marca TEXT,
                    modelo TEXT,
                    numero_serie TEXT,
                    status TEXT,
                    localizacao TEXT,
                    propria_locada TEXT,
                    setor TEXT
                )
            ''')

            # Tabela UBSs
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ubs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome_ubs TEXT UNIQUE
                )
            ''')

            # Tabela Setores
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS setores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome_setor TEXT UNIQUE
                )
            ''')

            # Tabela de histórico de manutenção
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS historico_manutencao (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero_patrimonio TEXT,
                    descricao TEXT,
                    data_manutencao TEXT,
                    FOREIGN KEY (numero_patrimonio) REFERENCES inventario(numero_patrimonio)
                )
            ''')

            # Tabela de chamados
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chamados (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    ubs TEXT NOT NULL,
                    setor TEXT NOT NULL,
                    tipo_defeito TEXT NOT NULL,
                    problema TEXT NOT NULL,
                    hora_abertura TEXT NOT NULL,
                    solucao TEXT,
                    hora_fechamento TEXT,
                    protocolo INTEGER UNIQUE NOT NULL,
                    machine TEXT,
                    patrimonio TEXT                )
            ''')

            # Tabela de peças usadas
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pecas_usadas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chamado_id INTEGER,
                    peca_nome TEXT,
                    data_uso TEXT,
                    FOREIGN KEY (chamado_id) REFERENCES chamados(id)
                )
            ''')

            # Tabela de usuários (incluindo a coluna 'role' para definir o tipo de usuário)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT,
                    role TEXT DEFAULT 'user'  -- Adicionando a coluna 'role'
                )
            ''')

            conn.commit()
            logging.info("Tabelas criadas ou já existentes verificadas com sucesso.")
    except sqlite3.Error as e:
        logging.error(f"Erro ao criar as tabelas: {e}")

# Função para verificar se o usuário admin já existe e, se não, criá-lo
def check_or_create_admin_user():
    try:
        with sqlite3.connect('chamados.db') as conn:
            cursor = conn.cursor()
            # Verificar se o usuário admin já existe
            cursor.execute("SELECT * FROM usuarios WHERE username=?", ('admin',))
            admin_user = cursor.fetchone()

            if not admin_user:
                # Solicitar senha para o usuário admin via terminal
                admin_password = os.getenv('ADMIN_PASSWORD')
                if not admin_password:
                    admin_password = input("Insira a senha para o usuário 'admin': ")

                # Hashear a senha usando bcrypt
                hashed_password = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt())
                cursor.execute("INSERT INTO usuarios (username, password, role) VALUES (?, ?, ?)", ('admin', hashed_password, 'admin'))
                conn.commit()
                logging.info("Usuário 'admin' criado com sucesso.")
                print("Usuário 'admin' criado com sucesso.")
            else:
                logging.info("Usuário 'admin' já existe.")
                print("Usuário 'admin' já existe.")
    except sqlite3.Error as e:
        logging.error(f"Erro ao verificar ou criar usuário admin: {e}")
        print(f"Erro ao verificar ou criar usuário admin: {e}")

# Função para adicionar uma UBS ao banco de dados
def add_ubs(nome_ubs):
    try:
        with sqlite3.connect('chamados.db') as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO ubs (nome_ubs) VALUES (?)", (nome_ubs,))
            conn.commit()
            logging.info(f"UBS '{nome_ubs}' adicionada ou já existente.")
    except sqlite3.Error as e:
        logging.error(f"Erro ao adicionar UBS: {e}")

# Função para adicionar um setor ao banco de dados
def add_setor(nome_setor):
    try:
        with sqlite3.connect('chamados.db') as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO setores (nome_setor) VALUES (?)", (nome_setor,))
            conn.commit()
            logging.info(f"Setor '{nome_setor}' adicionado ou já existente.")
    except sqlite3.Error as e:
        logging.error(f"Erro ao adicionar setor: {e}")

# Função para inicializar UBSs e setores no banco de dados
def initialize_ubs_setores():
    ubs_iniciais = [
        "UBS Arapari/Cabeceiras", "UBS Assunção", "UBS Flores", "UBS Baleia",
        "UBS Barrento", "UBS Bastioes", "UBS Bela Vista", "UBS Betânia",
        "UBS Boa Vista", "UBS Cacimbas", "UBS Calugi", "UBS Centro",
        "UBS Coqueiro", "UBS Cruzeiro/Maranhão", "UBS Deserto/Mangueira",
        "UBS Encruzilhadas", "UBS Estação", "UBS Fazendinha", "UBS Ipu/Mazagão",
        "UBS Jacaré", "UBS Ladeira", "UBS Lagoa da Cruz", "UBS Lagoa das Mercês",
        "UBS Livramento", "UBS Maceió", "UBS Madalenas", "UBS Marinheiros",
        "UBS Mourão", "UBS Mulatão", "UBS Picos", "UBS Salgado dos Pires",
        "UBS Sítio do Meio", "UBS Tabocal", "UBS Taboca", "UBS Vida Nova Vida Bela",
        "UBS Nova Aldeota", "UBS Violete", "UBS Violete II"
    ]

    setores_iniciais = [
        "Recepção", "Consultório Médico", "Farmácia", "Sala da Enfermeira",
        "Sala da Vacina", "Consultório Odontológico", "Sala de Administração"
    ]

    # Inicializar UBSs
    for ubs in ubs_iniciais:
        add_ubs(ubs)

    # Inicializar Setores
    for setor in setores_iniciais:
        add_setor(setor)

# Função para verificar se o usuário é administrador
def is_admin(username):
    try:
        with sqlite3.connect('chamados.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT role FROM usuarios WHERE username=?", (username,))
            user_role = cursor.fetchone()
            return user_role and user_role[0] == 'admin'
    except sqlite3.Error as e:
        logging.error(f"Erro ao verificar função do usuário: {e}")
        return False

# Inicialização do banco de dados ao rodar o script
if __name__ == "__main__":
    create_tables()
    initialize_ubs_setores()
    check_or_create_admin_user()
    logging.info("Banco de dados inicializado com sucesso.")
