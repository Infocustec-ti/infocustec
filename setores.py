# setores.py
from sqlalchemy.orm import Session
from database import SessionLocal, Setor
import streamlit as st
import logging

# Função para adicionar um novo setor
def add_setor(nome_setor: str) -> bool:
    session: Session = SessionLocal()
    try:
        # Verifica se o setor já existe
        setor_existente = session.query(Setor).filter(Setor.nome_setor == nome_setor).first()
        if setor_existente:
            return False  # Setor já existe
        novo_setor = Setor(nome_setor=nome_setor)
        session.add(novo_setor)
        session.commit()
        logging.info(f"Setor '{nome_setor}' adicionado ao banco de dados.")
        return True
    except Exception as e:
        session.rollback()
        logging.error(f"Erro ao adicionar setor '{nome_setor}': {e}")
        st.error("Erro interno ao adicionar setor. Tente novamente mais tarde.")
        return False
    finally:
        session.close()

# Função para listar todos os setores cadastrados
def get_setores_list() -> list:
    session: Session = SessionLocal()
    try:
        setores = session.query(Setor.nome_setor).all()
        logging.info("Setores recuperados do banco de dados.")
        return [setor[0] for setor in setores]
    except Exception as e:
        logging.error(f"Erro ao recuperar setores: {e}")
        st.error("Erro interno ao recuperar setores. Tente novamente mais tarde.")
        return []
    finally:
        session.close()

# Função para remover um setor
def remove_setor(nome_setor: str) -> bool:
    session: Session = SessionLocal()
    try:
        setor = session.query(Setor).filter(Setor.nome_setor == nome_setor).first()
        if setor:
            session.delete(setor)
            session.commit()
            logging.info(f"Setor '{nome_setor}' removido do banco de dados.")
            return True
        else:
            return False  # Setor não encontrado
    except Exception as e:
        session.rollback()
        logging.error(f"Erro ao remover setor '{nome_setor}': {e}")
        st.error("Erro interno ao remover setor. Tente novamente mais tarde.")
        return False
    finally:
        session.close()

# Função para atualizar o nome de um setor
def update_setor(old_name: str, new_name: str) -> bool:
    session: Session = SessionLocal()
    try:
        setor = session.query(Setor).filter(Setor.nome_setor == old_name).first()
        if setor:
            # Verifica se o novo nome já existe
            setor_existente = session.query(Setor).filter(Setor.nome_setor == new_name).first()
            if setor_existente:
                st.warning(f"Setor '{new_name}' já está cadastrado.")
                logging.warning(f"Tentativa de atualizar setor para um nome já existente: {new_name}")
                return False
            setor.nome_setor = new_name
            session.commit()
            logging.info(f"Setor '{old_name}' atualizado para '{new_name}'.")
            return True
        else:
            return False  # Setor não encontrado
    except Exception as e:
        session.rollback()
        logging.error(f"Erro ao atualizar setor de '{old_name}' para '{new_name}': {e}")
        st.error("Erro interno ao atualizar setor. Tente novamente mais tarde.")
        return False
    finally:
        session.close()

# Função para inicializar alguns setores no banco de dados (se necessário)
def initialize_setores():
    setores_iniciais = [
        "Recepção"
    ]
    for setor in setores_iniciais:
        add_setor(setor)

# Função para exibir e gerenciar setores usando Streamlit
def manage_setores():
    st.subheader('Gerenciar Setores')

    action = st.selectbox('Selecione uma ação:', ['Listar Setores', 'Adicionar Setor', 'Editar Setor', 'Remover Setor'])

    if action == 'Listar Setores':
        setores_list = get_setores_list()
        if setores_list:
            st.write('Setores cadastrados:')
            for setor in setores_list:
                st.write(f"- {setor}")
        else:
            st.write('Nenhum setor cadastrado.')

    elif action == 'Adicionar Setor':
        nome_setor = st.text_input('Nome do Setor')
        if st.button('Adicionar'):
            if nome_setor:
                if add_setor(nome_setor):
                    st.success(f"Setor '{nome_setor}' adicionado com sucesso.")
                else:
                    st.warning(f"Setor '{nome_setor}' já está cadastrado.")
            else:
                st.error('Por favor, insira o nome do setor.')

    elif action == 'Editar Setor':
        setores_list = get_setores_list()
        if setores_list:
            old_name = st.selectbox('Selecione o setor para editar:', setores_list)
            new_name = st.text_input('Novo nome do setor', value=old_name)
            if st.button('Atualizar'):
                if new_name:
                    if update_setor(old_name, new_name):
                        st.success(f"Setor '{old_name}' atualizado para '{new_name}'.")
                    else:
                        st.error('Erro ao atualizar o setor ou o novo nome já está em uso.')
                else:
                    st.error('Por favor, insira o novo nome do setor.')
        else:
            st.write('Nenhum setor cadastrado para editar.')

    elif action == 'Remover Setor':
        setores_list = get_setores_list()
        if setores_list:
            nome_setor = st.selectbox('Selecione o setor para remover:', setores_list)
            if st.button('Remover'):
                if remove_setor(nome_setor):
                    st.success(f"Setor '{nome_setor}' removido com sucesso.")
                else:
                    st.error('Erro ao remover o setor.')
        else:
            st.write('Nenhum setor cadastrado para remover.')
