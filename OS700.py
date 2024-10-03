import streamlit as st
import os
import logging
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from streamlit_option_menu import option_menu

# Importar as funções dos módulos
from database import create_tables, initialize_ubs_setores, check_or_create_admin_user, is_admin
from autenticacao import authenticate, add_user, list_users, change_password
from chamados import (
    add_chamado,
    list_chamados,
    list_chamados_em_aberto,
    finalizar_chamado,
    get_chamado_by_protocolo,
    show_average_time,
    generate_linear_time_chart,
    get_monthly_technical_data,
    generate_monthly_report,
    calculate_tempo_decorrido,
    buscar_no_inventario_por_patrimonio
)
from inventario import (
    get_machines_from_inventory,
    show_inventory_list,
    add_machine_to_inventory,
    show_maintenance_history,
    add_maintenance_history,
    update_inventory_status,
    delete_inventory_item,
    edit_inventory_item,
    create_inventory_report
)
from ubs import initialize_ubs, manage_ubs, get_ubs_list
from setores import initialize_setores, manage_setores, get_setores_list

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("os500.log"),
        logging.StreamHandler()
    ]
)

# Inicializar o banco de dados e tabelas
create_tables()
initialize_ubs_setores()
check_or_create_admin_user()
logging.info("Banco de dados inicializado com sucesso.")

# Inicializar session_state
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ''

# Configuração da página do Streamlit
st.set_page_config(
    page_title="Gestão de Parque de Informática - UBS",
    page_icon="✅",
    layout="wide",
)

# Gerenciar caminho do logotipo via variável de ambiente
logo_path = os.getenv('LOGO_PATH', 'infocustec.png')
if os.path.exists(logo_path):
    st.image(logo_path, width=300)
    logging.info("Logotipo carregado com sucesso.")
else:
    st.warning("Logotipo não encontrado. Verifique o caminho configurado.")
    logging.warning("Logotipo não encontrado no caminho especificado.")

# Título da aplicação
st.title('Gestão de Parque de Informática - UBS ITAPIPOCA')

# Menu de navegação utilizando o streamlit-option-menu
if st.session_state.get('logged_in') and is_admin(st.session_state.get('username')):
    menu_options = ['Login', 'Abrir Chamado', 'Administração', 'Relatórios', 'Chamados Técnicos', 'Buscar Protocolo', 'Configurações']
    icons = ['box-arrow-in-right', 'plus-square', 'gear', 'bar-chart', 'tools', 'search', 'wrench']
else:
    menu_options = ['Login', 'Abrir Chamado', 'Buscar Protocolo']
    icons = ['box-arrow-in-right', 'plus-square', 'search']

# Crie o menu horizontal
selected_option = option_menu(
    menu_title=None,
    options=menu_options,
    icons=icons,
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "#00008B"},
        "icon": {"color": "white", "font-size": "18px"},
        "nav-link": {
            "font-size": "16px",
            "text-align": "center",
            "margin": "0px",
            "color": "white",
            "--hover-color": "#1E90FF",
        },
        "nav-link-selected": {"background-color": "#1E90FF"},
    }
)

# Funções da aplicação
def login():
    st.subheader('Login')
    username = st.text_input('Nome de usuário')
    password = st.text_input('Senha', type='password')

    if st.button('Entrar'):
        if not username or not password:
            st.error('Por favor, preencha ambos os campos de usuário e senha.')
            logging.warning("Tentativa de login com campos vazios.")
            return

        if authenticate(username, password):
            st.success(f'Login bem-sucedido! Bem-vindo, {username}.')
            st.session_state.logged_in = True
            st.session_state.username = username
            logging.info(f"Usuário '{username}' fez login.")
            if is_admin(username):
                st.info('Você está logado como administrador.')
                logging.info(f"Usuário '{username}' tem privilégios de administrador.")
            else:
                st.info('Você está logado como usuário.')
        else:
            st.error('Nome de usuário ou senha incorretos.')
            logging.warning(f"Falha no login para o usuário '{username}'.")

