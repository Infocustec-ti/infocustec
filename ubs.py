import sqlite3
import streamlit as st

# Função para criar a tabela de UBS, caso ainda não exista
def create_ubs_table():
    with sqlite3.connect('chamados.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ubs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_ubs TEXT UNIQUE
            )
        ''')
        conn.commit()

# Função para adicionar uma nova UBS
def add_ubs(nome_ubs):
    with sqlite3.connect('chamados.db') as conn:
        cursor = conn.cursor()
        try:
            # Verifica se a UBS já existe
            cursor.execute("INSERT OR IGNORE INTO ubs (nome_ubs) VALUES (?)", (nome_ubs,))
            conn.commit()
            if cursor.rowcount == 0:
                # Se não houve alteração, significa que a UBS já existe
                return False
            return True
        except sqlite3.IntegrityError:
            return False

# Função para listar todas as UBSs cadastradas
def get_ubs_list():
    with sqlite3.connect('chamados.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT nome_ubs FROM ubs")
        ubs_list = cursor.fetchall()
    return [ubs[0] for ubs in ubs_list]

# Função para remover uma UBS
def remove_ubs(nome_ubs):
    with sqlite3.connect('chamados.db') as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ubs WHERE nome_ubs = ?", (nome_ubs,))
        conn.commit()
        return cursor.rowcount > 0

# Função para atualizar o nome de uma UBS
def update_ubs(old_name, new_name):
    with sqlite3.connect('chamados.db') as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE ubs SET nome_ubs = ? WHERE nome_ubs = ?", (new_name, old_name))
        conn.commit()
        return cursor.rowcount > 0

# Inicializar algumas UBSs no banco de dados
def initialize_ubs():
    # Certifique-se de que a tabela UBS está criada
    create_ubs_table()

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

    # Adicionar UBSs iniciais, se ainda não existirem
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

# Inicializar o sistema de UBS ao rodar o script
if __name__ == "__main__":
    initialize_ubs()
    # Exibir UBSs cadastradas para verificação
    ubs_list = get_ubs_list()
    print("UBSs cadastradas:")
    for ubs in ubs_list:
        print(ubs)
