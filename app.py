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

# CORREÇÃO AQUI: Forçar a coluna 'whatsapp' a ser lida estritamente como string (texto)
if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE, dtype={"whatsapp": str})
    df['data_consulta'] = pd.to_datetime(df['data_consulta']).dt.date
    if 'status_retorno' not in df.columns:
        df['status_retorno'] = 'PENDENTE'
else:
    df = pd.DataFrame(columns=["nome", "whatsapp", "data_consulta", "status_retorno"])
    df['whatsapp'] = df['whatsapp'].astype(str)

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
                    "whatsapp": str(whatsapp_limpo),
                    "data_consulta": data_consulta,
                    "status_retorno": "PENDENTE"
                }])
                df = pd.concat([df, novo_registro], ignore_index=True)
                df.to_csv(DATA_FILE, index=False)
                st.success(f"✅ {nome} cadastrado com sucesso!")
                st.rerun()
            else:
                st.error("Por favor, preencha o Nome e o WhatsApp.")

# --- LÓGICA DE TEMPO (TODAS AS REGRAS COMBINADAS) ---
data_atual = datetime.today().date()
if not df.empty:
    df['dias_desde_consulta'] = df['data_consulta'].apply(lambda x: (data_atual - x).days)
else:
    df['dias_desde_consulta'] = 0

# 1. Retorno Grátis: Pendente entre 0 e 30 dias
retornos_pendentes = df[(df['status_retorno'] == 'PENDENTE') & (df['dias_desde_consulta'] >= 0) & (df['dias_desde_consulta'] <= 30)]

# 2. Preventivo Pago: Fez retorno e está entre 30 e 60 dias
reeng_preventivo = df[(df['status_retorno'] == 'RETORNO_REALIZADO') & (df['dias_desde_consulta'] >= 30) & (df['dias_desde_consulta'] <= 60)]

# 3. Crítico Pago (Mais de 60 dias): Fez retorno e passou de 60 dias
reeng_critico = df[(df['status_retorno'] == 'RETORNO_REALIZADO') & (df['dias_desde_consulta'] > 60)]

# 4. Retorno Expirado: Pendente há mais de 30 dias
reeng_sem_retorno = df[(df['status_retorno'] == 'PENDENTE') & (df['dias_desde_consulta'] > 30)]


