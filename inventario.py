import sqlite3
import streamlit as st
import pandas as pd
import logging
from fpdf import FPDF
from io import BytesIO
import os

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("inventario.log"),
        logging.StreamHandler()
    ]
)

# Função para obter os setores a partir das tabelas 'chamados' e 'inventario'
def get_setores_from_db():
    try:
        with sqlite3.connect('chamados.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT setor FROM chamados WHERE setor IS NOT NULL")
            setores_chamados = cursor.fetchall()
            cursor.execute("SELECT DISTINCT setor FROM inventario WHERE setor IS NOT NULL")
            setores_inventario = cursor.fetchall()
        setores = set([s[0] for s in setores_chamados + setores_inventario])
        logging.info("Setores obtidos do banco de dados.")
        return sorted(setores)
    except sqlite3.Error as e:
        logging.error(f"Erro ao obter setores: {e}")
        st.error("Erro interno ao obter setores. Tente novamente mais tarde.")
        return []

# Função para cadastrar máquina no inventário
def add_machine_to_inventory(tipo, marca, modelo, numero_serie, status, localizacao, propria_locada, patrimonio, setor):
    try:
        with sqlite3.connect('chamados.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM inventario WHERE numero_patrimonio = ?", (patrimonio,))
            existing_machine = cursor.fetchone()

            if existing_machine:
                st.error(f"Máquina com o número de patrimônio {patrimonio} já existe no inventário.")
                logging.warning(f"Tentativa de duplicação de patrimônio: {patrimonio}")
            else:
                numero_serie = numero_serie if numero_serie else None
                cursor.execute("""
                    INSERT INTO inventario 
                    (numero_patrimonio, tipo, marca, modelo, numero_serie, status, localizacao, propria_locada, setor) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (patrimonio, tipo, marca, modelo, numero_serie, status, localizacao, propria_locada, setor))
                conn.commit()
                st.success('Máquina adicionada ao inventário com sucesso!')
                logging.info(f"Máquina adicionada: Patrimônio {patrimonio}")
    except sqlite3.Error as e:
        logging.error(f"Erro ao adicionar máquina ao inventário: {e}")
        st.error("Erro interno ao adicionar máquina. Tente novamente mais tarde.")

# Função para listar chamados técnicos relacionados a um número de patrimônio
def list_chamados_por_patrimonio(patrimonio):
    try:
        with sqlite3.connect('chamados.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM chamados WHERE patrimonio = ?", (patrimonio,))
            chamados = cursor.fetchall()
            return chamados
    except sqlite3.Error as e:
        logging.error(f"Erro ao listar chamados por patrimônio {patrimonio}: {e}")
        st.error("Erro interno ao listar chamados. Tente novamente mais tarde.")
        return []

# Função para mostrar o formulário de cadastro de máquina
def show_inventory_form():
    st.subheader('Cadastro de Máquina')

    # Obter a lista de UBSs e setores existentes
    ubs_list = get_ubs_list()  # Assumindo que a função get_ubs_list já está definida em outro módulo
    setores_existentes = get_setores_from_db()

    with st.form("Formulario_inventario", clear_on_submit=True):
        tipo = st.selectbox('Tipo de Equipamento', ['Computador', 'Impressora', 'Monitor', 'Outro'])
        marca = st.text_input('Marca')
        modelo = st.text_input('Modelo')
        numero_serie = st.text_input('Número de Série (Opcional)', value='')
        patrimonio = st.text_input('Número de Patrimônio')
        status = st.selectbox('Status', ['Ativo', 'Em Manutenção', 'Inativo'])
        localizacao = st.selectbox('Localização (UBS)', ubs_list)

        if setores_existentes:
            setor = st.selectbox('Setor', setores_existentes)
        else:
            st.warning('Nenhum setor encontrado. Insira um novo setor abaixo.')
            setor = st.text_input('Setor (Novo)')

        submit_button = st.form_submit_button(label='Adicionar ao Inventário')

        if submit_button:
            if all([marca, modelo, patrimonio, localizacao, setor]):
                add_machine_to_inventory(tipo, marca, modelo, numero_serie, status, localizacao, 'Própria', patrimonio, setor)
            else:
                st.error("Preencha todos os campos obrigatórios!")
                logging.warning("Campos obrigatórios não preenchidos no formulário de cadastro de máquina.")

# Função para obter máquinas do inventário
def get_machines_from_inventory():
    try:
        with sqlite3.connect('chamados.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM inventario")
            machines = cursor.fetchall()
        logging.info("Máquinas recuperadas do inventário.")
        return machines
    except sqlite3.Error as e:
        logging.error(f"Erro ao recuperar máquinas do inventário: {e}")
        st.error("Erro interno ao recuperar inventário. Tente novamente mais tarde.")
        return []

# Função para exibir lista de inventário com a opção de listar chamados por patrimônio
def show_inventory_list():
    st.subheader('Lista de Inventário')
    inventory_items = get_machines_from_inventory()

    if inventory_items:
        df = pd.DataFrame(inventory_items, columns=[
            'ID', 'Número de Patrimônio', 'Tipo', 'Marca', 'Modelo', 'Número de Série', 
            'Status', 'Localização', 'Própria/Locada', 'Setor'
        ])

        st.dataframe(df)

        selected_patrimonio = st.selectbox('Selecione o Número de Patrimônio para ações:', df['Número de Patrimônio'])
        action = st.selectbox('Selecione uma ação:', ['Visualizar', 'Editar', 'Atualizar Status', 'Listar Chamados Técnicos', 'Excluir'])

        if action == 'Visualizar':
            st.write(df[df['Número de Patrimônio'] == selected_patrimonio])
            show_maintenance_history(selected_patrimonio)

        elif action == 'Editar':
            item = df[df['Número de Patrimônio'] == selected_patrimonio].iloc[0]
            with st.form('edit_form'):
                tipo = st.selectbox('Tipo de Equipamento', ['Computador', 'Impressora', 'Monitor', 'Outro'], index=['Computador', 'Impressora', 'Monitor', 'Outro'].index(item['Tipo']))
                marca = st.text_input('Marca', value=item['Marca'])
                modelo = st.text_input('Modelo', value=item['Modelo'])
                status = st.selectbox('Status', ['Ativo', 'Em Manutenção', 'Inativo'], index=['Ativo', 'Em Manutenção', 'Inativo'].index(item['Status']))
                localizacao = st.text_input('Localização', value=item['Localização'])

                setores = get_setores_from_db()
                if setores:
                    setor = st.selectbox('Setor', setores, index=setores.index(item['Setor']))
                else:
                    setor = st.text_input('Setor (Novo)', value=item['Setor'])

                propria_locada = st.selectbox('Própria ou Locada', ['Própria', 'Locada'], index=['Própria', 'Locada'].index(item['Própria/Locada']))
                submit_button = st.form_submit_button('Salvar Alterações')
                if submit_button:
                    new_values = {
                        'tipo': tipo,
                        'marca': marca,
                        'modelo': modelo,
                        'status': status,
                        'localizacao': localizacao,
                        'setor': setor,
                        'propria_locada': propria_locada
                    }
                    edit_inventory_item(selected_patrimonio, new_values)

        elif action == 'Atualizar Status':
            new_status = st.selectbox('Novo Status', ['Ativo', 'Em Manutenção', 'Inativo'])
            if st.button('Atualizar Status'):
                update_inventory_status(selected_patrimonio, new_status)

        elif action == 'Listar Chamados Técnicos':
            chamados = list_chamados_por_patrimonio(selected_patrimonio)
            if chamados:
                df_chamados = pd.DataFrame(chamados, columns=[
                    'ID', 'Usuário', 'UBS', 'Setor', 'Tipo de Defeito', 'Problema',
                    'Hora Abertura', 'Solução', 'Hora Fechamento', 'Protocolo',
                    'Máquina', 'Patrimônio'
                ])
                st.subheader(f'Chamados Técnicos para o Patrimônio {selected_patrimonio}')
                st.dataframe(df_chamados)
            else:
                st.info(f'Nenhum chamado técnico encontrado para o patrimônio {selected_patrimonio}.')

        elif action == 'Excluir':
            if st.button('Confirmar Exclusão'):
                delete_inventory_item(selected_patrimonio)
    else:
        st.write("Nenhum item encontrado no inventário.")

# Função para adicionar manutenção no histórico
def add_maintenance_history(patrimonio, descricao):
    if not descricao:
        st.error("Por favor, insira a descrição da manutenção.")
        logging.warning(f"Tentativa de adicionar manutenção sem descrição para patrimônio {patrimonio}.")
        return
    try:
        with sqlite3.connect('chamados.db') as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO historico_manutencao (numero_patrimonio, descricao, data_manutencao) VALUES (?, ?, datetime('now'))",
                           (patrimonio, descricao))
            conn.commit()
        logging.info(f"Manutenção adicionada para patrimônio {patrimonio}.")
    except sqlite3.Error as e:
        logging.error(f"Erro ao adicionar manutenção para patrimônio {patrimonio}: {e}")
        st.error("Erro interno ao adicionar manutenção. Tente novamente mais tarde.")

# Função para mostrar o histórico de manutenção de uma máquina junto com peças usadas
def show_maintenance_history(patrimonio):
    try:
        with sqlite3.connect('chamados.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT descricao, data_manutencao FROM historico_manutencao WHERE numero_patrimonio = ?", (patrimonio,))
            history = cursor.fetchall()
            
            cursor.execute("""
                SELECT pu.peca_nome, pu.data_uso 
                FROM pecas_usadas pu
                JOIN chamados c ON pu.chamado_id = c.id
                WHERE c.patrimonio = ?
            """, (patrimonio,))
            pecas = cursor.fetchall()

        if history:
            df_history = pd.DataFrame(history, columns=['Descrição', 'Data'])
            df_pecas = pd.DataFrame(pecas, columns=['Peça', 'Data de Uso'])
            st.write(df_history)
            st.write("Peças Usadas:")
            st.write(df_pecas)
            logging.info(f"Histórico de manutenção e peças exibido para patrimônio {patrimonio}.")
        else:
            st.write("Nenhum histórico de manutenção encontrado para este item.")
            logging.info(f"Nenhum histórico de manutenção encontrado para patrimônio {patrimonio}.")
    except sqlite3.Error as e:
        logging.error(f"Erro ao recuperar histórico de manutenção para patrimônio {patrimonio}: {e}")
        st.error("Erro interno ao recuperar histórico de manutenção. Tente novamente mais tarde.")

# Função para atualizar o status de um item no inventário
def update_inventory_status(patrimonio, new_status):
    try:
        with sqlite3.connect('chamados.db') as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE inventario SET status = ? WHERE numero_patrimonio = ?", (new_status, patrimonio))
            conn.commit()
            st.success('Status atualizado com sucesso!')
            logging.info(f"Status atualizado para patrimônio {patrimonio}: {new_status}")
    except sqlite3.Error as e:
        logging.error(f"Erro ao atualizar status do patrimônio {patrimonio}: {e}")
        st.error("Erro interno ao atualizar status. Tente novamente mais tarde.")

# Função para editar um item no inventário
def edit_inventory_item(patrimonio, new_values):
    try:
        with sqlite3.connect('chamados.db') as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE inventario 
                SET tipo = ?, marca = ?, modelo = ?, status = ?, localizacao = ?, 
                    setor = ?, propria_locada = ? 
                WHERE numero_patrimonio = ?
            """, (
                new_values['tipo'], new_values['marca'], new_values['modelo'], 
                new_values['status'], new_values['localizacao'], 
                new_values['setor'], new_values['propria_locada'], patrimonio
            ))
            conn.commit()
            st.success('Informações atualizadas com sucesso!')
            logging.info(f"Informações atualizadas para patrimônio {patrimonio}.")
    except sqlite3.Error as e:
        logging.error(f"Erro ao editar patrimônio {patrimonio}: {e}")
        st.error("Erro interno ao editar informações. Tente novamente mais tarde.")

# Função para remover um item do inventário
def delete_inventory_item(patrimonio):
    try:
        with sqlite3.connect('chamados.db') as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM inventario WHERE numero_patrimonio = ?", (patrimonio,))
            conn.commit()
            st.success('Item removido com sucesso!')
            logging.info(f"Item removido: Patrimônio {patrimonio}")
    except sqlite3.Error as e:
        logging.error(f"Erro ao remover patrimônio {patrimonio}: {e}")
        st.error("Erro interno ao remover item. Tente novamente mais tarde.")

# Função para criar um relatório de inventário em PDF
def create_inventory_report(inventory_items, logo_path):
    if not inventory_items:
        st.error("Nenhum dado no inventário.")
        logging.warning("Tentativa de gerar relatório de inventário sem dados.")
        return None

    try:
        pdf = FPDF('L', 'mm', 'A4')  # Layout paisagem, milímetros, tamanho A4
        pdf.add_page()
        pdf.set_font("Arial", size=8)

        # Inserir o logotipo se disponível
        if logo_path and os.path.exists(logo_path):
            pdf.image(logo_path, x=10, y=10, w=30)
            logging.info("Logotipo inserido no relatório de inventário.")
        elif logo_path:
            st.warning("Logotipo não encontrado. Continuando sem logotipo.")
            logging.warning("Logotipo não encontrado para inserção no relatório.")

        pdf.ln(40)  # Espaçamento após o logotipo
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, 'Relatório de Inventário', 0, 1, 'C')  # Título centralizado

        pdf.ln(10)  # Espaçamento após o título

        # Definir cabeçalhos da tabela
        headers = ['Número de Patrimônio', 'Tipo', 'Marca', 'Modelo', 'Número de Série', 'Status', 'Localização', 'Própria/Locada', 'Setor']
        column_widths = [40, 20, 20, 25, 30, 25, 30, 30, 40]

        # Criar cabeçalhos
        pdf.set_font('Arial', 'B', 10)
        for col_width, header in zip(column_widths, headers):
            pdf.cell(col_width, 10, header, 1, 0, 'C')  # Usar o parâmetro 'align' correto: 'C' para centralizado
        pdf.ln()

        # Preencher a tabela com dados do inventário
        pdf.set_font('Arial', '', 8)
        for item in inventory_items:
            item_data = item[1:]  # Pular o ID
            for col_width, value in zip(column_widths, item_data):
                pdf.cell(col_width, 10, str(value).strip(), 1)  # Alinhar à esquerda por padrão
            pdf.ln()

        # Criar o arquivo PDF na memória
        pdf_output = BytesIO()
        pdf_output.write(pdf.output(dest='S').encode('latin1'))  # Salvar o PDF na memória
        pdf_output.seek(0)

        logging.info("Relatório de inventário em PDF gerado com sucesso.")
        return pdf_output
    except Exception as e:
        logging.error(f"Erro ao gerar relatório de inventário: {e}")
        st.error("Erro interno ao gerar relatório. Tente novamente mais tarde.")
        return None