def abrir_chamado():
    if not st.session_state.get('logged_in'):
        st.warning('Você precisa estar logado para abrir um chamado.')
        return

    st.subheader('Abrir Chamado Técnico')

    patrimonio = st.text_input('Número de Patrimônio')
    machine_info = None
    machine_type = None  # Garantir que a variável seja sempre inicializada

    # Verifica se foi inserido o patrimônio e busca no inventário
    if patrimonio:
        machine_info = buscar_no_inventario_por_patrimonio(patrimonio)
        if machine_info:
            # Preenche as informações automaticamente com os dados do inventário
            st.write(f'**Máquina encontrada:** {machine_info["tipo"]} - {machine_info["marca"]} {machine_info["modelo"]}')
            st.write(f'**UBS:** {machine_info["localizacao"]} | **Setor:** {machine_info["setor"]}')
            ubs_selecionada = machine_info['localizacao']
            setor = machine_info['setor']
            selected_machine = machine_info['patrimonio']
            machine_type = machine_info['tipo']  # Atribuir o tipo da máquina encontrado no inventário
        else:
            # Se o patrimônio não for encontrado no inventário, o usuário deve preencher as informações manualmente
            st.error('Número de patrimônio não encontrado no inventário.')
            ubs_list = get_ubs_list()
            setores_list = get_setores_list()

            ubs_selecionada = st.selectbox('Unidade Básica de Saúde (UBS)', ubs_list)
            setor = st.selectbox('Setor', setores_list)
            selected_machine = None
            machine_type = st.selectbox('Tipo de Máquina', ['Computador', 'Impressora', 'Outro'])  # Define o tipo manualmente
    else:
        # Caso o patrimônio não seja inserido, o usuário preenche manualmente as informações
        ubs_list = get_ubs_list()
        setores_list = get_setores_list()

        ubs_selecionada = st.selectbox('Unidade Básica de Saúde (UBS)', ubs_list)
        setor = st.selectbox('Setor', setores_list)
        machine_type = st.selectbox('Tipo de Máquina', ['Computador', 'Impressora', 'Outro'])  # Define o tipo manualmente
        selected_machine = None

    # Verificação do tipo de máquina selecionado
    if machine_type:
        st.write(f'Tipo de Máquina selecionado: {machine_type}')

    # Definir tipos de defeito com base no tipo de máquina selecionado
    if machine_type == 'Computador':
        tipo_defeito = st.selectbox('Tipo de Defeito/Solicitação', [
            'Computador não liga', 'Computador lento', 'Tela azul',
            'Sistema travando', 'Erro de disco', 'Problema com atualização',
            'Desligamento inesperado', 'Problemas de internet', 'Problema com Wi-Fi',
            'Sem conexão de rede', 'Mouse não funciona', 'Teclado não funciona'
        ])
    elif machine_type == 'Impressora':
        tipo_defeito = st.selectbox('Tipo de Defeito/Solicitação', [
            'Impressora não imprime', 'Impressão borrada', 'Toner vazio',
            'Troca de toner', 'Papel enroscado', 'Erro de conexão com a impressora'
        ])
    else:
        tipo_defeito = st.selectbox('Tipo de Defeito/Solicitação', [
            'Solicitação de suporte geral', 'Outros tipos de defeito'
        ])

    problema = st.text_area('Descreva o Problema ou Solicitação')

    if st.button('Abrir Chamado'):
        if not problema:
            st.error('Por favor, descreva o problema ou solicitação.')
            return
        protocolo = add_chamado(
            st.session_state.username,
            ubs_selecionada,
            setor,
            tipo_defeito,
            problema,
            machine=selected_machine,
            patrimonio=patrimonio
        )
        st.success(f'Chamado aberto com sucesso! Seu protocolo é: {protocolo}')