# --- ABA 1: DASHBOARD DA SECRETÁRIA ---
with aba_dashboard:
    col1, col2 = st.columns(2)
    
    # --- COLUNA 1: RETORNOS GRATUITOS ---
    with col1:
        st.subheader("⏳ Agendar Retorno Grátis (Até 30 dias)")
        st.caption("Pacientes dentro do prazo legal para agendar o retorno gratuito.")
        
        if retornos_pendentes.empty:
            st.info("Nenhum paciente pendente de retorno nesta janela.")
        else:
            for idx, row in retornos_pendentes.iterrows():
                with st.container(border=True):
                    st.write(f"👤 **{row['nome']}**")
                    st.write(f"📅 Consultou há: {row['dias_desde_consulta']} dias ({row['data_consulta'].strftime('%d/%m/%Y')})")
                    
                    msg = f"Olá {row['nome']}, tudo bem? Identificamos que sua consulta completou {row['dias_desde_consulta']} dias. Vamos agendar seu retorno gratuito para esta semana?"
                    msg_encoded = urllib.parse.quote(msg)
                    link_wa = f"https://wa.me/55{row['whatsapp']}?text={msg_encoded}"
                    link_agenda = gerar_link_google_agenda(row['nome'], "Retorno Gratuito")
                    
                    st.link_button("💬 Chamar no WhatsApp", link_wa, type="primary", use_container_width=True)
                    
                    c1, c2 = st.columns(2)
                    c1.link_button("📆 Abrir Google Agenda", link_agenda, use_container_width=True)
                    if c2.button("Confirmar Retorno", key=f"btn_ret_{idx}", use_container_width=True):
                        df.at[idx, 'status_retorno'] = 'RETORNO_REALIZADO'
                        df.at[idx, 'data_consulta'] = data_atual 
                        df.to_csv(DATA_FILE, index=False)
                        st.success("Marcado como Retorno Realizado!")
                        st.rerun()

    # --- COLUNA 2: REENGAJAMENTO / CONSULTAS PAGAS ---
    with col2:
        st.subheader("🔥 Reengajamento: Nova Consulta Paga")
        st.caption("Pacientes que precisam agendar consultas pagantes para dar continuidade.")
        
        # SUB-SESSÃO A: PREVENTIVO (30 a 60 dias pós-retorno)
        st.markdown("##### 🔁 Agendamento Preventivo (30 a 60 dias pós-retorno)")
        if reeng_preventivo.empty:
            st.caption("Nenhum paciente nesta janela de antecipação hoje.")
        else:
            for idx, row in reeng_preventivo.iterrows():
                with st.container(border=True):
                    st.write(f"👤 **{row['nome']}**")
                    st.write(f"⏳ Retorno realizado há: {row['dias_desde_consulta']} dias")
                    
                    msg = f"Olá {row['nome']}, tudo bem? Como o seu último retorno completou {row['dias_desde_consulta']} dias, estamos entrando em contato para deixar programada sua próxima consulta de acompanhamento com o doutor para as próximas semanas. Qual o melhor dia para você?"
                    msg_encoded = urllib.parse.quote(msg)
                    link_wa = f"https://wa.me/55{row['whatsapp']}?text={msg_encoded}"
                    link_agenda = gerar_link_google_agenda(row['nome'], "Consulta Paga (Prevenção)")
                    
                    st.link_button("💬 Antecipar Agendamento Pago", link_wa, type="secondary", use_container_width=True)
                    
                    c1, c2 = st.columns(2)
                    c1.link_button("📆 Abrir Google Agenda", link_agenda, use_container_width=True)
                    if c2.button("Nova Consulta Confirmada", key=f"btn_reeng_prev_{idx}", use_container_width=True):
                        df.at[idx, 'status_retorno'] = 'PENDENTE'
                        df.at[idx, 'data_consulta'] = data_atual
                        df.to_csv(DATA_FILE, index=False)
                        st.success("Novo ciclo iniciado!")
                        st.rerun()
                        
        st.markdown("---")
        
        # SUB-SESSÃO B: CRÍTICO (Mais de 60 dias pós-retorno)
        st.markdown("##### 🚨 Sumidos há mais de 60 dias (Pós-Retorno)")
        if reeng_critico.empty:
            st.caption("Nenhum paciente crítico sumido hoje.")
        else:
            for idx, row in reeng_critico.iterrows():
                with st.container(border=True):
                    st.write(f"👤 **{row['nome']}**")
                    st.write(f"🔥 Último contato há: {row['dias_desde_consulta']} dias (Passou do prazo ideal de 60 dias)")
                    
                    msg = f"Olá {row['nome']}, faz um tempo desde sua última consulta de retorno! Como tem passado? Gostaria de agendar uma nova consulta de acompanhamento com o doutor?"
                    msg_encoded = urllib.parse.quote(msg)
                    link_wa = f"https://wa.me/55{row['whatsapp']}?text={msg_encoded}"
                    link_agenda = gerar_link_google_agenda(row['nome'], "Consulta Paga (Reengajamento)")
                    
                    st.link_button("💬 Chamar para Consulta Paga", link_wa, type="secondary", use_container_width=True)
                    
                    c1, c2 = st.columns(2)
                    c1.link_button("📆 Abrir Google Agenda", link_agenda, use_container_width=True)
                    if c2.button("Reiniciar Ciclo", key=f"btn_reeng_crit_{idx}", use_container_width=True):
                        df.at[idx, 'status_retorno'] = 'PENDENTE'
                        df.at[idx, 'data_consulta'] = data_atual
                        df.to_csv(DATA_FILE, index=False)
                        st.success("Novo ciclo iniciado!")
                        st.rerun()
                        
        st.markdown("---")
        
        # SUB-SESSÃO C: RETORNO EXPIRADO (Passou de 30 dias da principal sem retorno)
        st.markdown("##### ⚠️ Perderam o Prazo do Retorno (Expirado)")
        if reeng_sem_retorno.empty:
            st.caption("Nenhum paciente com prazo expirado hoje.")
        else:
            for idx, row in reeng_sem_retorno.iterrows():
                with st.container(border=True):
                    st.write(f"👤 **{row['nome']}**")
                    st.write(f"🚨 Consultou há: {row['dias_desde_consulta']} dias (Prazo de 30 dias expirou)")
                    
                    msg = f"Olá {row['nome']}, tudo bem? Vimos que seu prazo para o retorno gratuito de 30 dias expirou. Como você está se sentindo? Caso precise dar continuidade ao tratamento, podemos agendar uma nova consulta?"
                    msg_encoded = urllib.parse.quote(msg)
                    link_wa = f"https://wa.me/55{row['whatsapp']}?text={msg_encoded}"
                    link_agenda = gerar_link_google_agenda(row['nome'], "Consulta Paga (Retorno Expirado)")
                    
                    st.link_button("💬 Oferecer Nova Consulta", link_wa, type="secondary", use_container_width=True)
                    
                    c1, c2 = st.columns(2)
                    c1.link_button("📆 Abrir Google Agenda", link_agenda, use_container_width=True)
                    if c2.button("Reativar Paciente", key=f"btn_reeng_exp_{idx}", use_container_width=True):
                        df.at[idx, 'status_retorno'] = 'PENDENTE'
                        df.at[idx, 'data_consulta'] = data_atual
                        df.to_csv(DATA_FILE, index=False)
                        st.success("Paciente reativado no fluxo de consultas!")
                        st.rerun()

# --- ABA 3: GERENCIAMENTO (EDITAR E EXCLUIR) ---
with aba_gerenciamento:
    st.header("⚙️ Editar ou Corrigir Lançamentos")
    
    if df.empty:
        st.write("Nenhum paciente cadastrado.")
    else:
        # Garantir que a coluna whatsapp seja interpretada temporariamente como string na visualização
        df['whatsapp'] = df['whatsapp'].astype(str)
        
        lista_pacientes = df['nome'].tolist()
        paciente_selecionado = st.selectbox("Selecione o paciente que deseja alterar:", lista_pacientes)
        
        idx_edicao = df[df['nome'] == paciente_selecionado].index[0]
        
        with st.form("form_edicao"):
            st.write(f"### Editando os dados de: {paciente_selecionado}")
            novo_nome = st.text_input("Nome:", value=df.at[idx_edicao, 'nome'])
            novo_whatsapp = st.text_input("WhatsApp:", value=str(df.at[idx_edicao, 'whatsapp']))
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
                # CORREÇÃO DEFINITIVA: Força a coluna inteira a aceitar objetos/strings antes de injetar o valor
                df['whatsapp'] = df['whatsapp'].astype(str)
                whatsapp_filtrado = "".join(filter(str.isdigit, novo_whatsapp))
                
                df.at[idx_edicao, 'nome'] = novo_nome
                df.at[idx_edicao, 'whatsapp'] = str(whatsapp_filtrado)
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
