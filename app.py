import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import urllib.parse

# Configuração da página
st.set_page_config(page_title="Gestão de Retornos", layout="wide")
st.title("🏥 Sistema de Controle de Retornos e Reengajamento")

# Arquivo para salvar os dados (Banco de dados ultra simples em arquivo)
DATA_FILE = "pacientes_dados.csv"

# Carregar dados existentes ou criar um novo
if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
    df['data_consulta'] = pd.to_datetime(df['data_consulta']).dt.date
else:
    df = pd.DataFrame(columns=["nome", "whatsapp", "data_consulta", "status_retorno"])

# --- TELA 1: CADASTRO DE PACIENTE ---
st.sidebar.header("📝 Cadastrar Novo Atendimento")
with st.sidebar.form("form_cadastro", clear_on_submit=True):
    nome = st.text_input("Nome do Paciente:")
    whatsapp = st.text_input("WhatsApp (com DDD, apenas números):", placeholder="11999999999")
    data_consulta = st.date_input("Data da Consulta Principal:", value=datetime.today().date())
    
    enviado = st.form_submit_button("Salvar Paciente")
    if enviado:
        if nome and whatsapp:
            # Limpar o número de whatsapp de espaços ou caracteres
            whatsapp_limpo = "".join(filter(str.isdigit, whatsapp))
            novo_registro = pd.DataFrame([{
                "nome": nome,
                "whatsapp": whatsapp_limpo,
                "data_consulta": data_consulta,
                "status_retorno": "PENDENTE"
            }])
            df = pd.concat([df, novo_registro], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)
            st.sidebar.success(f"✅ {nome} cadastrado com sucesso!")
            st.rerun()
        else:
            st.sidebar.error("Por favor, preencha o Nome e o WhatsApp.")

# --- LÓGICA DE PROCESSAMENTO DOS ALERTAS ---
data_atual = datetime.today().date()

# Criar colunas para calcular os prazos
if not df.empty:
    df['dias_desde_consulta'] = df['data_consulta'].apply(lambda x: (data_atual - x).days)
else:
    df['dias_desde_consulta'] = 0

# Filtro 1: Retorno Grátis (Entre 20 e 30 dias da consulta e ainda PENDENTE)
retornos_pendentes = df[(df['status_retorno'] == 'PENDENTE') & (df['dias_desde_consulta'] >= 20) & (df['dias_desde_consulta'] <= 30)]

# Filtro 2: Reengajamento (Mais de 60 dias da consulta)
reengajamento_pendente = df[(df['dias_desde_consulta'] >= 60)]

# --- TELA 2: DASHBOARD DA SECRETÁRIA ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("⏳ Gerar Retorno (20 a 30 dias)")
    st.caption("Pacientes que precisam agendar o retorno gratuito logo.")
    
    if retornos_pendentes.empty:
        st.info("Nenhum paciente nesta janela para hoje.")
    else:
        for idx, row in retornos_pendentes.iterrows():
            with st.container(border=True):
                st.write(f"**{row['nome']}**")
                st.write(f"Consultou há {row['dias_desde_consulta']} dias ({row['data_consulta'].strftime('%d/%m/%Y')})")
                
                # Botão do WhatsApp
                msg = f"Olá {row['nome']}, tudo bem? Identificamos que sua consulta completou {row['dias_desde_consulta']} dias. Vamos agendar seu retorno gratuito esta semana?"
                msg_encoded = urllib.parse.quote(msg)
                link_wa = f"https://wa.me/55{row['whatsapp']}?text={msg_encoded}"
                
                c1, c2 = st.columns(2)
                c1.link_button("💬 Chamar no WhatsApp", link_wa, type="primary")
                if c2.button("Marcar como Agendado", key=f"agendar_{idx}"):
                    df.at[idx, 'status_retorno'] = 'AGENDADO'
                    df.to_csv(DATA_FILE, index=False)
                    st.success("Status atualizado!")
                    st.rerun()

with col2:
    st.subheader("🔥 Reengajamento (60+ dias)")
    st.caption("Pacientes sumidos há mais de 20 meses. Hora de oferecer nova consulta paga.")
    
    if reengajamento_pendente.empty:
        st.info("Nenhum paciente elegível para reengajamento hoje.")
    else:
        for idx, row in reengajamento_pendente.iterrows():
            with st.container(border=True):
                st.write(f"**{row['nome']}**")
                st.write(f"Último contato há {row['dias_desde_consulta']} dias.")
                
                # Botão do WhatsApp
                msg = f"Olá {row['nome']}, faz um tempo que não nos vemos! Como tem passado? Gostaria de agendar uma nova consulta de acompanhamento?"
                msg_encoded = urllib.parse.quote(msg)
                link_wa = f"https://wa.me/55{row['whatsapp']}?text={msg_encoded}"
                
                c1, c2 = st.columns(2)
                c1.link_button("💬 Chamar para Nova Consulta", link_wa, type="secondary")
                if c2.button("Arquivar / Atualizar", key=f"reeng_{idx}"):
                    # Reseta a data para hoje simulando um novo ciclo se ele reajustar
                    df.at[idx, 'data_consulta'] = data_atual
                    df.at[idx, 'status_retorno'] = 'PENDENTE'
                    df.to_csv(DATA_FILE, index=False)
                    st.success("Paciente atualizado no fluxo!")
                    st.rerun()

# --- TELA EXTRA: VISÃO GERAL DA BASE ---
st.markdown("---")
st.subheader("📋 Todos os Pacientes Cadastrados")
if not df.empty:
    st.dataframe(df[["nome", "whatsapp", "data_consulta", "status_retorno"]], use_container_width=True)
else:
    st.write("Nenhum paciente cadastrado ainda.")
