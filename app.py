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

# Carregar dados existentes ou criar um novo com as novas colunas necessárias
if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
    df['data_consulta'] = pd.to_datetime(df['data_consulta']).dt.date
    # Garantir que colunas novas existam para bases antigas
    if 'status_retorno' not in df.columns:
        df['status_retorno'] = 'PENDENTE'
else:
    df = pd.DataFrame(columns=["nome", "whatsapp", "data_consulta", "status_retorno"])

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
                    "status_retorno": "PENDENTE" # Inicia precisando de retorno
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

# Filtros inteligentes baseados no status real do paciente:
# Alerta 1: Só mostra quem está PENDENTE (ainda não fez o retorno grátis) e na janela de 20 a 30 dias
retornos_pendentes = df[(df['status_retorno'] == 'PENDENTE') & (df['dias_desde_consulta'] >= 20) & (df['dias_desde_consulta'] <= 30)]

# Alerta 2: Só mostra para Reengajamento quem JÁ REALIZOU o retorno grátis e sumiu há mais de 60 dias daquela data
reengajamento_pendente = df[(df['status_retorno'] == 'RETORNO_REALIZADO') & (df['dias_desde_consulta'] >= 60)]


# --- ABA 1: DASHBOARD DA SECRETÁRIA ---
with aba_dashboard:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("⏳ Agendar Retorno Grátis (20 a 30 dias)")
        st.caption("Pacientes que fizeram a consulta principal e ainda não usaram o retorno.")
        
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
                    
                    c1, c2 = st.columns(2)
                    c1.link_button("💬 Chamar no WhatsApp", link_wa, type="primary")
                    if c2.button("Confirmar Retorno Realizado", key=f"btn_ret_{idx}"):
                        df.at[idx, 'status_retorno'] = 'RETORNO_REALIZADO'
                        # Atualiza a data para o dia de hoje (dia em que o retorno aconteceu) para contar os 60 dias a partir daqui
                        df.at[idx, 'data_consulta'] = data_atual 
                        df.to_csv(DATA_FILE, index=False)
                        st.success("Marcado como Retorno Realizado!")
                        st.rerun()

    with col2:
st.subheader("🔥 Reengajamento: Nova Consulta Paga (60+ dias)")
st.subheader("📋 Todos os Pacientes Cadastrados")
if not df.empty:
    st.dataframe(df[["nome", "whatsapp", "data_consulta", "status_retorno"]], use_container_width=True)
else:
    st.write("Nenhum paciente cadastrado ainda.")
