# chamados.py
import os
from datetime import datetime, timedelta
from twilio.rest import Client
import streamlit as st
import pandas as pd
from fpdf import FPDF
from io import BytesIO
import matplotlib.pyplot as plt
import seaborn as sns
import tempfile
import logging
from logging.handlers import RotatingFileHandler
from database import Chamado, SessionLocal, Inventario, PecaUsada, HistoricoManutencao
from sqlalchemy import desc
from workalendar.america import Brazil
from zoneinfo import ZoneInfo
from dateutil import parser

# Configuração do logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler_file = RotatingFileHandler("chamados.log", maxBytes=5*1024*1024, backupCount=5)
handler_file.setFormatter(formatter)
handler_stream = logging.StreamHandler()
handler_stream.setFormatter(formatter)
logger.addHandler(handler_file)
logger.addHandler(handler_stream)

# Definir o fuso horário local
local_tz = ZoneInfo('America/Sao_Paulo')

# Configurações de autenticação do Twilio usando variáveis de ambiente
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
if account_sid and auth_token:
    client = Client(account_sid, auth_token)
    twilio_from = os.getenv('TWILIO_FROM')
    twilio_to_numbers = os.getenv('TWILIO_TO_NUMBERS', '').split(',')
else:
    client = None
    logger.warning("Credenciais do Twilio não configuradas. Mensagens não serão enviadas.")

def gerar_protocolo_sequencial():
    with SessionLocal() as session:
        try:
            max_protocolo = session.query(Chamado).order_by(desc(Chamado.protocolo)).first()
            protocolo = max_protocolo.protocolo + 1 if max_protocolo else 1
            return protocolo
        except Exception as e:
            logger.error(f"Erro ao gerar protocolo sequencial: {e}")
            return None

def get_chamado_by_protocolo(protocolo):
    with SessionLocal() as session:
        try:
            chamado = session.query(Chamado).filter(Chamado.protocolo == protocolo).first()
            logger.info(f"Chamado buscado pelo protocolo {protocolo}: {'Encontrado' if chamado else 'Não encontrado'}")
            return chamado
        except Exception as e:
            logger.error(f"Erro ao buscar chamado por protocolo {protocolo}: {e}")
            return None

def buscar_no_inventario_por_patrimonio(patrimonio):
    with SessionLocal() as session:
        try:
            inventario = session.query(Inventario).filter(Inventario.numero_patrimonio == patrimonio).first()
            if inventario:
                logger.info(f"Máquina encontrada no inventário: Patrimônio {patrimonio}")
                return {
                    'tipo': inventario.tipo,
                    'marca': inventario.marca,
                    'modelo': inventario.modelo,
                    'patrimonio': inventario.numero_patrimonio,
                    'localizacao': inventario.localizacao,
                    'setor': inventario.setor
                }
            logger.info(f"Número de patrimônio {patrimonio} não encontrado no inventário.")
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar patrimônio {patrimonio} no inventário: {e}")
            return None

def add_chamado(username, ubs, setor, tipo_defeito, problema, machine=None, patrimonio=None):
    protocolo = gerar_protocolo_sequencial()
    if protocolo is None:
        st.error("Não foi possível gerar um protocolo para o chamado. Tente novamente mais tarde.")
        return

    hora_abertura = datetime.now(tz=local_tz)

    with SessionLocal() as session:
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
            logger.info(f"Chamado aberto: Protocolo {protocolo} por usuário {username}")

            if client and twilio_from and twilio_to_numbers:
                for numero in twilio_to_numbers:
                    numero = numero.strip()
                    if numero:
                        try:
                            message = client.messages.create(
                                from_=twilio_from,
                                body=f"Novo chamado técnico na UBS '{ubs}' no setor '{setor}': {problema}",
                                to=numero
                            )
                            logger.info(f"Mensagem enviada para {numero} via WhatsApp. SID: {message.sid}")
                        except Exception as e:
                            logger.error(f"Erro ao enviar mensagem para {numero} via WhatsApp: {e}")
            else:
                logger.warning("Cliente Twilio não configurado ou números de destino não fornecidos.")

            st.success(f"Chamado aberto com sucesso! Protocolo: {protocolo}")
        except Exception as e:
            session.rollback()
            logger.error(f"Erro ao adicionar chamado: {e}")
            st.error("Erro interno ao abrir chamado. Tente novamente mais tarde.")

