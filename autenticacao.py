# autenticacao.py

import bcrypt
import logging
from sqlalchemy.orm import Session
from database import SessionLocal, Usuario

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
def authenticate(username: str, password: str) -> bool:
    session: Session = SessionLocal()
    try:
        user = session.query(Usuario).filter(Usuario.username == username).first()
        if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            logging.info(f"Autenticação bem-sucedida para usuário '{username}'.")
            return True
        else:
            logging.warning(f"Falha na autenticação para usuário '{username}'.")
            return False
    except Exception as e:
        logging.error(f"Erro na autenticação: {e}")
        return False
    finally:
        session.close()

# Função para adicionar um novo usuário
def add_user(username: str, password: str, is_admin: bool = False) -> bool:
    session: Session = SessionLocal()
    try:
        existing_user = session.query(Usuario).filter(Usuario.username == username).first()
        if existing_user:
            logging.warning(f"Falha ao criar usuário '{username}': já existe.")
            return False
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        role = 'admin' if is_admin else 'user'
        new_user = Usuario(username=username, password=hashed_password, role=role)
        session.add(new_user)
        session.commit()
        logging.info(f"Usuário '{username}' criado com sucesso como '{role}'.")
        return True
    except Exception as e:
        session.rollback()
        logging.error(f"Erro ao adicionar usuário '{username}': {e}")
        return False
    finally:
        session.close()

# Função para verificar se o usuário é administrador
def is_admin(username: str) -> bool:
    session: Session = SessionLocal()
    try:
        user = session.query(Usuario).filter(Usuario.username == username).first()
        if user and user.role == 'admin':
            logging.info(f"Usuário '{username}' é um administrador.")
            return True
        else:
            logging.info(f"Usuário '{username}' não é um administrador.")
            return False
    except Exception as e:
        logging.error(f"Erro ao verificar função do usuário '{username}': {e}")
        return False
    finally:
        session.close()

# Função para listar todos os usuários cadastrados
def list_users():
    session: Session = SessionLocal()
    try:
        users = session.query(Usuario.username, Usuario.role).all()
        logging.info("Lista de usuários obtida com sucesso.")
        return users
    except Exception as e:
        logging.error(f"Erro ao listar usuários: {e}")
        return []
    finally:
        session.close()

# Função para alterar a senha de um usuário
def change_password(username: str, new_password: str) -> bool:
    session: Session = SessionLocal()
    try:
        user = session.query(Usuario).filter(Usuario.username == username).first()
        if user and bcrypt.checkpw(old_password.encode('utf-8'), user.password.encode('utf-8')):
            hashed_new_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            user.password = hashed_new_password
            session.commit()
            logging.info(f"Senha do usuário '{username}' alterada com sucesso.")
            return True
        else:
            logging.warning(f"Falha na alteração da senha para usuário '{username}': autenticação falhou.")
            return False
    except Exception as e:
        session.rollback()
        logging.error(f"Erro ao alterar a senha do usuário '{username}': {e}")
        return False
    finally:
        session.close()

# Função para remover um usuário (apenas para administradores)
def remove_user(admin_username: str, target_username: str) -> bool:
    session: Session = SessionLocal()
    try:
        admin_user = session.query(Usuario).filter(Usuario.username == admin_username).first()
        if not admin_user or admin_user.role != 'admin':
            logging.warning(f"Permissão negada para remover usuário '{target_username}' por '{admin_username}'.")
            return False
        
        target_user = session.query(Usuario).filter(Usuario.username == target_username).first()
        if not target_user:
            logging.warning(f"Usuário '{target_username}' não encontrado para remoção.")
            return False
        
        session.delete(target_user)
        session.commit()
        logging.info(f"Usuário '{target_username}' removido com sucesso por '{admin_username}'.")
        return True
    except Exception as e:
        session.rollback()
        logging.error(f"Erro ao remover usuário '{target_username}': {e}")
        return False
    finally:
        session.close()
