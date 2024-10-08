import os
import sys
import logging
from datetime import datetime
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
from streamlit_option_menu import option_menu
from st_aggrid import AgGrid, GridOptionsBuilder
from fpdf import FPDF
from io import BytesIO

# Importações dos módulos personalizados
from database import (
    create_tables,
    initialize_ubs_setores,
    check_or_create_admin_user,
    SessionLocal,
    UBS,
    Setor
)
from autenticacao import (
    authenticate,
    add_user,
    list_users,
    change_password
)
from chamados import (
    add_chamado,
    list_chamados,
    list_chamados_em_aberto,
    finalizar_chamado,
    get_chamado_by_protocolo,
    show_average_time,
    get_monthly_technical_data,
    generate_monthly_report,
    calculate_tempo_decorrido_em_segundos,
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

# Inicialização do estado da sessão
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ''

# Configuração da página
st.set_page_config(
    page_title="Gestão de Parque de Informática - UBS",
    page_icon="✅",
    layout="wide",
)

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # Logs para stdout (visíveis no Streamlit Cloud)
    ]
)

# Inicializar o banco de dados e tabelas
try:
    create_tables()
    initialize_ubs_setores()
    initialize_ubs()
    initialize_setores()
    check_or_create_admin_user()
    logging.info("Banco de dados inicializado com sucesso.")
except Exception as e:
    logging.error(f"Erro ao inicializar o banco de dados: {e}")
    st.error("Erro ao inicializar o banco de dados. Verifique os logs para mais detalhes.")

# Carregar o logotipo
def carregar_logotipo():
    logo_path = st.secrets.get('LOGO_PATH', 'infocustec.png')  # Utilize st.secrets para o caminho
    logo_url = st.secrets.get('LOGO_URL', None)  # Alternativa via URL
    if logo_path and os.path.exists(logo_path):
        st.image(logo_path, width=300)
        logging.info("Logotipo carregado com sucesso do caminho local.")
    elif logo_url:
        st.image(logo_url, width=300)
        logging.info("Logotipo carregado com sucesso via URL.")
    else:
        st.warning("Logotipo não encontrado. Verifique as configurações.")
        logging.warning("Logotipo não encontrado no caminho especificado e nenhuma URL fornecida.")

carregar_logotipo()

# Título da aplicação
st.title('Gestão de Parque de Informática - UBS ITAPIPOCA')

# Função de login
def login_form():
    st.subheader('Login')
    username = st.text_input('Nome de usuário')
    password = st.text_input('Senha', type='password')

    if st.button('Entrar'):
        if not username or not password:
            st.error('Por favor, preencha ambos os campos de usuário e senha.')
            logging.warning("Tentativa de login com campos vazios.")
            return

        try:
            if authenticate(username, password):
                st.success(f'Login bem-sucedido! Bem-vindo, {username}.')
                st.session_state.logged_in = True
                st.session_state.username = username
                logging.info(f"Usuário '{username}' fez login.")
                if is_admin(username):  # Verifica se o usuário é admin
                    st.session_state.is_admin = True
                    st.info('Você está logado como administrador.')
                    logging.info(f"Usuário '{username}' tem privilégios de administrador.")
                else:
                    st.session_state.is_admin = False
                    st.info('Você está logado como usuário.')
                
            else:
                st.error('Nome de usuário ou senha incorretos.')
                logging.warning(f"Falha no login para o usuário '{username}'.")
        except Exception as e:
            st.error('Ocorreu um erro durante a autenticação. Verifique os logs para mais detalhes.')
            logging.error(f"Erro durante a autenticação do usuário '{username}': {e}")

# Função de logout
def logout():
    st.session_state.logged_in = False
    st.session_state.username = ''
    st.session_state.is_admin = False
    st.success('Você saiu da sessão.')
    logging.info("Usuário deslogado com sucesso.")
    

