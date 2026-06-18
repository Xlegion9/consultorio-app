import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse

# Configuração da página
st.set_page_config(page_title="Gestão de Retornos", layout="wide")
st.title("🏥 Sistema Avançado de Controle de Retornos e Reengajamento")

# Arquivo para salvar os dados
DATA_FILE = "pacientes_dados.csv"

# Carregar dados existentes ou criar um novo
if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
    df['data_consulta'] = pd.to_datetime(df['data_consulta']).dt.date
    if 'status_retorno' not in df.columns:
        df['status_retorno'] = 'PENDENTE'
else:
    df = pd.DataFrame(columns=["nome", "whatsapp", "data_consulta", "status_retorno"])

# --- FUNÇÃO PARA GERAR LINK DO GOOGLE AGENDA ---
def gerar_link_google_agenda(nome_paciente, tipo_atendimento):
    titulo = f"{tipo_atendimento} - {nome_paciente}"
    detalhes = f"Agendamento realizado via Sistema de Retornos."
    titulo_enc = urllib.parse.quote(titulo)
    detalhes_enc = urllib.parse.quote(detalhes)
    return f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={titulo_enc}&details={detalhes_enc}"

# --- ABAS PRINCIPAIS DO SISTEMA ---
aba_dashboard, aba_cadastro, aba_gerenciamento = st.tabs([
    "📊 Painel de Controle", 
    "📝 Novo Atendimento", 
    "⚙️ Editar Pacientes e Lançamentos"
])

# --- ABA 2: CADASTRO DE PACIENTE ---
with aba_cadastro:
    st.header("Cadastrar Nova Consulta Principal")
    with st.form("form_cadastro", clear_on_submit=True):
        nome = st.text_input("Nome do Paciente:")
        whatsapp = st.text_input("WhatsApp (com DDD, apenas números):", placeholder="11999999999")
        data_consulta = st.date_input("Data da Consulta Principal:", value=datetime.today().date())
        
        enviado = st.form_submit_button("Salvar Paciente")
        if enviado:
            if nome and whatsapp:
                whatsapp_limpo = "".join(filter(str.isdigit, whatsapp))
                novo_registro = pd.DataFrame([{
                    "nome": nome,
                    "whatsapp": whatsapp_limpo,
                    "data_consulta": data_consulta,
                    "status_retorno": "PENDENTE"
                }])
                df = pd.concat([df, novo_registro], ignore_index=True)
                df.to_csv(DATA_FILE, index=False)
                st.success(f"✅ {nome} cadastrado com sucesso!")
                st.rerun()
            else:
                st.error("Por favor, preencha o Nome e o WhatsApp.")

# --- LÓGICA DE TEMPO (ALERTAS) ---
data_atual = datetime.today().date()
if not df.empty:
    df['dias_desde_consulta'] = df['data_consulta'].apply(lambda x: (data_atual - x).days)
else:
    df['dias_desde_consulta'] = 0

# Exibe todos de 0 até 30 dias com retorno pendente
retornos_pendentes = df[(df['status_retorno'] == 'PENDENTE') & (df['dias_desde_consulta'] >= 0) & (df['dias_desde_consulta'] <= 30)]
reengajamento_pendente = df[(df['status_retorno'] == 'RETORNO_REALIZADO') & (df['dias_desde_consulta'] >= 60)]