def administracao():
    if not st.session_state.get('logged_in') or not is_admin(st.session_state.get('username')):
        st.warning('Você precisa estar logado como administrador para acessar esta área.')
        logging.warning("Usuário sem privilégios tentou acessar a administração.")
        return

    st.subheader('Administração')

    # Menu de opções para administração
    admin_option = st.selectbox(
        'Selecione uma opção:',
        ['Cadastro de Usuário', 'Cadastro de Máquina', 'Lista de Inventário', 'Lista de Usuários', 'Gerenciar UBSs', 'Gerenciar Setores']
    )

    if admin_option == 'Cadastro de Máquina':
        st.subheader('Cadastro de Máquina no Inventário')

        # Usar a função get_setores_list para obter os setores
        setores_existentes = get_setores_list()

        with st.form("Cadastro_de_Maquina_Admin", clear_on_submit=True):
            tipo = st.selectbox('Tipo de Equipamento', ['Computador', 'Impressora', 'Monitor', 'Outro'])
            marca = st.text_input('Marca')
            modelo = st.text_input('Modelo')
            numero_serie = st.text_input('Número de Série (Opcional)', value='')  # Número de série como opcional
            patrimonio = st.text_input('Número de Patrimônio')  # Número de patrimônio obrigatório
            status = st.selectbox('Status', ['Ativo', 'Em Manutenção', 'Inativo'])
            localizacao = st.selectbox('Localização (UBS)', get_ubs_list())
            propria_locada = st.selectbox('Própria ou Locada', ['Própria', 'Locada'])

            # Verificar se setores estão disponíveis
            setor = st.selectbox('Setor', setores_existentes)

            submit_button = st.form_submit_button(label='Adicionar ao Inventário')

            if submit_button:
                # Validação do número de patrimônio
                def validar_patrimonio(patrimonio):
                    return patrimonio.isdigit()

                if not validar_patrimonio(patrimonio):
                    st.error('Número de patrimônio inválido. Deve conter apenas dígitos.')
                    logging.warning(f"Número de patrimônio inválido no cadastro de máquina: {patrimonio}")
                    return

                # Verificar se os campos obrigatórios estão preenchidos
                if marca and modelo and patrimonio and localizacao and setor:
                    try:
                        add_machine_to_inventory(
                            tipo=tipo,
                            marca=marca,
                            modelo=modelo,
                            numero_serie=numero_serie,
                            status=status,
                            localizacao=localizacao,
                            propria_locada=propria_locada,
                            patrimonio=patrimonio,
                            setor=setor
                        )
                        st.success('Máquina adicionada ao inventário com sucesso!')
                        logging.info(f"Máquina {patrimonio} adicionada ao inventário por {st.session_state.username}.")
                    except Exception as e:
                        st.error(f"Erro ao adicionar máquina: {e}")
                        logging.error(f"Erro ao adicionar máquina: {e}")
                else:
                    st.error("Preencha todos os campos obrigatórios!")
                    logging.warning("Campos obrigatórios não preenchidos no cadastro de máquina.")

    elif admin_option == 'Lista de Inventário':
        st.subheader('Lista de Inventário')
        try:
            show_inventory_list()
            logging.info("Lista de inventário exibida.")
        except Exception as e:
            st.error(f"Erro ao exibir a lista de inventário: {e}")
            logging.error(f"Erro ao exibir a lista de inventário: {e}")

    elif admin_option == 'Cadastro de Usuário':
        st.subheader('Cadastro de Usuário')

        with st.form("Cadastro_de_Usuario_Admin", clear_on_submit=True):
            novo_username = st.text_input('Nome de usuário')
            novo_password = st.text_input('Senha', type='password')
            is_admin_user = st.checkbox('Administrador')

            submit_button = st.form_submit_button(label='Cadastrar Usuário')

            if submit_button:
                # Validação de inputs
                def validar_username(username):
                    import re
                    return re.match(r'^[A-Za-z0-9_]{3,20}$', username)

                def validar_password(password):
                    return len(password) >= 6  # Exemplo simples

                if not novo_username or not novo_password:
                    st.error("Por favor, preencha todos os campos obrigatórios.")
                    logging.warning("Tentativa de cadastro de usuário com campos vazios.")
                    return

                if not validar_username(novo_username):
                    st.error("Nome de usuário inválido. Use 3-20 caracteres alfanuméricos ou sublinhados.")
                    logging.warning(f"Nome de usuário inválido inserido: {novo_username}")
                    return

                if not validar_password(novo_password):
                    st.error("Senha muito curta. Deve conter pelo menos 6 caracteres.")
                    logging.warning("Senha muito curta inserida durante o cadastro de usuário.")
                    return

                try:
                    if add_user(novo_username, novo_password, is_admin_user):
                        st.success('Usuário cadastrado com sucesso!')
                        logging.info(f"Novo usuário cadastrado: {novo_username}, Admin: {is_admin_user}")
                    else:
                        st.error('Falha ao cadastrar usuário. O usuário pode já existir.')
                        logging.warning(f"Falha ao cadastrar usuário: {novo_username}")
                except Exception as e:
                    st.error(f"Erro ao cadastrar usuário: {e}")
                    logging.error(f"Erro ao cadastrar usuário: {e}")

    elif admin_option == 'Lista de Usuários':
        st.subheader('Lista de Usuários')
        try:
            usuarios = list_users()
            df_usuarios = pd.DataFrame(usuarios, columns=['Nome de Usuário', 'Função'])
            st.dataframe(df_usuarios)
            logging.info("Lista de usuários exibida.")
        except Exception as e:
            st.error(f"Erro ao listar usuários: {e}")
            logging.error(f"Erro ao listar usuários: {e}")

    elif admin_option == 'Gerenciar UBSs':
        st.subheader('Gerenciar UBSs')
        try:
            manage_ubs()  # Chama a função para gerenciar UBSs
            logging.info("Gerenciamento de UBSs realizado.")
        except Exception as e:
            st.error(f"Erro ao gerenciar UBSs: {e}")
            logging.error(f"Erro ao gerenciar UBSs: {e}")

    elif admin_option == 'Gerenciar Setores':
        st.subheader('Gerenciar Setores')
        try:
            manage_setores()  # Chama a função para gerenciar Setores
            logging.info("Gerenciamento de Setores realizado.")
        except Exception as e:
            st.error(f"Erro ao gerenciar Setores: {e}")
            logging.error(f"Erro ao gerenciar Setores: {e}")