# Função para abrir chamado
def abrir_chamado():
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
        try:
            protocolo = add_chamado(
                st.session_state.username,
                ubs_selecionada,
                setor,
                tipo_defeito,
                problema,
                machine=selected_machine,
                patrimonio=patrimonio
            )
            if protocolo:
                st.success(f'Chamado aberto com sucesso! Seu protocolo é: {protocolo}')
                logging.info(f"Chamado '{protocolo}' aberto por '{st.session_state.username}'.")
            else:
                st.error('Erro ao abrir chamado.')
                logging.error(f"Erro ao abrir chamado por '{st.session_state.username}'.")
        except Exception as e:
            st.error('Erro ao abrir chamado. Verifique os logs para mais detalhes.')
            logging.error(f"Erro ao abrir chamado: {e}")

# Função de administração (apenas para admins)
def administracao():
    if not st.session_state.get('logged_in') or not st.session_state.get('is_admin'):
        st.warning('Você precisa estar logado como administrador para acessar esta área.')
        logging.warning("Usuário sem privilégios tentou acessar a administração.")
        return

    st.subheader('Administração')

    admin_option = st.selectbox(
        'Selecione uma opção:',
        ['Cadastro de Usuário', 'Cadastro de Máquina', 'Lista de Inventário', 'Lista de Usuários', 'Gerenciar UBSs', 'Gerenciar Setores']
    )

    if admin_option == 'Cadastro de Máquina':
        st.subheader('Cadastro de Máquina no Inventário')

        setores_existentes = get_setores_list()

        with st.form("Cadastro_de_Maquina_Admin", clear_on_submit=True):
            col1, col2 = st.columns(2)

            with col1:
                tipo = st.selectbox('Tipo de Equipamento', ['Computador', 'Impressora', 'Monitor', 'Outro'])
                marca = st.text_input('Marca')
                modelo = st.text_input('Modelo')
                numero_serie = st.text_input('Número de Série (Opcional)', value='')

            with col2:
                patrimonio = st.text_input('Número de Patrimônio')
                status = st.selectbox('Status', ['Ativo', 'Em Manutenção', 'Inativo'])
                localizacao = st.selectbox('Localização (UBS)', get_ubs_list())
                propria_locada = st.selectbox('Própria ou Locada', ['Própria', 'Locada'])
                setor = st.selectbox('Setor', setores_existentes)

            submit_button = st.form_submit_button(label='Adicionar ao Inventário')

            if submit_button:
                def validar_patrimonio(patrimonio):
                    return patrimonio.isdigit()

                if not validar_patrimonio(patrimonio):
                    st.error('Número de patrimônio inválido. Deve conter apenas dígitos.')
                    logging.warning(f"Número de patrimônio inválido no cadastro de máquina: {patrimonio}")
                    return

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
                def validar_username(username):
                    import re
                    return re.match(r'^[A-Za-z0-9_]{3,20}$', username)

                def validar_password(password):
                    return len(password) >= 6

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
            manage_ubs()
            logging.info("Gerenciamento de UBSs realizado.")
        except Exception as e:
            st.error(f"Erro ao gerenciar UBSs: {e}")
            logging.error(f"Erro ao gerenciar UBSs: {e}")

    elif admin_option == 'Gerenciar Setores':
        st.subheader('Gerenciar Setores')
        try:
            manage_setores()
            logging.info("Gerenciamento de Setores realizado.")
        except Exception as e:
            st.error(f"Erro ao gerenciar Setores: {e}")
            logging.error(f"Erro ao gerenciar Setores: {e}")

# Função para relatórios
def painel_relatorios():
    if not st.session_state.get('logged_in') or not st.session_state.get('is_admin'):
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
            df, months_list = get_monthly_technical_data()

            if not isinstance(df, pd.DataFrame):
                st.error("Erro: O retorno de dados não é um DataFrame.")
                logging.error("Esperava-se um DataFrame, mas o retorno foi de outro tipo.")
                return

            selected_month = st.selectbox('Selecione o Mês', months_list)

            if st.button('Gerar Relatório'):
                try:
                    filtered_df = df[df['Mês'].astype(str) == selected_month]

                    pdf_output = generate_monthly_report(filtered_df, selected_month, logo_path=st.secrets.get('LOGO_PATH', 'infocustec.png'))

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
            inventory_items = get_machines_from_inventory()

            pdf_output = create_inventory_report(inventory_items, logo_path=st.secrets.get('LOGO_PATH', 'infocustec.png'))

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