def calcular_tempo_decorrido(hora_abertura, hora_fechamento):
    try:
        cal = Brazil()
        total_seconds = 0

        if hora_fechamento is None or pd.isnull(hora_fechamento):
            hora_fechamento = datetime.now(tz=local_tz)

        if isinstance(hora_abertura, str):
            hora_abertura = parser.parse(hora_abertura)
        if isinstance(hora_fechamento, str):
            hora_fechamento = parser.parse(hora_fechamento)

        if hora_abertura.tzinfo is None:
            hora_abertura = hora_abertura.replace(tzinfo=local_tz)
        if hora_fechamento.tzinfo is None:
            hora_fechamento = hora_fechamento.replace(tzinfo=local_tz)

        current = hora_abertura

        while current < hora_fechamento:
            if cal.is_working_day(current.date()):
                start_of_day = current.replace(hour=8, minute=0, second=0, microsecond=0)
                end_of_day = current.replace(hour=17, minute=0, second=0, microsecond=0)
                lunch_start_time = current.replace(hour=12, minute=0, second=0, microsecond=0)
                lunch_end_time = current.replace(hour=13, minute=0, second=0, microsecond=0)

                if current < start_of_day:
                    current = start_of_day

                if current >= end_of_day:
                    current += timedelta(days=1)
                    continue

                interval_start = current
                interval_end = min(hora_fechamento, end_of_day)

                if interval_start < lunch_start_time < interval_end:
                    total_seconds += (lunch_start_time - interval_start).total_seconds()
                    interval_start = lunch_end_time

                if interval_start < lunch_end_time < interval_end:
                    interval_start = lunch_end_time

                if interval_start >= interval_end:
                    current += timedelta(days=1)
                    continue

                total_seconds += (interval_end - interval_start).total_seconds()

            current = current.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

        return total_seconds
    except Exception as e:
        logger.error(f"Erro ao calcular tempo decorrido: {e}")
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

        return tempo_formatado.strip()
    except Exception as e:
        logger.error(f"Erro ao formatar tempo: {e}")
        return "Erro no formato"

def calculate_average_time(chamados):
    total_tempo = 0
    total_chamados_finalizados = 0
    for chamado in chamados:
        if chamado.hora_abertura and chamado.hora_fechamento:
            tempo_segundos = calcular_tempo_decorrido(chamado.hora_abertura, chamado.hora_fechamento)
            if tempo_segundos is not None:
                total_tempo += tempo_segundos
                total_chamados_finalizados += 1
    if total_chamados_finalizados > 0:
        media_tempo = total_tempo / total_chamados_finalizados
        logger.info(f"Tempo médio de atendimento calculado: {media_tempo} segundos")
    else:
        media_tempo = 0
        logger.info("Nenhum chamado finalizado para calcular tempo médio de atendimento.")
    return media_tempo

def show_average_time(chamados):
    if chamados:
        media_tempo_segundos = calculate_average_time(chamados)
        tempo_formatado = formatar_tempo(media_tempo_segundos)
        st.write(f'Tempo médio de atendimento: {tempo_formatado}')
    else:
        st.write('Nenhum chamado finalizado para calcular o tempo médio.')

def finalizar_chamado(id_chamado, solucao, pecas_usadas=None):
    hora_fechamento = datetime.now(tz=local_tz)
    with SessionLocal() as session:
        try:
            chamado = session.query(Chamado).filter(Chamado.id == id_chamado).first()
            if chamado:
                chamado.solucao = solucao
                chamado.hora_fechamento = hora_fechamento

                if pecas_usadas:
                    for peca in pecas_usadas:
                        peca_usada = PecaUsada(
                            chamado_id=id_chamado,
                            peca_nome=peca,
                            data_uso=hora_fechamento
                        )
                        session.add(peca_usada)

                if chamado.patrimonio:
                    inventario = session.query(Inventario).filter(Inventario.numero_patrimonio == chamado.patrimonio).first()
                    if inventario:
                        descricao_manutencao = f"Manutenção realizada: {solucao}. Peças usadas: {', '.join(pecas_usadas) if pecas_usadas else 'Nenhuma'}."
                        historico = HistoricoManutencao(
                            numero_patrimonio=chamado.patrimonio,
                            descricao=descricao_manutencao,
                            data_manutencao=hora_fechamento
                        )
                        session.add(historico)
                    else:
                        logger.error(f"Patrimônio {chamado.patrimonio} não encontrado no inventário.")
                        st.error(f"Patrimônio {chamado.patrimonio} não encontrado no inventário. Histórico de manutenção não foi criado.")
                else:
                    logger.warning(f"Chamado ID {id_chamado} não possui 'patrimonio'. Histórico de manutenção não foi criado.")

                session.commit()

                st.success(f'Chamado ID: {id_chamado} finalizado com sucesso!')
                logger.info(f"Chamado ID: {id_chamado} finalizado.")
            else:
                st.error("Chamado não encontrado.")
                logger.warning(f"Chamado ID {id_chamado} não encontrado.")
        except Exception as e:
            session.rollback()
            logger.error(f"Erro ao finalizar chamado ID {id_chamado}: {e}")
            st.error("Erro interno ao finalizar chamado. Tente novamente mais tarde.")

def list_chamados():
    with SessionLocal() as session:
        try:
            chamados = session.query(Chamado).all()
            logger.info("Lista de todos os chamados recuperada.")
            return chamados
        except Exception as e:
            logger.error(f"Erro ao listar chamados: {e}")
            return []

