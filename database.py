import os
import bcrypt
import logging
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import streamlit as st

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("database.log"),
        logging.StreamHandler()
    ]
)

# Configuração do banco de dados PostgreSQL (Supabase) usando secrets no Streamlit ou variáveis de ambiente
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logging.error("DATABASE_URL não está definido nas variáveis de ambiente.")
    raise ValueError("DATABASE_URL não está definido nas variáveis de ambiente.")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Definição dos modelos ORM
class Inventario(Base):
    __tablename__ = 'inventario'
    id = Column(Integer, primary_key=True, index=True)
    numero_patrimonio = Column(String, unique=True, nullable=False)
    tipo = Column(String, nullable=False)
    marca = Column(String, nullable=False)
    modelo = Column(String, nullable=False)
    numero_serie = Column(String, nullable=False)
    status = Column(String, nullable=False)
    localizacao = Column(String, nullable=False)
    propria_locada = Column(String, nullable=False)
    setor = Column(String, nullable=False)
    historico = relationship("HistoricoManutencao", back_populates="inventario")

class UBS(Base):
    __tablename__ = 'ubs'
    id = Column(Integer, primary_key=True, index=True)
    nome_ubs = Column(String, unique=True, nullable=False)

class Setor(Base):
    __tablename__ = 'setores'
    id = Column(Integer, primary_key=True, index=True)
    nome_setor = Column(String, unique=True, nullable=False)

class HistoricoManutencao(Base):
    __tablename__ = 'historico_manutencao'
    id = Column(Integer, primary_key=True, index=True)
    numero_patrimonio = Column(String, ForeignKey('inventario.numero_patrimonio'), nullable=False)
    descricao = Column(String, nullable=False)
    data_manutencao = Column(String, nullable=False)
    inventario = relationship("Inventario", back_populates="historico")

class Chamado(Base):
    __tablename__ = 'chamados'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False)
    ubs = Column(String, nullable=False)
    setor = Column(String, nullable=False)
    tipo_defeito = Column(String, nullable=False)
    problema = Column(String, nullable=False)
    hora_abertura = Column(String, nullable=False)
    solucao = Column(String)
    hora_fechamento = Column(String)
    protocolo = Column(Integer, unique=True, nullable=False)
    machine = Column(String)
    patrimonio = Column(String)
    pecas_usadas = relationship("PecaUsada", back_populates="chamado")

class PecaUsada(Base):
    __tablename__ = 'pecas_usadas'
    id = Column(Integer, primary_key=True, index=True)
    chamado_id = Column(Integer, ForeignKey('chamados.id'), nullable=False)
    peca_nome = Column(String, nullable=False)
    data_uso = Column(String, nullable=False)
    chamado = relationship("Chamado", back_populates="pecas_usadas")

class Usuario(Base):
    __tablename__ = 'usuarios'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)  # Definindo tamanho máximo
    password = Column(String(128), nullable=False)  # Definindo tamanho máximo para senha criptografada
    role = Column(String(10), default='user', nullable=False)

# Função para criar as tabelas no banco de dados
# Função para criar as tabelas no banco de dados
def create_tables():
    try:
        Base.metadata.create_all(bind=engine)
        logging.info("Tabelas criadas ou já existentes verificadas com sucesso.")
    except Exception as e:
        logging.error(f"Erro ao criar as tabelas: {e}")
        print(f"Erro ao criar as tabelas: {e}")
        raise  # Relevanta o erro para parar a execução do sistema caso falhe
# Função para adicionar uma UBS ao banco de dados
# Função para adicionar uma UBS ao banco de dados
def add_ubs(nome_ubs):
    session = SessionLocal()
    try:
        ubs = session.query(UBS).filter(UBS.nome_ubs == nome_ubs).first()
        if not ubs:
            novo_ubs = UBS(nome_ubs=nome_ubs)
            session.add(novo_ubs)
            session.commit()
            logging.info(f"UBS '{nome_ubs}' adicionada com sucesso.")
        else:
            logging.info(f"UBS '{nome_ubs}' já existente.")
    except Exception as e:
        session.rollback()
        logging.error(f"Erro ao adicionar UBS: {e}")
    finally:
        session.close()

# Função para adicionar um setor ao banco de dados
def add_setor(nome_setor):
    session = SessionLocal()
    try:
        setor = session.query(Setor).filter(Setor.nome_setor == nome_setor).first()
        if not setor:
            novo_setor = Setor(nome_setor=nome_setor)
            session.add(novo_setor)
            session.commit()
            logging.info(f"Setor '{nome_setor}' adicionado com sucesso.")
        else:
            logging.info(f"Setor '{nome_setor}' já existente.")
    except Exception as e:
        session.rollback()
        logging.error(f"Erro ao adicionar setor: {e}")
    finally:
        session.close()

# Função para inicializar UBSs e setores no banco de dados
def initialize_ubs_setores():
    ubs_iniciais = [
        "UBS Arapari/Cabeceiras", "UBS Assunção", "UBS Flores", "UBS Baleia",
        # ... adicione mais UBSs
    ]

    setores_iniciais = [
        "Recepção", "Consultório Médico", "Farmácia", "Sala da Enfermeira",
        "Sala da Vacina", "Consultório Odontológico", "Sala de Administração"
    ]

    for ubs in ubs_iniciais:
        add_ubs(ubs)

    for setor in setores_iniciais:
        add_setor(setor)

def is_admin(username):
    session = SessionLocal()
    try:
        usuario = session.query(Usuario).filter(Usuario.username == username).first()
        if usuario:
            return usuario.role == 'admin'
        else:
            logging.warning(f"Usuário '{username}' não encontrado.")
            return False
    except Exception as e:
        logging.error(f"Erro ao verificar função do usuário: {e}")
        return False
    finally:
        session.close()

# Função para criar um usuário
def create_user(username, password, role='user'):
    session = SessionLocal()
    try:
        usuario = session.query(Usuario).filter(Usuario.username == username).first()
        if not usuario:
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            novo_usuario = Usuario(username=username, password=hashed_password, role=role)
            session.add(novo_usuario)
            session.commit()
            logging.info(f"Usuário '{username}' criado com sucesso.")
            return True
        else:
            logging.warning(f"Falha ao criar usuário '{username}': já existe.")
            return False
    except Exception as e:
        session.rollback()
        logging.error(f"Erro ao criar usuário '{username}': {e}")
        return False
    finally:
        session.close()

# Função para verificar e criar o usuário admin
def check_or_create_admin_user():
    if not create_user('admin', 'admin', 'admin'):
        logging.info("Usuário 'admin' já existe.")

# Inicialização do banco de dados ao rodar o script
if __name__ == "__main__":
    create_tables()
    initialize_ubs_setores()
    check_or_create_admin_user()
    logging.info("Banco de dados inicializado com sucesso.")