# Função para painel de chamados técnicos
def painel_chamados_tecnicos():
    if not st.session_state.get('logged_in') or not st.session_state.get('is_admin'):
        st.warning('Você precisa estar logado como administrador para acessar esta área.')
        logging.warning("Usuário sem privilégios tentou acessar o painel de chamados técnicos.")
        return

    st.subheader('Painel de Chamados Técnicos')

    chamados_abertos = list_chamados_em_aberto()
    chamados = list_chamados()

    if chamados:  # Certifique-se de que há dados de chamados
        df_chamados = pd.DataFrame([{
            'ID': chamado.id,
            'Usuário': chamado.username,
            'UBS': chamado.ubs,
            'Setor': chamado.setor,
            'Tipo de Defeito': chamado.tipo_defeito,
            'Problema': chamado.problema,
            'Hora Abertura': chamado.hora_abertura,
            'Solução': chamado.solucao,
            'Hora Fechamento': chamado.hora_fechamento,
            'Protocolo': chamado.protocolo,
            'Patrimônio': chamado.patrimonio,
            'Machine': chamado.machine
        } for chamado in chamados])

        df_chamados['Tempo Decorrido'] = df_chamados.apply(lambda row: calculate_tempo_decorrido(row), axis=1)

        tab1, tab2, tab3 = st.tabs(['Chamados em Aberto', 'Painel de Chamados', 'Análise de Chamados'])

        with tab1:
            st.subheader('Chamados em Aberto')

            if chamados_abertos:
                df_abertos = pd.DataFrame([{
                    'ID': chamado.id,
                    'Usuário': chamado.username,
                    'UBS': chamado.ubs,
                    'Setor': chamado.setor,
                    'Tipo de Defeito': chamado.tipo_defeito,
                    'Problema': chamado.problema,
                    'Hora Abertura': chamado.hora_abertura,
                    'Solução': chamado.solucao,
                    'Hora Fechamento': chamado.hora_fechamento,
                    'Protocolo': chamado.protocolo,
                    'Patrimônio': chamado.patrimonio,
                    'Machine': chamado.machine
                } for chamado in chamados_abertos])

                gb = GridOptionsBuilder.from_dataframe(df_abertos)
                gb.configure_pagination()
                gb.configure_selection('single', use_checkbox=True)  # Permite seleção de uma única linha com checkbox
                gridOptions = gb.build()

                grid_response = AgGrid(
                    df_abertos,
                    gridOptions=gridOptions,
                    update_mode='MODEL_CHANGED',
                    fit_columns_on_grid_load=True,
                    enable_enterprise_modules=True,
                    height=350,
                    reload_data=True
                )

                selected_rows = grid_response.get('selected_rows', [])

                # Inicializar variável para o chamado selecionado
                chamado_selecionado = None

                # Verificar se selected_rows é uma lista e contém elementos
                if isinstance(selected_rows, list) and len(selected_rows) > 0:
                    chamado_selecionado = selected_rows[0]
                # Verificar se selected_rows é um DataFrame e não está vazio
                elif isinstance(selected_rows, pd.DataFrame) and not selected_rows.empty:
                    chamado_selecionado = selected_rows.iloc[0].to_dict()

                if chamado_selecionado:
                    # Verificar se as chaves necessárias estão presentes
                    if 'ID' in chamado_selecionado and 'Problema' in chamado_selecionado:
                        st.write('### Finalizar Chamado Selecionado')
                        st.write(f"ID do Chamado: {chamado_selecionado.get('ID', 'N/A')}")
                        st.write(f"Problema: {chamado_selecionado.get('Problema', 'N/A')}")

                        solucao = st.text_area('Insira a solução para o chamado')

                        pecas_disponiveis = [
                            'Placa Mãe', 'Fonte', 'Memória RAM', 'HD', 'SSD',
                            'Teclado', 'Mouse', 'Monitor', 'Cabo de Rede', 'Placa de Rede',
                            'Processador', 'Cooler', 'Fonte da Impressora', 'Cartucho', 'Toner'
                        ]

                        pecas_selecionadas = st.multiselect(
                            'Selecione as peças utilizadas',
                            pecas_disponiveis
                        )

                        if st.button('Finalizar Chamado'):
                            if solucao:
                                try:
                                    # Finalizar o chamado e atualizar o banco de dados
                                    finalizar_chamado(chamado_selecionado.get('ID'), solucao, pecas_selecionadas)
                                    st.success(f'Chamado ID: {chamado_selecionado["ID"]} finalizado com sucesso!')
                                    logging.info(f"Chamado ID: {chamado_selecionado['ID']} finalizado por {st.session_state.username}.")
                                    st.experimental_rerun()  # Atualiza a página
                                except Exception as e:
                                    st.error(f"Erro ao finalizar o chamado: {e}")
                                    logging.error(f"Erro ao finalizar o chamado ID {chamado_selecionado.get('ID')}: {e}")
                                    st.experimental_set_query_params(updated='true')
                            else:
                                st.error('Por favor, insira a solução antes de finalizar o chamado.')
                    else:
                        st.error("O chamado selecionado não contém informações completas.")
                else:
                    st.info('Nenhum chamado selecionado.')
            else:
                st.info("Não há chamados em aberto no momento.")
                logging.info("Nenhum chamado em aberto para exibir.")

        with tab2:
            st.subheader('Painel de Chamados')

            status_options = ['Todos', 'Em Aberto', 'Finalizado']
            status = st.selectbox('Filtrar por Status', status_options)

            ubs_list = ['Todas'] + df_chamados['UBS'].unique().tolist()
            ubs_selecionada = st.selectbox('Filtrar por UBS', ubs_list)

            df_filtrado = df_chamados.copy()

            if status != 'Todos':
                if status == 'Em Aberto':
                    df_filtrado = df_filtrado[df_filtrado['Hora Fechamento'].isnull()]
                else:
                    df_filtrado = df_filtrado[df_filtrado['Hora Fechamento'].notnull()]

            if ubs_selecionada != 'Todas':
                df_filtrado = df_filtrado[df_filtrado['UBS'] == ubs_selecionada]

            gb = GridOptionsBuilder.from_dataframe(df_filtrado)
            gb.configure_pagination()
            gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc='sum', editable=False)
            gridOptions = gb.build()

            AgGrid(
                df_filtrado,
                gridOptions=gridOptions,
                enable_enterprise_modules=True
            )

        with tab3:
            st.subheader('Análise de Chamados')
            # Exibir tempo médio de atendimento
            st.subheader('Tempo Médio de Atendimento')
            try:
                show_average_time(chamados)  # Chamada da função que exibe o tempo médio de atendimento
            except Exception as e:
                st.error(f"Erro ao exibir tempo médio de atendimento: {e}")
                logging.error(f"Erro ao exibir tempo médio de atendimento: {e}")

            fig = px.bar(
                df_chamados,
                x='UBS',
                title='Quantidade de Chamados por UBS',
                labels={'UBS': 'UBS', 'ID': 'Quantidade'},
                color='UBS'  # Definir cor diferente para cada UBS
            )
            fig.update_layout(yaxis=dict(tickmode='linear', tick0=1))
            st.plotly_chart(fig)

            fig_defeitos = px.bar(
                df_chamados,
                x='Tipo de Defeito',
                title='Quantidade de Chamados por Tipo de Defeito',
                labels={'Tipo de Defeito': 'Tipo de Defeito', 'ID': 'Quantidade'},
                color='Tipo de Defeito'  # Definir cor diferente para cada tipo de defeito
            )
            fig_defeitos.update_layout(yaxis=dict(tickmode='linear', tick0=1))
            st.plotly_chart(fig_defeitos)

            fig_setor = px.bar(
                df_chamados,
                x='Setor',
                title='Quantidade de Chamados por Setor',
                labels={'Setor': 'Setor', 'ID': 'Quantidade'},
                color='Setor'  # Definir cor diferente para cada setor
            )
            fig_setor.update_layout(yaxis=dict(tickmode='linear', tick0=1))
            st.plotly_chart(fig_setor)

