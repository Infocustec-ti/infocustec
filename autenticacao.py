# autenticacao.py

import sqlite3
import bcrypt
import logging

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("autenticacao.log"),
        logging.StreamHandler()
    ]
)

# Função para autenticar o usuário
def authenticate(username, password):
    try:
        with sqlite3.connect('chamados.db') as conn:
            cursor = conn.cursor()

            # Busca o hash da senha armazenada no banco de dados
            cursor.execute("SELECT password FROM usuarios WHERE username=?", (username,))
            result = cursor.fetchone()

            if result:
                stored_password = result[0]
                # Garantir que stored_password é do tipo bytes
                if isinstance(stored_password, str):
                    stored_password = stored_password.encode('utf-8')

                # Verifica a senha usando bcrypt
                if bcrypt.checkpw(password.encode('utf-8'), stored_password):
                    logging.info(f"Usuário '{username}' autenticado com sucesso.")
                    return True
                else:
                    logging.warning(f"Senha incorreta para o usuário '{username}'.")
                    return False
            else:
                logging.warning(f"Usuário '{username}' não encontrado.")
                return False
    except Exception as e:
        logging.error(f"Erro na autenticação: {e}")
        return False

# Função para adicionar um novo usuário
def add_user(username, password, is_admin=False):
    try:
        with sqlite3.connect('chamados.db') as conn:
            cursor = conn.cursor()

            # Verifica se o usuário já existe
            cursor.execute("SELECT * FROM usuarios WHERE username=?", (username,))
            existing_user = cursor.fetchone()

            if existing_user:
                logging.warning(f"Usuário '{username}' já existe.")
                return False
            else:
                # Hashear a senha usando bcrypt
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                role = 'admin' if is_admin else 'user'
                cursor.execute(
                    "INSERT INTO usuarios (username, password, role) VALUES (?, ?, ?)",
                    (username, hashed_password, role)
                )
                conn.commit()
                logging.info(f"Usuário '{username}' criado com sucesso como {role}.")
                return True
    except Exception as e:
        logging.error(f"Erro ao adicionar usuário '{username}': {e}")
        return False

# Função para verificar se o usuário é administrador
def is_admin(username):
    try:
        with sqlite3.connect('chamados.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT role FROM usuarios WHERE username=?", (username,))
            user_role = cursor.fetchone()
            return user_role and user_role[0] == 'admin'
    except Exception as e:
        logging.error(f"Erro ao verificar função do usuário '{username}': {e}")
        return False

# Função para listar todos os usuários cadastrados
def list_users():
    try:
        with sqlite3.connect('chamados.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT username, role FROM usuarios")
            users = cursor.fetchall()
            return users
    except Exception as e:
        logging.error(f"Erro ao listar usuários: {e}")
        return []

# Função para alterar a senha de um usuário
def change_password(username, new_password):
    try:
        if not username or not new_password:
            raise ValueError("Usuário ou nova senha inválidos.")

        hashed_new_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())

        with sqlite3.connect('chamados.db') as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE usuarios SET password=? WHERE username=?",
                (hashed_new_password, username)
            )
            conn.commit()
            logging.info(f"Senha do usuário '{username}' alterada com sucesso.")
            return True
    except Exception as e:
        logging.error(f"Erro ao alterar a senha do usuário '{username}': {e}")
        return False

# Função para remover um usuário (apenas para administradores)
def remove_user(admin_username, target_username):
    if is_admin(admin_username):
        try:
            with sqlite3.connect('chamados.db') as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM usuarios WHERE username=?", (target_username,))
                conn.commit()
                logging.info(f"Usuário '{target_username}' removido com sucesso por '{admin_username}'.")
                return True
        except Exception as e:
            logging.error(f"Erro ao remover usuário '{target_username}': {e}")
            return False
    else:
        logging.warning(f"Permissão negada. Usuário '{admin_username}' não é administrador.")
        return False
