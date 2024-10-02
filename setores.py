import sqlite3
import streamlit as st

# Função para criar a tabela de setores, caso ainda não exista
def create_setores_table():
    with sqlite3.connect('chamados.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS setores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_setor TEXT UNIQUE
            )
        ''')
        conn.commit()

# Função para adicionar um novo setor
def add_setor(nome_setor):
    with sqlite3.connect('chamados.db') as conn:
        cursor = conn.cursor()
        # Verifica se o setor já existe
        cursor.execute("SELECT nome_setor FROM setores WHERE nome_setor = ?", (nome_setor,))
        if cursor.fetchone() is None:
            cursor.execute("INSERT INTO setores (nome_setor) VALUES (?)", (nome_setor,))
            conn.commit()
            return True
        else:
            return False

# Função para listar todos os setores cadastrados
def get_setores_list():
    with sqlite3.connect('chamados.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT nome_setor FROM setores")
        setores_list = cursor.fetchall()
    return [setor[0] for setor in setores_list]

# Função para remover um setor
def remove_setor(nome_setor):
    with sqlite3.connect('chamados.db') as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM setores WHERE nome_setor = ?", (nome_setor,))
        conn.commit()
        return cursor.rowcount > 0

# Função para atualizar o nome de um setor
def update_setor(old_name, new_name):
    with sqlite3.connect('chamados.db') as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE setores SET nome_setor = ? WHERE nome_setor = ?", (new_name, old_name))
        conn.commit()
        return cursor.rowcount > 0

# Inicializar alguns setores no banco de dados
def initialize_setores():
    # Certifique-se de que a tabela setores está criada
    create_setores_table()

    # Lista de setores iniciais que queremos cadastrar
    setores_iniciais = [
        "Recepção", "Consultório médico", "Farmácia", "Sala da Enfermeira", 
        "Sala da vacina", "Consultório odontológico", "Sala administração"
    ]

    # Adicionar setores iniciais, se ainda não existirem
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
                        st.error('Erro ao atualizar o setor.')
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

# Inicializar os setores ao rodar o script
if __name__ == "__main__":
    initialize_setores()
    # Exibir setores cadastrados para verificação
    setores_list = get_setores_list()
    print("Setores cadastrados:")
    for setor in setores_list:
        print(setor)
