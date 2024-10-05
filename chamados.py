import os
from datetime import datetime, timedelta
from twilio.rest import Client
import streamlit as st
import pandas as pd
from fpdf import FPDF
from io import BytesIO
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.ticker import MaxNLocator
import tempfile
import logging
from database import SessionLocal, Chamado, Inventario, HistoricoManutencao, PecaUsada, Usuario
from sqlalchemy import desc
from autenticacao import is_admin

# Configurações de autenticação do Twilio (caso necessário)
account_sid = 'AC4eb3adf6ace24cc654d2823e9e9d2309'
auth_token = '7f1ceaf4d179eb2d1fe9897860158571'
client = Client(account_sid, auth_token)

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("chamados.log"),
        logging.StreamHandler()
    ]
)

# Função para gerar protocolo sequencial
def gerar_protocolo_sequencial():
    session = SessionLocal()
    try:
        max_protocolo = session.query(Chamado).order_by(desc(Chamado.protocolo)).first()
        if max_protocolo:
            protocolo = max_protocolo.protocolo + 1
        else:
            protocolo = 1
        return protocolo
    except Exception as e:
        logging.error(f"Erro ao gerar protocolo sequencial: {e}")
        return None
    finally:
        session.close()

# Função para buscar chamado por protocolo
def get_chamado_by_protocolo(protocolo):
    session = SessionLocal()
    try:
        chamado = session.query(Chamado).filter(Chamado.protocolo == protocolo).first()
        logging.info(f"Chamado buscado pelo protocolo {protocolo}: {'Encontrado' if chamado else 'Não encontrado'}")
        return chamado
    except Exception as e:
        logging.error(f"Erro ao buscar chamado por protocolo {protocolo}: {e}")
        st.error("Erro interno ao buscar chamado. Tente novamente mais tarde.")
        return None
    finally:
        session.close()

# Função para buscar no inventário por número de patrimônio
def buscar_no_inventario_por_patrimonio(patrimonio):
    session = SessionLocal()
    try:
        inventario = session.query(Inventario).filter(Inventario.numero_patrimonio == patrimonio).first()
        if inventario:
            logging.info(f"Máquina encontrada no inventário: Patrimônio {patrimonio}")
            return {
                'tipo': inventario.tipo, 
                'marca': inventario.marca, 
                'modelo': inventario.modelo,
                'patrimonio': inventario.numero_patrimonio,
                'localizacao': inventario.localizacao,
                'setor': inventario.setor
            }
        logging.info(f"Número de patrimônio {patrimonio} não encontrado no inventário.")
        return None
    except Exception as e:
        logging.error(f"Erro ao buscar patrimônio {patrimonio} no inventário: {e}")
        st.error("Erro interno ao buscar no inventário. Tente novamente mais tarde.")
        return None
    finally:
        session.close()

# Função para adicionar um chamado
def add_chamado(username, ubs, setor, tipo_defeito, problema, machine=None, patrimonio=None):
    protocolo = gerar_protocolo_sequencial()
    if protocolo is None:
        return

    hora_abertura = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

    session = SessionLocal()
    try:
        novo_chamado = Chamado(
            username=username,
            ubs=ubs,
            setor=setor,
            tipo_defeito=tipo_defeito,
            problema=problema,
            hora_abertura=hora_abertura,
            protocolo=protocolo,
            machine=machine,
            patrimonio=patrimonio
        )
        session.add(novo_chamado)
        session.commit()
        logging.info(f"Chamado aberto: Protocolo {protocolo} por usuário {username}")

        # Enviar mensagem via WhatsApp
        numeros_destino = [
            'whatsapp:+558586981658',
            'whatsapp:+558894000846',
        ]
        if client and ubs and setor:
            for numero in numeros_destino:
                try:
                    client.messages.create(
                        from_='whatsapp:+14155238886',
                        body=f"Novo chamado técnico na UBS '{ubs}' no setor '{setor}': {problema}",
                        to=numero
                    )
                    logging.info(f"Mensagem enviada para {numero} via WhatsApp.")
                except Exception as e:
                    logging.error(f"Erro ao enviar mensagem para {numero} via WhatsApp: {e}")
                    st.error(f"Erro ao enviar mensagem para {numero} via WhatsApp: {e}")

        st.success(f"Chamado aberto com sucesso! Protocolo: {protocolo}")
    except Exception as e:
        session.rollback()
        logging.error(f"Erro ao adicionar chamado: {e}")
        st.error("Erro interno ao abrir chamado. Tente novamente mais tarde.")
    finally:
        session.close()

