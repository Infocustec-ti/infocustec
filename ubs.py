import os
import streamlit as st
from sqlalchemy.orm import Session
from database import SessionLocal, UBS
import logging

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("os500.log"),
        logging.StreamHandler()
    ]
)

# Função para adicionar uma nova UBS
def add_ubs(nome_ubs: str) -> bool:
    session: Session = SessionLocal()
    try:
        # Verifica se a UBS já existe
        setor_existente = session.query(UBS).filter(UBS.nome_ubs == nome_ubs).first()
        if setor_existente:
            logging.warning(f"UBS '{nome_ubs}' já está cadastrada.")
            return False
        nova_ubs = UBS(nome_ubs=nome_ubs)
        session.add(nova_ubs)
        session.commit()
        logging.info(f"UBS '{nome_ubs}' adicionada com sucesso.")
        return True
    except Exception as e:
        session.rollback()
        logging.error(f"Erro ao adicionar UBS '{nome_ubs}': {e}")
        st.error("Erro interno ao adicionar UBS. Tente novamente mais tarde.")
        return False
    finally:
        session.close()

# Função para listar todas as UBSs cadastradas
def get_ubs_list() -> list:
    session: Session = SessionLocal()
    try:
        ubs = session.query(UBS.nome_ubs).all()
        ubs_list = [item[0] for item in ubs]
        logging.info("UBSs recuperadas com sucesso.")
        return ubs_list
    except Exception as e:
        logging.error(f"Erro ao recuperar UBSs: {e}")
        st.error("Erro interno ao recuperar UBSs. Tente novamente mais tarde.")
        return []
    finally:
        session.close()

# Função para remover uma UBS
def remove_ubs(nome_ubs: str) -> bool:
    session: Session = SessionLocal()
    try:
        ubs = session.query(UBS).filter(UBS.nome_ubs == nome_ubs).first()
        if ubs:
            session.delete(ubs)
            session.commit()
            logging.info(f"UBS '{nome_ubs}' removida com sucesso.")
            return True
        else:
            logging.warning(f"UBS '{nome_ubs}' não encontrada para remoção.")
            return False
    except Exception as e:
        session.rollback()
        logging.error(f"Erro ao remover UBS '{nome_ubs}': {e}")
        st.error("Erro interno ao remover UBS. Tente novamente mais tarde.")
        return False
    finally:
        session.close()

# Função para atualizar o nome de uma UBS
def update_ubs(old_name: str, new_name: str) -> bool:
    session: Session = SessionLocal()
    try:
        # Verifica se o novo nome já existe
        ubs_existente = session.query(UBS).filter(UBS.nome_ubs == new_name).first()
        if ubs_existente:
            st.warning(f"UBS '{new_name}' já está cadastrada.")
            logging.warning(f"Tentativa de atualizar UBS para um nome já existente: {new_name}")
            return False

        ubs = session.query(UBS).filter(UBS.nome_ubs == old_name).first()
        if ubs:
            ubs.nome_ubs = new_name
            session.commit()
            logging.info(f"UBS '{old_name}' atualizada para '{new_name}'.")
            return True
        else:
            logging.error(f"UBS '{old_name}' não encontrada para atualização.")
            return False
    except Exception as e:
        session.rollback()
        logging.error(f"Erro ao atualizar UBS de '{old_name}' para '{new_name}': {e}")
        st.error("Erro interno ao atualizar UBS. Tente novamente mais tarde.")
        return False
    finally:
        session.close()

# Inicializar algumas UBSs no banco de dados
def initialize_ubs():
    # Lista de UBSs iniciais que queremos cadastrar
    ubs_iniciais = [
        "UBS Arapari/Cabeceiras", "UBS Assunçao", "UBS Flores", "UBS Baleia",
        "UBS Barrento", "UBS Bastioes", "UBS Bela Vista", "UBS Betania",
        "UBS Boa Vista", "UBS Cacimbas", "UBS Calugi", "UBS Centro",
        "UBS Coqueiro", "UBS Cruzeiro/Maranhao", "UBS Deserto/Mangueira",
        "UBS Encruzilhadas", "UBS Estaçao", "UBS Fazendinha", "UBS Ipu/Mazagao",
        "UBS Jacare", "UBS Ladeira", "UBS Lagoa da Cruz", "UBS Lagoa das Merces",
        "UBS Livramento", "UBS Maceio", "UBS Madalenas", "UBS Marinheiros",
        "UBS Mourao", "UBS Mulatao", "UBS Picos", "UBS Salgado dos Pires",
        "UBS Sitio do Meio", "UBS Tabocal", "UBS Taboca", "UBS Vida Nova Vida Bela",
        "UBS Nova Aldeota", "UBS Violete", "UBS Violete II"
    ]

    for ubs in ubs_iniciais:
        add_ubs(ubs)

# Função para exibir e gerenciar UBSs usando Streamlit
def manage_ubs():
    st.subheader('Gerenciar UBSs')

    action = st.selectbox('Selecione uma ação:', ['Listar UBSs', 'Adicionar UBS', 'Editar UBS', 'Remover UBS'])

    if action == 'Listar UBSs':
        ubs_list = get_ubs_list()
        if ubs_list:
            st.write('UBSs cadastradas:')
            for ubs in ubs_list:
                st.write(f"- {ubs}")
        else:
            st.write('Nenhuma UBS cadastrada.')

    elif action == 'Adicionar UBS':
        nome_ubs = st.text_input('Nome da UBS')
        if st.button('Adicionar'):
            if nome_ubs:
                if add_ubs(nome_ubs):
                    st.success(f"UBS '{nome_ubs}' adicionada com sucesso.")
                else:
                    st.warning(f"UBS '{nome_ubs}' já está cadastrada.")
            else:
                st.error('Por favor, insira o nome da UBS.')

    elif action == 'Editar UBS':
        ubs_list = get_ubs_list()
        if ubs_list:
            old_name = st.selectbox('Selecione a UBS para editar:', ubs_list)
            new_name = st.text_input('Novo nome da UBS', value=old_name)
            if st.button('Atualizar'):
                if new_name:
                    if update_ubs(old_name, new_name):
                        st.success(f"UBS '{old_name}' atualizada para '{new_name}'.")
                    else:
                        st.error('Erro ao atualizar a UBS.')
                else:
                    st.error('Por favor, insira o novo nome da UBS.')
        else:
            st.write('Nenhuma UBS cadastrada para editar.')

    elif action == 'Remover UBS':
        ubs_list = get_ubs_list()
        if ubs_list:
            nome_ubs = st.selectbox('Selecione a UBS para remover:', ubs_list)
            if st.button('Remover'):
                if remove_ubs(nome_ubs):
                    st.success(f"UBS '{nome_ubs}' removida com sucesso.")
                else:
                    st.error('Erro ao remover a UBS.')
        else:
            st.write('Nenhuma UBS cadastrada para remover.')