def painel_chamados_tecnicos():
    if not st.session_state.get('logged_in') or not is_admin(st.session_state.get('username')):
        st.warning('Você precisa estar logado como administrador para acessar esta área.')
        logging.warning("Usuário sem privilégios tentou acessar o painel de chamados técnicos.")
        return

    st.subheader('Painel de Chamados Técnicos')

    try:
        chamados_abertos = list_chamados_em_aberto()
    except Exception as e:
        st.error(f"Erro ao listar chamados em aberto: {e}")
        logging.error(f"Erro ao listar chamados em aberto: {e}")
        chamados_abertos = []

    # Lista de peças que podem ser utilizadas (pode ser expandida conforme necessário)
    pecas_disponiveis = [
        'Placa Mãe', 'Fonte', 'Memória RAM', 'HD', 'SSD',
        'Teclado', 'Mouse', 'Monitor', 'Cabo de Rede', 'Placa de Rede',
        'Processador', 'Cooler', 'Fonte da Impressora', 'Cartucho', 'Toner'
    ]

    if chamados_abertos:
        st.subheader('Chamados em Aberto')

        for chamado in chamados_abertos:
            with st.expander(f"Chamado ID: {chamado[0]}"):
                st.write(f"**ID do Chamado:** {chamado[0]}")
                st.write(f"**Usuário:** {chamado[1]}")
                st.write(f"**UBS:** {chamado[2]}")
                st.write(f"**Setor:** {chamado[3]}")  # Exibe o setor do chamado
                st.write(f"**Tipo de Defeito:** {chamado[4]}")
                st.write(f"**Problema:** {chamado[5]}")
                st.write(f"**Hora de Abertura:** {chamado[6]}")

                solucao = st.text_area('Insira a solução para o chamado', key=f"solucao_{chamado[0]}")

                # Selectbox para selecionar múltiplas peças utilizadas
                pecas_selecionadas = st.multiselect(
                    'Selecione as peças utilizadas',
                    pecas_disponiveis,
                    key=f"pecas_{chamado[0]}"
                )

                if st.button(f"Finalizar Chamado ID: {chamado[0]}", key=f"finalizar_{chamado[0]}"):
                    if solucao:
                        try:
                            # Finaliza o chamado e registra as peças usadas
                            finalizar_chamado(chamado[0], solucao, pecas_selecionadas)
                            st.success(f'Chamado ID: {chamado[0]} finalizado com sucesso!')
                            logging.info(f"Chamado ID: {chamado[0]} finalizado por {st.session_state.username}.")
                            st.experimental_rerun()
                        except Exception as e:
                            st.error(f"Erro ao finalizar chamado: {e}")
                            logging.error(f"Erro ao finalizar chamado ID: {chamado[0]}: {e}")
                    else:
                        st.error('Por favor, insira a solução antes de finalizar o chamado.')
                        logging.warning(f"Chamado ID: {chamado[0]} tentou ser finalizado sem solução.")

    else:
        st.info("Não há chamados em aberto no momento.")
        logging.info("Nenhum chamado em aberto para exibir.")

    # Obter todos os chamados
    try:
        chamados = list_chamados()

    except Exception as e:
        st.error(f"Erro ao listar todos os chamados: {e}")
        logging.error(f"Erro ao listar todos os chamados: {e}")
        chamados = []

    df_chamados = pd.DataFrame(chamados, columns=[
        'ID', 'Usuário', 'UBS', 'Setor', 'Tipo de Defeito', 'Problema',
        'Hora Abertura', 'Solução', 'Hora Fechamento',
        'Protocolo', 'Patrimônio', 'Machine'
    ])

    try:
        df_chamados['Tempo Decorrido'] = df_chamados.apply(lambda row: calculate_tempo_decorrido(row), axis=1)
    except Exception as e:
        st.error(f"Erro ao calcular tempo decorrido: {e}")
        logging.error(f"Erro ao calcular tempo decorrido: {e}")
        df_chamados['Tempo Decorrido'] = None

    st.subheader('Painel de Chamados')
    st.dataframe(df_chamados)

    # Exibir tempo médio de atendimento
    st.subheader('Tempo Médio de Atendimento')
    try:
        show_average_time(chamados)
    except Exception as e:
        st.error(f"Erro ao exibir tempo médio de atendimento: {e}")
        logging.error(f"Erro ao exibir tempo médio de atendimento: {e}")

    # Gráfico de tempo linear
    st.subheader('Tempo Decorrido entre Chamados')
    try:
        generate_linear_time_chart(chamados)
    except Exception as e:
        st.error(f"Erro ao gerar gráfico de tempo linear: {e}")
        logging.error(f"Erro ao gerar gráfico de tempo linear: {e}")

    # Gráficos de análise dos dados
    if not df_chamados.empty:
        st.subheader('Análise de Chamados')

        try:
            # Tipos de Defeito por UBS
            df_defeitos_ubs = df_chamados.groupby(['UBS', 'Tipo de Defeito']).size().unstack(fill_value=0)
            fig, ax = plt.subplots(figsize=(12, 8))
            df_defeitos_ubs.plot(kind='bar', stacked=True, ax=ax)
            ax.set_title('Tipos de Defeito por UBS')
            ax.set_xlabel('UBS')
            ax.set_ylabel('Quantidade de Chamados')
            ax.yaxis.get_major_locator().set_params(integer=True)
            plt.xticks(rotation=45)
            plt.tight_layout()
            st.pyplot(fig)
            logging.info("Gráfico 'Tipos de Defeito por UBS' exibido.")
        except Exception as e:
            st.error(f"Erro ao gerar gráfico 'Tipos de Defeito por UBS': {e}")
            logging.error(f"Erro ao gerar gráfico 'Tipos de Defeito por UBS': {e}")

        try:
            # Quantidade de Chamados por UBS
            st.subheader('Quantidade de Chamados por UBS')
            ubs_counts = df_chamados['UBS'].value_counts()
            fig1, ax1 = plt.subplots(figsize=(8, 6))
            sns.barplot(x=ubs_counts.index, y=ubs_counts.values, ax=ax1)
            ax1.set_title('Quantidade de Chamados por UBS')
            ax1.yaxis.get_major_locator().set_params(integer=True)
            plt.xticks(rotation=45)
            plt.tight_layout()
            st.pyplot(fig1)
            logging.info("Gráfico 'Quantidade de Chamados por UBS' exibido.")
        except Exception as e:
            st.error(f"Erro ao gerar gráfico 'Quantidade de Chamados por UBS': {e}")
            logging.error(f"Erro ao gerar gráfico 'Quantidade de Chamados por UBS': {e}")

        try:
            # Quantidade de Chamados por Tipo de Defeito
            st.subheader('Quantidade de Chamados por Tipo de Defeito')
            defeito_counts = df_chamados['Tipo de Defeito'].value_counts()
            fig2, ax2 = plt.subplots(figsize=(8, 6))
            sns.barplot(x=defeito_counts.index, y=defeito_counts.values, ax=ax2)
            ax2.set_title('Quantidade de Chamados por Tipo de Defeito')
            ax2.yaxis.get_major_locator().set_params(integer=True)
            plt.xticks(rotation=45)
            plt.tight_layout()
            st.pyplot(fig2)
            logging.info("Gráfico 'Quantidade de Chamados por Tipo de Defeito' exibido.")
        except Exception as e:
            st.error(f"Erro ao gerar gráfico 'Quantidade de Chamados por Tipo de Defeito': {e}")
            logging.error(f"Erro ao gerar gráfico 'Quantidade de Chamados por Tipo de Defeito': {e}")

        try:
            # Quantidade de Chamados por Setor
            st.subheader('Quantidade de Chamados por Setor')
            setor_counts = df_chamados['Setor'].value_counts()
            fig3, ax3 = plt.subplots(figsize=(8, 6))
            sns.barplot(x=setor_counts.index, y=setor_counts.values, ax=ax3)
            ax3.set_title('Quantidade de Chamados por Setor')
            ax3.yaxis.get_major_locator().set_params(integer=True)
            plt.xticks(rotation=45)
            plt.tight_layout()
            st.pyplot(fig3)
            logging.info("Gráfico 'Quantidade de Chamados por Setor' exibido.")
        except Exception as e:
            st.error(f"Erro ao gerar gráfico 'Quantidade de Chamados por Setor': {e}")
            logging.error(f"Erro ao gerar gráfico 'Quantidade de Chamados por Setor': {e}")