# Função para buscar protocolo
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
                st.write(f'**ID:** {chamado.id}')
                st.write(f'**Usuário:** {chamado.username}')
                st.write(f'**UBS:** {chamado.ubs}')
                st.write(f'**Setor:** {chamado.setor}')
                st.write(f'**Tipo de Defeito:** {chamado.tipo_defeito}')
                st.write(f'**Problema:** {chamado.problema}')
                st.write(f'**Hora Abertura:** {chamado.hora_abertura}')
                st.write(f'**Solução:** {chamado.solucao}')
                st.write(f'**Hora Fechamento:** {chamado.hora_fechamento}')
                st.write(f'**Protocolo:** {chamado.protocolo}')
                st.write(f'**Máquina:** {chamado.machine}')
                st.write(f'**Patrimônio:** {chamado.patrimonio}')
                logging.info(f"Chamado encontrado pelo protocolo: {protocolo}")
            else:
                st.warning(f'Chamado com o protocolo {protocolo} não encontrado.')
                logging.info(f"Chamado não encontrado pelo protocolo: {protocolo}")
        except Exception as e:
            st.error(f"Erro ao buscar chamado: {e}")
            logging.error(f"Erro ao buscar chamado pelo protocolo {protocolo}: {e}")

# Função para configurações (alterar senha)
def configuracoes():
    if not st.session_state.get('logged_in') or not st.session_state.get('is_admin'):
        st.warning('Você precisa estar logado como administrador para acessar esta área.')
        logging.warning("Usuário sem privilégios tentou acessar as configurações.")
        return

    st.subheader('Configurações de Usuários')

    usuarios = list_users()
    if not usuarios:
        st.info("Nenhum usuário encontrado.")
        return

    usernames = [user[0] for user in usuarios]

    selected_user = st.selectbox('Selecione um usuário para alterar a senha:', usernames)

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
        try:
            if change_password(selected_user, nova_senha):
                st.success(f'Senha do usuário "{selected_user}" alterada com sucesso!')
                logging.info(f"Senha do usuário '{selected_user}' alterada com sucesso pelo administrador.")
            else:
                st.error('Erro ao alterar a senha.')
                logging.error(f"Erro ao alterar a senha do usuário '{selected_user}'.")
        except Exception as e:
            st.error(f"Erro ao alterar a senha: {e}")
            logging.error(f"Erro ao alterar a senha do usuário '{selected_user}': {e}")