def list_chamados_em_aberto():
    with SessionLocal() as session:
        try:
            chamados = session.query(Chamado).filter(Chamado.hora_fechamento == None).all()
            logger.info("Lista de chamados em aberto recuperada.")
            return chamados
        except Exception as e:
            logger.error(f"Erro ao listar chamados em aberto: {e}")
            return []

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
    df['Hora Abertura'] = pd.to_datetime(df['Hora Abertura'], errors='coerce')
    df['Hora Fechamento'] = pd.to_datetime(df['Hora Fechamento'], errors='coerce')
    df['Mês'] = df['Hora Abertura'].dt.to_period('M')
    months_list = df['Mês'].astype(str).unique().tolist()
    logger.info("Dados mensais dos chamados técnicos preparados.")
    return df, months_list

def save_plot_to_temp_file():
    try:
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmpfile:
            plt.savefig(tmpfile.name, format='png')
            plt.close()
            logger.info(f"Gráfico salvo temporariamente em {tmpfile.name}")
            return tmpfile.name
    except Exception as e:
        logger.error(f"Erro ao salvar gráfico temporariamente: {e}")
        return None

def add_image_to_pdf(pdf, image_path, title):
    try:
        pdf.set_font('Arial', 'B', 12)
        pdf.ln(10)
        pdf.cell(0, 10, title, ln=True, align='C')
        pdf.image(image_path, x=10, y=pdf.get_y() + 10, w=270)
        os.remove(image_path)
        logger.info(f"Imagem {title} adicionada ao PDF e arquivo temporário removido.")
    except Exception as e:
        logger.error(f"Erro ao adicionar imagem {title} ao PDF: {e}")

def generate_monthly_report(df, selected_month, pecas_usadas_df=None, logo_path=None):
    try:
        if not isinstance(df, pd.DataFrame):
            raise ValueError("O argumento 'df' não é um DataFrame")

        if pecas_usadas_df is None or not isinstance(pecas_usadas_df, pd.DataFrame):
            logger.warning("O argumento 'pecas_usadas_df' não é um DataFrame ou é None.")
            pecas_usadas_df = pd.DataFrame(columns=['chamado_id', 'peca_nome'])

        df = df.dropna(subset=['Hora Abertura'])

        selected_year_int = int(selected_month[:4])
        selected_month_int = int(selected_month[5:7])

        df_filtered = df[
            (df['Hora Abertura'].dt.year == selected_year_int) &
            (df['Hora Abertura'].dt.month == selected_month_int)
        ]

        if df_filtered.empty:
            st.warning(f"Não há dados para o mês selecionado: {selected_month}.")
            logger.info(f"Relatório mensal: nenhum dado para {selected_month}.")
            return None

        df_filtered['Tempo Decorrido (s)'] = df_filtered.apply(
            lambda row: calcular_tempo_decorrido(row['Hora Abertura'], row['Hora Fechamento']), axis=1
        )

        df_filtered = df_filtered.dropna(subset=['Tempo Decorrido (s)'])

        if df_filtered.empty:
            st.warning("Nenhum dado disponível após o cálculo do tempo decorrido.")
            logger.info("Nenhum dado disponível após o cálculo do tempo decorrido.")
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
            logger.warning("Logotipo não encontrado para inserção no relatório.")

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
        col_widths = [20, 40, 40, 35, 50, 30, 30, 30, 40]

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
            problema = str(row['Problema'])[:47] + '...' if len(str(row['Problema'])) > 50 else str(row['Problema'])
            pdf.cell(col_widths[4], 8, problema, border=1, align='L')
            hora_abertura_formatada = row['Hora Abertura'].astimezone(local_tz).strftime('%d/%m/%Y %H:%M:%S') if pd.notnull(row['Hora Abertura']) else '-'
            hora_fechamento_formatada = row['Hora Fechamento'].astimezone(local_tz).strftime('%d/%m/%Y %H:%M:%S') if pd.notnull(row['Hora Fechamento']) else '-'
            pdf.cell(col_widths[5], 8, hora_abertura_formatada, border=1, align='C')
            pdf.cell(col_widths[6], 8, hora_fechamento_formatada, border=1, align='C')
            tempo_formatado = formatar_tempo(row['Tempo Decorrido (s)'])
            pdf.cell(col_widths[7], 8, tempo_formatado, border=1, align='C')
            peca_nome = str(row['peca_nome'])[:37] + '...' if len(str(row['peca_nome'])) > 40 else str(row['peca_nome'])
            pdf.cell(col_widths[8], 8, peca_nome, border=1, align='L')
            pdf.ln()

        pdf_content = pdf.output(dest='S').encode('latin1')
        pdf_output = BytesIO(pdf_content)

        logger.info(f"Relatório mensal de chamados técnicos gerado para {selected_month}")
        return pdf_output
    except Exception as e:
        logger.error(f"Erro ao gerar relatório mensal: {e}")
        st.error("Erro ao gerar relatório. Tente novamente mais tarde.")
        return None