def painel_relatorios():
    if not st.session_state.get('logged_in') or not is_admin(st.session_state.get('username')):
        st.warning('Você precisa estar logado como administrador para acessar esta área.')
        logging.warning("Usuário sem privilégios tentou acessar os relatórios.")
        return

    st.subheader('Relatórios')
    report_option = st.selectbox(
        'Selecione um tipo de relatório:',
        ['Chamados Técnicos', 'Inventário']
    )

    if report_option == 'Chamados Técnicos':
        st.subheader('Relatório de Chamados Técnicos')
        try:
            # Chamar a função que retorna o DataFrame e a lista de meses
            df, months_list = get_monthly_technical_data()

            # Verifique se 'df' é realmente um DataFrame
            if not isinstance(df, pd.DataFrame):
                st.error("Erro: O retorno de dados não é um DataFrame.")
                logging.error("Esperava-se um DataFrame, mas o retorno foi de outro tipo.")
                return

            # Exibir a seleção do mês
            selected_month = st.selectbox('Selecione o Mês', months_list)

            # Quando o botão 'Gerar Relatório' for pressionado
            if st.button('Gerar Relatório'):
                try:
                    # Filtrar o DataFrame pelo mês selecionado
                    filtered_df = df[df['Mês'].astype(str) == selected_month]

                    # Gerar o relatório PDF com os dados filtrados
                    pdf_output = generate_monthly_report(filtered_df, selected_month, logo_path)

                    # Se o PDF for gerado com sucesso, exibir o botão de download
                    if pdf_output:
                        st.download_button(
                            label="Download Relatório PDF",
                            data=pdf_output,
                            file_name=f"Relatorio_Chamados_Mensal_{selected_month}.pdf",
                            mime="application/pdf"
                        )
                        logging.info(f"Relatório mensal gerado para o mês: {selected_month}")
                    else:
                        st.error(f"Erro ao gerar o relatório para o mês: {selected_month}")
                        logging.error(f"Erro ao gerar o relatório para o mês: {selected_month}")

                except Exception as e:
                    st.error(f"Erro ao gerar relatório: {e}")
                    logging.error(f"Erro ao gerar relatório mensal: {e}")
        except Exception as e:
            st.error(f"Erro ao preparar dados para relatório: {e}")
            logging.error(f"Erro ao preparar dados para relatório: {e}")

    elif report_option == 'Inventário':
        st.subheader('Relatório de Inventário')
        try:
            # Obter os itens do inventário
            inventory_items = get_machines_from_inventory()

            # Gerar o relatório PDF de inventário
            pdf_output = create_inventory_report(inventory_items, logo_path)

            # Se o PDF for gerado com sucesso, exibir o botão de download
            if pdf_output:
                st.download_button(
                    label="Download Relatório de Inventário",
                    data=pdf_output,
                    file_name="Relatorio_Inventario.pdf",
                    mime="application/pdf"
                )
                logging.info("Relatório de inventário gerado com sucesso.")
            else:
                st.error("Erro ao gerar relatório de inventário.")
                logging.error("Erro ao gerar relatório de inventário.")
        except Exception as e:
            st.error(f"Erro ao gerar relatório de inventário: {e}")
            logging.error(f"Erro ao gerar relatório de inventário: {e}")

