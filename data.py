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

    # Obter todos os chamados
    try:
        chamados = list_chamados()
        
        # Depuração: verificar quantas colunas os dados têm
        st.write(f"Chamados tem {len(chamados[0])} colunas.")  # Isso irá imprimir o número de colunas dos dados
        
    except Exception as e:
        st.error(f"Erro ao listar todos os chamados: {e}")
        logging.error(f"Erro ao listar todos os chamados: {e}")
        chamados = []

    # Verifique se o número de colunas nos dados coincide com o número de colunas especificadas
    try:
        # Ajuste o número de colunas para refletir o número correto
        df_chamados = pd.DataFrame(chamados, columns=[
            'ID', 'Usuário', 'UBS', 'Setor', 'Tipo de Defeito', 'Problema',
            'Hora Abertura', 'Solução', 'Hora Fechamento', 'Protocolo',
            'Machine', 'Patrimonio'
        ])
        
        # Se a quantidade de colunas não for igual, ajuste o número de colunas
        if len(chamados[0]) != 12:  # Aqui, substitua 12 pelo número correto de colunas
            st.error(f"Erro: esperado 12 colunas, mas os dados têm {len(chamados[0])}.")
            return
        
    except Exception as e:
        st.error(f"Erro ao criar DataFrame de chamados: {e}")
        logging.error(f"Erro ao criar DataFrame de chamados: {e}")
        return

    st.subheader('Todos os Chamados')
    st.dataframe(df_chamados)