# Criação do menu de navegação
def criar_menu():
    if st.session_state.get('logged_in'):
        if st.session_state.get('is_admin'):
            menu_options = ['Abrir Chamado', 'Administração', 'Relatórios', 'Chamados Técnicos', 'Buscar Protocolo', 'Configurações', 'Logout']
            icons = ['plus-square', 'gear', 'bar-chart', 'tools', 'search', 'wrench', 'box-arrow-right']
        else:
            menu_options = ['Abrir Chamado', 'Buscar Protocolo', 'Logout']
            icons = ['plus-square', 'search', 'box-arrow-right']
    else:
        menu_options = ['Login']
        icons = ['box-arrow-in-right']

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
    return selected_option

# Criação do menu
selected_option = criar_menu()

# Renderização do conteúdo com base na opção selecionada
if selected_option == 'Login':
    if not st.session_state.get('logged_in'):
        login_form()
    else:
        st.info(f"Você já está logado como {st.session_state.get('username')}.")
elif selected_option == 'Logout':
    logout()
elif selected_option == 'Abrir Chamado':
    abrir_chamado()
elif selected_option == 'Buscar Protocolo':
    buscar_protocolo()
elif selected_option == 'Administração':
    administracao()
elif selected_option == 'Relatórios':
    painel_relatorios()
elif selected_option == 'Chamados Técnicos':
    painel_chamados_tecnicos()
elif selected_option == 'Configurações':
    configuracoes()
else:
    st.error("Página selecionada não existe.")
    logging.error(f"Página selecionada inválida: {selected_option}")

# Página padrão ou conteúdo adicional
st.markdown("""
---
Desenvolvido por Infocustec (Email: atendimento@infocustec.com.br)
""")
