# database.py
import os
import sys
import logging
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import bcrypt

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

# Configuração do banco de dados PostgreSQL usando variáveis de ambiente
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
    numero_patrimonio = Column(String(50), unique=True, nullable=False, index=True)
    tipo = Column(String(50), nullable=False)
    marca = Column(String(50), nullable=False)
    modelo = Column(String(50), nullable=False)
    numero_serie = Column(String(50), nullable=True)
    status = Column(String(20), nullable=False)
    localizacao = Column(String(100), nullable=False)
    propria_locada = Column(String(20), nullable=False)
    setor = Column(String(50), nullable=False)
    historico = relationship(
        "HistoricoManutencao",
        back_populates="inventario",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Inventario(numero_patrimonio='{self.numero_patrimonio}', tipo='{self.tipo}')>"

class UBS(Base):
    __tablename__ = 'ubs'
    id = Column(Integer, primary_key=True, index=True)
    nome_ubs = Column(String(100), unique=True, nullable=False, index=True)

    def __repr__(self):
        return f"<UBS(nome_ubs='{self.nome_ubs}')>"

class Setor(Base):
    __tablename__ = 'setores'
    id = Column(Integer, primary_key=True, index=True)
    nome_setor = Column(String(100), unique=True, nullable=False, index=True)

    def __repr__(self):
        return f"<Setor(nome_setor='{self.nome_setor}')>"

class HistoricoManutencao(Base):
    __tablename__ = 'historico_manutencao'
    id = Column(Integer, primary_key=True, index=True)
    numero_patrimonio = Column(String(50), ForeignKey('inventario.numero_patrimonio'), nullable=False)
    descricao = Column(String(500), nullable=False)
    data_manutencao = Column(DateTime, nullable=False)
    inventario = relationship("Inventario", back_populates="historico")

    def __repr__(self):
        return f"<HistoricoManutencao(numero_patrimonio='{self.numero_patrimonio}', data_manutencao='{self.data_manutencao}')>"

class Chamado(Base):
    __tablename__ = 'chamados'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False)
    ubs = Column(String(100), nullable=False)
    setor = Column(String(100), nullable=False)
    tipo_defeito = Column(String(100), nullable=False)
    problema = Column(String(500), nullable=False)
    hora_abertura = Column(DateTime, nullable=False)
    solucao = Column(String(500))
    hora_fechamento = Column(DateTime)
    protocolo = Column(Integer, unique=True, nullable=False, index=True)
    machine = Column(String(100))
    patrimonio = Column(String(50))
    pecas_usadas = relationship(
        "PecaUsada",
        back_populates="chamado",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Chamado(protocolo='{self.protocolo}', username='{self.username}')>"

class PecaUsada(Base):
    __tablename__ = 'peca_usada'
    id = Column(Integer, primary_key=True, index=True)
    chamado_id = Column(Integer, ForeignKey('chamados.id'), nullable=False)
    peca_nome = Column(String(100), nullable=False)
    data_uso = Column(DateTime, nullable=False)
    chamado = relationship("Chamado", back_populates="pecas_usadas")

    def __repr__(self):
        return f"<PecaUsada(peca_nome='{self.peca_nome}', chamado_id='{self.chamado_id}')>"

class Usuario(Base):
    __tablename__ = 'usuarios'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(60), nullable=False)
    role = Column(String(10), default='user', nullable=False)

    def __repr__(self):
        return f"<Usuario(username='{self.username}', role='{self.role}')>"

# Função para criar as tabelas no banco de dados
def create_tables():
    try:
        Base.metadata.create_all(bind=engine, checkfirst=True)
        logging.info("Tabelas criadas ou já existentes verificadas com sucesso.")
    except Exception as e:
        logging.error(f"Erro ao criar as tabelas: {e}")
        raise

# Função para adicionar uma UBS ao banco de dados
def add_ubs(nome_ubs):
    if not nome_ubs.strip():
        logging.error("Nome da UBS não pode ser vazio.")
        return
    with SessionLocal() as session:
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
            logging.error(f"Erro ao adicionar UBS '{nome_ubs}': {e}")

# Função para adicionar um setor ao banco de dados
def add_setor(nome_setor):
    if not nome_setor.strip():
        logging.error("Nome do setor não pode ser vazio.")
        return
    with SessionLocal() as session:
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
            logging.error(f"Erro ao adicionar setor '{nome_setor}': {e}")

# Função para inicializar UBSs e setores no banco de dados
def initialize_ubs_setores():
    ubs_iniciais = [
        "UBS Baleia",
        "UBS Arapari/Cabeceiras",
        # ... adicione mais UBSs conforme necessário
    ]

    setores_iniciais = [
        "Recepção",
        "TI",
        # ... adicione mais setores conforme necessário
    ]

    with SessionLocal() as session:
        ubs_existentes = {ubs.nome_ubs for ubs in session.query(UBS).all()}
        novos_ubs = set(ubs_iniciais) - ubs_existentes
        for ubs in novos_ubs:
            add_ubs(ubs)

        setores_existentes = {setor.nome_setor for setor in session.query(Setor).all()}
        novos_setores = set(setores_iniciais) - setores_existentes
        for setor in novos_setores:
            add_setor(setor)

# Função para criar um novo usuário
def create_user(username, password, role='user'):
    if not username.strip() or not password:
        logging.error("Username e senha não podem ser vazios.")
        return
    with SessionLocal() as session:
        try:
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            novo_usuario = Usuario(username=username, password=hashed_password.decode('utf-8'), role=role)
            session.add(novo_usuario)
            session.commit()
            logging.info(f"Usuário '{username}' criado com sucesso com o papel '{role}'.")
        except Exception as e:
            session.rollback()
            logging.error(f"Erro ao criar usuário '{username}': {e}")

# Função para verificar e criar o usuário admin
def check_or_create_admin_user():
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin")
    if not admin_username.strip() or not admin_password:
        logging.error("ADMIN_USERNAME e ADMIN_PASSWORD não podem ser vazios.")
        return

    with SessionLocal() as session:
        try:
            usuario = session.query(Usuario).filter(Usuario.username == admin_username).first()
            if not usuario:
                create_user(admin_username, admin_password, 'admin')
            else:
                if not bcrypt.checkpw(admin_password.encode('utf-8'), usuario.password.encode('utf-8')):
                    hashed_password = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt())
                    usuario.password = hashed_password.decode('utf-8')
                    usuario.role = 'admin'
                    session.commit()
                    logging.info(f"Senha do usuário admin '{admin_username}' atualizada com hash bcrypt.")
                else:
                    logging.info(f"Usuário admin '{admin_username}' já existe com senha hashada.")
        except Exception as e:
            session.rollback()
            logging.error(f"Erro ao verificar/criar usuário admin: {e}")