# Função para finalizar um chamado
def finalizar_chamado(id_chamado, solucao, pecas_usadas=None):
    hora_fechamento = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    session = SessionLocal()
    try:
        chamado = session.query(Chamado).filter(Chamado.id == id_chamado).first()
        if chamado:
            chamado.solucao = solucao
            chamado.hora_fechamento = hora_fechamento
            session.commit()

            if pecas_usadas:
                for peca in pecas_usadas:
                    peca_usada = PecaUsada(
                        chamado_id=id_chamado,
                        peca_nome=peca,
                        data_uso=hora_fechamento
                    )
                    session.add(peca_usada)
                session.commit()

            descricao_manutencao = f"Manutenção realizada: {solucao}. Peças usadas: {', '.join(pecas_usadas) if pecas_usadas else 'Nenhuma'}."
            historico = HistoricoManutencao(
                numero_patrimonio=chamado.patrimonio,
                descricao=descricao_manutencao,
                data_manutencao=hora_fechamento
            )
            session.add(historico)
            session.commit()

            st.success(f'Chamado ID: {id_chamado} finalizado com sucesso e histórico de manutenção criado!')
            logging.info(f"Chamado ID: {id_chamado} finalizado e histórico de manutenção criado para patrimônio {chamado.patrimonio}.")
        else:
            st.error("Número de patrimônio não encontrado para o chamado.")
            logging.warning(f"Número de patrimônio não encontrado para o chamado ID {id_chamado}.")
    except Exception as e:
        session.rollback()
        logging.error(f"Erro ao finalizar chamado ID {id_chamado}: {e}")
        st.error(f"Erro interno ao finalizar chamado e registrar manutenção. Tente novamente mais tarde. Detalhes: {e}")
    finally:
        session.close()

# Função para listar todos os chamados
def list_chamados():
    session = SessionLocal()
    try:
        chamados = session.query(Chamado).all()
        logging.info("Lista de todos os chamados recuperada.")
        return chamados
    except Exception as e:
        logging.error(f"Erro ao listar chamados: {e}")
        st.error("Erro interno ao listar chamados. Tente novamente mais tarde.")
        return []
    finally:
        session.close()

# Função para listar chamados em aberto
def list_chamados_em_aberto():
    session = SessionLocal()
    try:
        chamados = session.query(Chamado).filter(Chamado.hora_fechamento == None).all()
        logging.info("Lista de chamados em aberto recuperada.")
        return chamados
    except Exception as e:
        logging.error(f"Erro ao listar chamados em aberto: {e}")
        st.error("Erro interno ao listar chamados em aberto. Tente novamente mais tarde.")
        return []
    finally:
        session.close()