# --- ABA 1: DASHBOARD DA SECRETÁRIA ---
with aba_dashboard:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("⏳ Agendar Retorno Grátis (Até 30 dias)")
        st.caption("Todos os pacientes que consultaram nos últimos 30 dias e ainda estão com retorno pendente.")
        
        if retornos_pendentes.empty:
            st.info("Nenhum paciente pendente de retorno nesta janela para hoje.")
        else:
            for idx, row in retornos_pendentes.iterrows():
                with st.container(border=True):
                    st.write(f"👤 **{row['nome']}**")
                    st.write(f"📅 Consultou em: {row['data_consulta'].strftime('%d/%m/%Y')} ({row['dias_desde_consulta']} dias atrás)")
                    
                    msg = f"Olá {row['nome']}, tudo bem? Identificamos que sua consulta completou {row['dias_desde_consulta']} dias. Vamos agendar seu retorno gratuito para esta semana?"
                    msg_encoded = urllib.parse.quote(msg)
                    link_wa = f"https://wa.me/55{row['whatsapp']}?text={msg_encoded}"
                    link_agenda = gerar_link_google_agenda(row['nome'], "Retorno Gratuito")
                    
                    # Botões de Ação Restaurados
                    st.link_button("💬 Chamar no WhatsApp", link_wa, type="primary", use_container_width=True)
                    
                    c1, c2 = st.columns(2)
                    c1.link_button("📆 Abrir Google Agenda", link_agenda, use_container_width=True)
                    if c2.button("Confirmar Retorno", key=f"btn_ret_{idx}", use_container_width=True):
                        df.at[idx, 'status_retorno'] = 'RETORNO_REALIZADO'
                        df.at[idx, 'data_consulta'] = data_atual 
                        df.to_csv(DATA_FILE, index=False)
                        st.success("Marcado como Retorno Realizado!")
                        st.rerun()

    with col2:
        st.subheader("🔥 Reengajamento: Nova Consulta Paga (60+ dias)")
        st.caption("Pacientes que já fizeram o retorno grátis, mas estão sumidos há mais de 60 dias.")
        
        if reengajamento_pendente.empty:
            st.info("Nenhum paciente elegível para captação/nova consulta hoje.")
        else:
            for idx, row in reengajamento_pendente.iterrows():
                with st.container(border=True):
                    st.write(f"👤 **{row['nome']}**")
                    st.write(f"⏳ Último retorno/contato há {row['dias_desde_consulta']} dias.")
                    
                    msg = f"Olá {row['nome']}, faz um tempo desde sua última consulta de retorno! Como tem passado? Gostaria de agendar uma nova consulta de acompanhamento com o doutor?"
                    msg_encoded = urllib.parse.quote(msg)
                    link_wa = f"https://wa.me/55{row['whatsapp']}?text={msg_encoded}"
                    link_agenda = gerar_link_google_agenda(row['nome'], "Consulta Paga (Reengajamento)")
                    
                    # Botões de Ação Restaurados
                    st.link_button("💬 Chamar para Consulta Paga", link_wa, type="secondary", use_container_width=True)
                    
                    c1, c2 = st.columns(2)
                    c1.link_button("📆 Abrir Google Agenda", link_agenda, use_container_width=True)
                    if c2.button("Reiniciar Ciclo", key=f"btn_reeng_{idx}", use_container_width=True):
                        df.at[idx, 'status_retorno'] = 'PENDENTE'
                        df.at[idx, 'data_consulta'] = data_atual
                        df.to_csv(DATA_FILE, index=False)
                        st.success("Novo ciclo de consulta iniciado!")
                        st.rerun()

# --- ABA 3: GERENCIAMENTO (EDITAR E EXCLUIR) ---
with aba_gerenciamento:
    st.header("⚙️ Editar ou Corrigir Lançamentos")
    
    if df.empty:
        st.write("Nenhum paciente cadastrado.")
    else:
        lista_pacientes = df['nome'].tolist()
        paciente_selecionado = st.selectbox("Selecione o paciente que deseja alterar:", lista_pacientes)
        
        idx_edicao = df[df['nome'] == paciente_selecionado].index[0]
        
        with st.form("form_edicao"):
            st.write(f"### Editando os dados de: {paciente_selecionado}")
            novo_nome = st.text_input("Nome:", value=df.at[idx_edicao, 'nome'])
            novo_whatsapp = st.text_input("WhatsApp:", value=df.at[idx_edicao, 'whatsapp'])
            nova_data = st.date_input("Data do Último Evento/Consulta:", value=df.at[idx_edicao, 'data_consulta'])
            
            novo_status = st.selectbox(
                "Status Atual do Paciente:", 
                ["PENDENTE", "RETORNO_REALIZADO"],
                index=0 if df.at[idx_edicao, 'status_retorno'] == 'PENDENTE' else 1
            )
            
            c_salvar, c_excluir = st.columns([1, 4])
            
            salvou = c_salvar.form_submit_button("Salvar Alterações", type="primary")
            excluiu = c_excluir.form_submit_button("❌ Excluir Paciente", type="secondary")
            
            if salvou:
                df.at[idx_edicao, 'nome'] = novo_nome
                df.at[idx_edicao, 'whatsapp'] = "".join(filter(str.isdigit, novo_whatsapp))
                df.at[idx_edicao, 'data_consulta'] = nova_data
                df.at[idx_edicao, 'status_retorno'] = novo_status
                df.to_csv(DATA_FILE, index=False)
                st.success("Dados atualizados com sucesso!")
                st.rerun()
                
            if excluiu:
                df = df.drop(idx_edicao).reset_index(drop=True)
                df.to_csv(DATA_FILE, index=False)
                st.warning("Paciente removido do sistema.")
                st.rerun()

    st.markdown("---")
    st.subheader("📋 Visualização Geral do Banco de Dados")
    st.dataframe(df[["nome", "whatsapp", "data_consulta", "status_retorno"]], use_container_width=True)