def buscar_protocolo():
    st.subheader('Buscar Chamado por Protocolo')
    protocolo = st.text_input('Digite o número do protocolo:')

    if st.button('Buscar'):
        if not protocolo:
            st.error('Por favor, insira um número de protocolo para buscar.')
            logging.warning("Busca de protocolo realizada sem inserção de protocolo.")
            return

        try:
            chamado = get_chamado_by_protocolo(protocolo)
            if chamado:
                st.success('Chamado encontrado:')
                st.write(f'**ID:** {chamado[0]}')
                st.write(f'**Usuário:** {chamado[1]}')
                st.write(f'**UBS:** {chamado[2]}')
                st.write(f'**Setor:** {chamado[3]}')
                st.write(f'**Tipo de Defeito:** {chamado[4]}')
                st.write(f'**Problema:** {chamado[5]}')
                st.write(f'**Hora Abertura:** {chamado[6]}')
                st.write(f'**Solução:** {chamado[7]}')
                st.write(f'**Hora Fechamento:** {chamado[8]}')
                st.write(f'**Protocolo:** {chamado[9]}')
                st.write(f'**Máquina:** {chamado[10]}')
                st.write(f'**Patrimônio:** {chamado[11]}')
                logging.info(f"Chamado encontrado pelo protocolo: {protocolo}")
            else:
                st.warning(f'Chamado com o protocolo {protocolo} não encontrado.')
                logging.info(f"Chamado não encontrado pelo protocolo: {protocolo}")
        except Exception as e:
            st.error(f"Erro ao buscar chamado: {e}")
            logging.error(f"Erro ao buscar chamado pelo protocolo {protocolo}: {e}")