# Função otimizada para calcular horas úteis entre duas datas
def calculate_working_hours(start, end):
    total_seconds = 0
    current = start

    while current < end:
        if current.weekday() >= 5:
            next_day = current + timedelta(days=1)
            current = next_day.replace(hour=0, minute=0, second=0, microsecond=0)
            continue

        start_morning = current.replace(hour=8, minute=0, second=0, microsecond=0)
        end_morning = current.replace(hour=12, minute=0, second=0, microsecond=0)
        start_afternoon = current.replace(hour=13, minute=0, second=0, microsecond=0)
        end_afternoon = current.replace(hour=17, minute=0, second=0, microsecond=0)

        if start <= end_morning and end > start_morning:
            interval_start = max(start, start_morning)
            interval_end = min(end, end_morning)
            if interval_end > interval_start:
                total_seconds += (interval_end - interval_start).total_seconds()

        if start <= end_afternoon and end > start_afternoon:
            interval_start = max(start, start_afternoon)
            interval_end = min(end, end_afternoon)
            if interval_end > interval_start:
                total_seconds += (interval_end - interval_start).total_seconds()

        current = (current + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    return timedelta(seconds=total_seconds)

def calculate_tempo_decorrido(chamado):
    try:
        hora_abertura = chamado.hora_abertura
        hora_fechamento = chamado.hora_fechamento or datetime.now()

        if isinstance(hora_abertura, str):
            hora_abertura = datetime.strptime(hora_abertura, '%d/%m/%Y %H:%M:%S')

        if isinstance(hora_fechamento, str):
            hora_fechamento = datetime.strptime(hora_fechamento, '%d/%m/%Y %H:%M:%S')

        tempo_uteis = calculate_working_hours(hora_abertura, hora_fechamento)

        total_seconds = int(tempo_uteis.total_seconds())
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        tempo_formatado = ''
        if days > 0:
            tempo_formatado += f'{days}d '
        if hours > 0 or days > 0:
            tempo_formatado += f'{hours}h '
        if minutes > 0 or hours > 0 or days > 0:
            tempo_formatado += f'{minutes}m '
        tempo_formatado += f'{seconds}s'

        return tempo_formatado
    except Exception as e:
        logging.error(f"Erro ao calcular tempo decorrido: {e}")
        return "Erro no cálculo"

def calculate_tempo_decorrido_em_segundos(chamado):
    try:
        hora_abertura = chamado.hora_abertura
        hora_fechamento = chamado.hora_fechamento or datetime.now()

        if isinstance(hora_abertura, str):
            hora_abertura = datetime.strptime(hora_abertura, '%d/%m/%Y %H:%M:%S')

        if isinstance(hora_fechamento, str):
            hora_fechamento = datetime.strptime(hora_fechamento, '%d/%m/%Y %H:%M:%S')

        tempo_uteis = calculate_working_hours(hora_abertura, hora_fechamento)
        return tempo_uteis.total_seconds()
    except Exception as e:
        logging.error(f"Erro ao calcular tempo decorrido em segundos: {e}")
        return None

def formatar_tempo(total_seconds):
    try:
        total_seconds = int(total_seconds)
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        tempo_formatado = ''
        if days > 0:
            tempo_formatado += f'{days}d '
        if hours > 0 or days > 0:
            tempo_formatado += f'{hours}h '
        if minutes > 0 or hours > 0 or days > 0:
            tempo_formatado += f'{minutes}m '
        tempo_formatado += f'{seconds}s'

        return tempo_formatado
    except Exception as e:
        logging.error(f"Erro ao formatar tempo: {e}")
        return "Erro no formato"

def calculate_average_time(chamados):
    total_tempo = 0
    total_chamados_finalizados = 0
    for chamado in chamados:
        if chamado.hora_abertura and chamado.hora_fechamento:
            tempo_segundos = calculate_tempo_decorrido_em_segundos(chamado)
            if tempo_segundos is not None:
                total_tempo += tempo_segundos
                total_chamados_finalizados += 1
    if total_chamados_finalizados > 0:
        media_tempo = total_tempo / total_chamados_finalizados
        logging.info(f"Tempo médio de atendimento calculado: {media_tempo} segundos")
    else:
        media_tempo = 0
        logging.info("Nenhum chamado finalizado para calcular tempo médio de atendimento.")
    return media_tempo

def show_average_time(chamados):
    if chamados:
        media_tempo_segundos = calculate_average_time(chamados)
        tempo_formatado = formatar_tempo(media_tempo_segundos)
        st.write(f'Tempo médio de atendimento: {tempo_formatado}')
    else:
        st.write('Nenhum chamado finalizado para calcular o tempo médio.')

def get_monthly_technical_data():
    chamados = list_chamados()
    data = []
    for chamado in chamados:
        data.append({
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
            'Machine': chamado.machine,
            'Patrimonio': chamado.patrimonio
        })
    df = pd.DataFrame(data)
    df['Hora Abertura'] = pd.to_datetime(df['Hora Abertura'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
    df['Hora Fechamento'] = pd.to_datetime(df['Hora Fechamento'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
    df['Mês'] = df['Hora Abertura'].dt.to_period('M')
    months_list = df['Mês'].astype(str).unique().tolist()
    logging.info("Dados mensais dos chamados técnicos preparados.")
    return df, months_list

def save_plot_to_temp_file():
    try:
        tmpfile = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        plt.savefig(tmpfile.name, format='png')
        plt.close()
        logging.info(f"Gráfico salvo temporariamente em {tmpfile.name}")
        return tmpfile.name
    except Exception as e:
        logging.error(f"Erro ao salvar gráfico temporariamente: {e}")
        return None

def add_image_to_pdf(pdf, image_path, title):
    try:
        pdf.set_font('Arial', 'B', 12)
        pdf.ln(10)
        pdf.cell(0, 10, title, ln=True, align='C')
        pdf.image(image_path, x=10, y=pdf.get_y() + 10, w=270)
        os.remove(image_path)
        logging.info(f"Imagem {title} adicionada ao PDF e arquivo temporário removido.")
    except Exception as e:
        logging.error(f"Erro ao adicionar imagem {title} ao PDF: {e}")

def generate_monthly_report(df, selected_month, pecas_usadas_df=None, logo_path=None):
    try:
        if not isinstance(df, pd.DataFrame):
            raise ValueError("O argumento 'df' não é um DataFrame")
        
        if pecas_usadas_df is None or not isinstance(pecas_usadas_df, pd.DataFrame):
            logging.warning("O argumento 'pecas_usadas_df' não é um DataFrame ou é None. Criando DataFrame vazio.")
            pecas_usadas_df = pd.DataFrame(columns=['chamado_id', 'peca_nome'])
        
        df['Hora Abertura'] = pd.to_datetime(df['Hora Abertura'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
        df['Hora Fechamento'] = pd.to_datetime(df['Hora Fechamento'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
        
        df = df.dropna(subset=['Hora Abertura'])
        
        selected_year_int = int(selected_month[:4])
        selected_month_int = int(selected_month[5:7])
        
        df_filtered = df[
            (df['Hora Abertura'].dt.year == selected_year_int) & 
            (df['Hora Abertura'].dt.month == selected_month_int)
        ]
        
        if df_filtered.empty:
            st.warning(f"Não há dados para o mês selecionado: {selected_month}.")
            logging.info(f"Relatório mensal: nenhum dado para {selected_month}.")
            return None
        
        df_filtered['Tempo Decorrido (s)'] = df_filtered.apply(
            calculate_tempo_decorrido_em_segundos, axis=1
        )
        
        df_filtered = df_filtered.dropna(subset=['Tempo Decorrido (s)'])
        
        if df_filtered.empty:
            st.warning("Nenhum dado disponível após o cálculo do tempo decorrido.")
            logging.info("Nenhum dado disponível após o cálculo do tempo decorrido.")
            return None

        if not pecas_usadas_df.empty:
            pecas_usadas_por_chamado = pecas_usadas_df.groupby('chamado_id')['peca_nome'].apply(', '.join).reset_index()
            df_filtered = pd.merge(df_filtered, pecas_usadas_por_chamado, left_on='ID', right_on='chamado_id', how='left')
            df_filtered['peca_nome'] = df_filtered['peca_nome'].fillna('Nenhuma')
        else:
            df_filtered['peca_nome'] = 'Nenhuma'

        total_chamados = len(df_filtered)
        chamados_resolvidos = df_filtered['Hora Fechamento'].notnull().sum()
        chamados_nao_resolvidos = total_chamados - chamados_resolvidos
        tempo_medio_resolucao_seg = df_filtered['Tempo Decorrido (s)'].mean()
        tempo_medio_resolucao = formatar_tempo(tempo_medio_resolucao_seg) if pd.notnull(tempo_medio_resolucao_seg) else 'N/A'
        tipo_defeito_mais_comum = df_filtered['Tipo de Defeito'].mode()[0] if not df_filtered['Tipo de Defeito'].mode().empty else 'N/A'
        setor_mais_ativo = df_filtered['Setor'].mode()[0] if not df_filtered['Setor'].mode().empty else 'N/A'
        ubs_mais_ativa = df_filtered['UBS'].mode()[0] if not df_filtered['UBS'].mode().empty else 'N/A'
        
        total_pecas_usadas = pecas_usadas_df['peca_nome'].count() if not pecas_usadas_df.empty else 0
        pecas_mais_usadas = pecas_usadas_df['peca_nome'].value_counts().head(5) if not pecas_usadas_df.empty else pd.Series([], dtype="int64")

        fig, ax = plt.subplots(figsize=(10, 6))
        sns.countplot(data=df_filtered, x='UBS', order=df_filtered['UBS'].value_counts().index, ax=ax)
        ax.set_title('Número de Chamados por UBS')
        ax.set_xticklabels(ax.get_xticklabels(), rotation=45)
        plt.tight_layout(pad=2.0)
        chamados_por_ubs_chart = save_plot_to_temp_file()
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(10, 6))
        sns.countplot(data=df_filtered, x='Tipo de Defeito', order=df_filtered['Tipo de Defeito'].value_counts().index, ax=ax)
        ax.set_title('Número de Chamados por Tipo de Defeito')
        ax.set_xticklabels(ax.get_xticklabels(), rotation=45)
        plt.tight_layout(pad=2.0)
        chamados_por_defeito_chart = save_plot_to_temp_file()
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(10, 6))
        tempo_medio_por_ubs = df_filtered.groupby('UBS')['Tempo Decorrido (s)'].mean().reset_index()
        tempo_medio_por_ubs['Tempo Médio'] = tempo_medio_por_ubs['Tempo Decorrido (s)'].apply(formatar_tempo)
        sns.barplot(data=tempo_medio_por_ubs, x='UBS', y='Tempo Decorrido (s)', ax=ax)
        ax.set_title('Tempo Médio de Resolução por UBS')
        ax.set_ylabel('Tempo (segundos)')
        ax.set_xticklabels(ax.get_xticklabels(), rotation=45)
        plt.tight_layout(pad=2.0)
        tempo_medio_por_ubs_chart = save_plot_to_temp_file()
        plt.close(fig)

        if not pecas_mais_usadas.empty:
            fig, ax = plt.subplots(figsize=(10, 6))
            sns.barplot(x=pecas_mais_usadas.index, y=pecas_mais_usadas.values, ax=ax)
            ax.set_title('Peças Mais Usadas')
            ax.set_xlabel('Peça')
            ax.set_ylabel('Quantidade')
            pecas_mais_usadas_chart = save_plot_to_temp_file()
            plt.close(fig)

        pdf = FPDF(orientation='L')
        pdf.add_page()
        
        if logo_path and os.path.exists(logo_path):
            pdf.image(logo_path, x=10, y=8, w=30)
        elif logo_path:
            st.warning("Logotipo não encontrado. Verifique o caminho configurado.")
            logging.warning("Logotipo não encontrado para inserção no relatório.")
        
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, f'Relatório Mensal de Chamados Técnicos - {selected_month}', ln=True, align='C')
        
        pdf.set_font('Arial', '', 12)
        pdf.ln(10)
        pdf.cell(0, 10, f'Total de Chamados: {total_chamados}', ln=True)
        pdf.cell(0, 10, f'Chamados Resolvidos: {chamados_resolvidos}', ln=True)
        pdf.cell(0, 10, f'Chamados Não Resolvidos: {chamados_nao_resolvidos}', ln=True)
        pdf.cell(0, 10, f'Tempo Médio de Resolução: {tempo_medio_resolucao}', ln=True)
        pdf.cell(0, 10, f'Tipo de Defeito Mais Comum: {tipo_defeito_mais_comum}', ln=True)
        pdf.cell(0, 10, f'Setor Mais Ativo: {setor_mais_ativo}', ln=True)
        pdf.cell(0, 10, f'UBS Mais Ativa: {ubs_mais_ativa}', ln=True)
        pdf.cell(0, 10, f'Total de Peças Usadas: {total_pecas_usadas}', ln=True)
        
        pdf.ln(10)
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Dashboard', ln=True, align='C')
        
        pdf.add_page()
        add_image_to_pdf(pdf, chamados_por_ubs_chart, 'Chamados por UBS')
        
        pdf.add_page()
        add_image_to_pdf(pdf, chamados_por_defeito_chart, 'Chamados por Tipo de Defeito')

        pdf.add_page()
        add_image_to_pdf(pdf, tempo_medio_por_ubs_chart, 'Tempo Médio de Resolução por UBS')

        if not pecas_mais_usadas.empty:
            pdf.add_page()
            add_image_to_pdf(pdf, pecas_mais_usadas_chart, 'Peças Mais Usadas')

        pdf.add_page()
        
        if logo_path and os.path.exists(logo_path):
            pdf.image(logo_path, x=10, y=8, w=30)
        
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 10, 'Detalhamento dos Chamados', ln=True, align='C')

        columns = ['Protocolo', 'UBS', 'Setor', 'Tipo de Defeito', 'Problema', 'Hora Abertura', 'Hora Fechamento', 'Tempo Decorrido', 'Peças Usadas']
        col_widths = [16, 34, 34, 31, 36, 31, 31, 31, 26]

        pdf.set_font('Arial', 'B', 10)
        for i, col in enumerate(columns):
            pdf.cell(col_widths[i], 8, col, border=1, align='C')
        pdf.ln()

        pdf.set_font('Arial', '', 8)
        for _, row in df_filtered.iterrows():
            pdf.cell(col_widths[0], 8, str(row['Protocolo']), border=1, align='C')
            pdf.cell(col_widths[1], 8, str(row['UBS']), border=1, align='C')
            pdf.cell(col_widths[2], 8, str(row['Setor']), border=1, align='C')
            pdf.cell(col_widths[3], 8, str(row['Tipo de Defeito']), border=1, align='C')
            pdf.cell(col_widths[4], 8, str(row['Problema']), border=1, align='L')
            pdf.cell(col_widths[5], 8, row['Hora Abertura'].strftime('%d/%m/%Y %H:%M:%S'), border=1, align='C')
            pdf.cell(col_widths[6], 8, row['Hora Fechamento'].strftime('%d/%m/%Y %H:%M:%S') if row['Hora Fechamento'] else '-', border=1, align='C')
            tempo_formatado = formatar_tempo(row['Tempo Decorrido (s)'])
            pdf.cell(col_widths[7], 8, tempo_formatado, border=1, align='C')
            pdf.cell(col_widths[8], 8, row['peca_nome'], border=1, align='L')
            pdf.ln()

        pdf_content = pdf.output(dest='S').encode('latin1')
        pdf_output = BytesIO(pdf_content)

        logging.info(f"Relatório mensal de chamados técnicos gerado para {selected_month}")
        return pdf_output
    except Exception as e:
        logging.error(f"Erro ao gerar relatório mensal: {e}")
        st.error("Erro ao gerar relatório. Tente novamente mais tarde.")
        return None

# Função para gerar gráfico de tempo linear
def generate_linear_time_chart(chamados):
    try:
        if chamados:
            tempos_decorridos = []
            chamados_sorted = sorted(chamados, key=lambda x: datetime.strptime(x.hora_abertura, '%d/%m/%Y %H:%M:%S'))
            for i in range(1, len(chamados_sorted)):
                tempo_decorrido = calculate_tempo_decorrido_entre_chamados(chamados_sorted[i - 1], chamados_sorted[i])
                if tempo_decorrido:
                    tempos_decorridos.append(tempo_decorrido)

            if tempos_decorridos:
                tempos_numeros = [int(tempo.total_seconds() / 60) for tempo in tempos_decorridos]
                plt.figure(figsize=(10, 6))
                plt.plot(tempos_numeros, marker='o', linestyle='-')
                plt.title('Tempo Decorrido entre Chamados Consecutivos')
                plt.xlabel('Chamados Consecutivos')
                plt.ylabel('Tempo Decorrido (minutos)')
                plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))
                plt.tight_layout(pad=2.0)

                linear_time_chart = save_plot_to_temp_file()
                
                pdf = FPDF(orientation='L')
                pdf.add_page()
                pdf.set_font('Arial', 'B', 14)
                pdf.cell(0, 10, 'Tempo Decorrido entre Chamados Consecutivos', ln=True, align='C')
                pdf.image(linear_time_chart, x=10, y=30, w=270)

                pdf_output = BytesIO()
                pdf_output_bytes = pdf.output(dest='S').encode('latin1')
                pdf_output.write(pdf_output_bytes)
                pdf_output.seek(0)

                logging.info("Gráfico de tempo linear gerado com sucesso.")
                return pdf_output
        return None
    except Exception as e:
        logging.error(f"Erro ao gerar gráfico de tempo linear: {e}")
        return None

# Função para calcular tempo decorrido entre chamados consecutivos
def calculate_tempo_decorrido_entre_chamados(chamado_anterior, chamado_atual):
    try:
        hora_abertura_anterior = chamado_anterior.hora_abertura
        hora_abertura_atual = chamado_atual.hora_abertura

        if isinstance(hora_abertura_anterior, str):
            hora_abertura_anterior = datetime.strptime(hora_abertura_anterior, '%d/%m/%Y %H:%M:%S')
        if isinstance(hora_abertura_atual, str):
            hora_abertura_atual = datetime.strptime(hora_abertura_atual, '%d/%m/%Y %H:%M:%S')

        return hora_abertura_atual - hora_abertura_anterior
    except Exception as e:
        logging.error(f"Erro ao calcular tempo decorrido entre chamados consecutivos: {e}")
        return None