def configuracoes():
    if not st.session_state.get('logged_in') or not is_admin(st.session_state.get('username')):
        st.warning('Você precisa estar logado como administrador para acessar esta área.')
        logging.warning("Usuário sem privilégios tentou acessar as configurações.")
        return

    st.subheader('Configurações de Usuários')

    # Obter a lista de usuários
    usuarios = list_users()
    if not usuarios:
        st.info("Nenhum usuário encontrado.")
        return

    usernames = [user[0] for user in usuarios]

    # Selecionar o usuário para alterar a senha
    selected_user = st.selectbox('Selecione um usuário para alterar a senha:', usernames)

    # Campos para inserir a nova senha
    nova_senha = st.text_input('Nova senha', type='password')
    confirmar_senha = st.text_input('Confirme a nova senha', type='password')

    if st.button('Alterar Senha'):
        if not nova_senha or not confirmar_senha:
            st.error('Por favor, preencha ambos os campos de senha.')
            return
        if nova_senha != confirmar_senha:
            st.error('As senhas não coincidem.')
            return
        if len(nova_senha) < 6:
            st.error('A senha deve ter pelo menos 6 caracteres.')
            return
        if change_password(selected_user, nova_senha):
            st.success(f'Senha do usuário "{selected_user}" alterada com sucesso!')
            logging.info(f"Senha do usuário '{selected_user}' alterada com sucesso pelo administrador.")
        else:
            st.error('Erro ao alterar a senha.')
            logging.error(f"Erro ao alterar a senha do usuário '{selected_user}'.")

# Páginas disponíveis no menu
if selected_option == 'Login':
    login()
elif selected_option == 'Abrir Chamado':
    abrir_chamado()
elif selected_option == 'Administração':
    administracao()
elif selected_option == 'Relatórios':
    painel_relatorios()
elif selected_option == 'Chamados Técnicos':
    painel_chamados_tecnicos()
elif selected_option == 'Buscar Protocolo':
    buscar_protocolo()
elif selected_option == 'Configurações':
    configuracoes()
else:
    st.error("Página selecionada não existe.")
    logging.error(f"Página selecionada inválida: {selected_option}")
