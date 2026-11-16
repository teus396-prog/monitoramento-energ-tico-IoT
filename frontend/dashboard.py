import os
from pathlib import Path
import psycopg2
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Carrega o arquivo .env da raiz PII
pasta_raiz = Path(__file__).resolve().parent.parent
arquivo_env = pasta_raiz / ".env"
load_dotenv(dotenv_path=arquivo_env, encoding="latin-1")

st.set_page_config(page_title="Monitoramento Energético - PI UNIVESP", layout="wide")

# --- 1. CONTROLE DE LOGIN ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

USUARIOS = {
    "admin": "univesp2026",
    "hotel": "energia123"
}

def tela_login():
    st.title("🔐 Acesso ao Sistema - PI UNIVESP")
    st.write("Insira suas credenciais para acessar o Painel de Consumo Energético Empresarial.")

    col_esq, col_centro, col_dir = st.columns([1, 2, 1])
    with col_centro:
        with st.form("form_login"):
            usuario = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            entrar = st.form_submit_button("Entrar", use_container_width=True)

            if entrar:
                if usuario in USUARIOS and USUARIOS[usuario] == senha:
                    st.session_state["autenticado"] = True
                    st.session_state["usuario_atual"] = usuario
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

# --- 2. FUNÇÃO DE CARREGAMENTO DO BANCO ---
def carregar_dados():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS")         
    )
    query = """
        SELECT tempo, dispositivo_id, corrente_rms, potencia_ativa, consumo_kwh
        FROM metricas_eletricas
        ORDER BY tempo DESC
        LIMIT 500
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# --- 3. PÁGINA PRINCIPAL (SEU DASHBOARD ORIGINAL) ---
def pagina_dashboard():
    st.title("⚡ Painel de Consumo Energético Empresarial")

    df = carregar_dados()

    # Configuração na barra lateral
    st.sidebar.header("⚙️ Configurações")
    tarifa_kwh = st.sidebar.number_input("Tarifa de Energia (R$/kWh):", min_value=0.10, value=0.85, step=0.05)
    limite_potencia = st.sidebar.number_input("Limite de Alerta (W):", min_value=100, value=1000, step=100)

    if st.sidebar.button("🔄 Atualizar Agora"):
        st.rerun()

    if df.empty:
        st.info("Aguardando os primeiros dados do ESP32 ou do Bot do Telegram...")
    else:
        dispositivos = df["dispositivo_id"].unique()
        dispositivo_selecionado = st.sidebar.selectbox("Selecione o Dispositivo:", dispositivos)
        df_filtrado = df[df["dispositivo_id"] == dispositivo_selecionado]

        ultima = df_filtrado.iloc[0]

        # Alerta visual se a última medição ultrapassou o limite
        if ultima["potencia_ativa"] > limite_potencia:
            st.error(f"🚨 ALERTA DE SOBRECARGA: Potência atual ({ultima['potencia_ativa']:.1f} W) acima do limite de {limite_potencia} W!")

        # Cálculos financeiros e elétricos
        consumo_total = df_filtrado["consumo_kwh"].sum()
        custo_estimado = consumo_total * tarifa_kwh

        # 4 Cards principais
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Corrente RMS", f"{ultima['corrente_rms']:.2f} A")
        col2.metric("Potência Ativa", f"{ultima['potencia_ativa']:.1f} W")
        col3.metric("Consumo Acumulado", f"{consumo_total:.3f} kWh")
        col4.metric("Custo Estimado", f"R$ {custo_estimado:.2f}")

        # Gráficos lado a lado
        graf1, graf2 = st.columns(2)
        with graf1:
            st.subheader("📈 Potência Ativa (W)")
            st.line_chart(df_filtrado.set_index("tempo")["potencia_ativa"])
        with graf2:
            st.subheader("🔌 Corrente RMS (A)")
            st.line_chart(df_filtrado.set_index("tempo")["corrente_rms"])

        st.subheader("📋 Histórico de Leituras")
        st.dataframe(df_filtrado, width="stretch")

# --- 4. NOVA TELA DE INFORMAÇÕES ---
def pagina_informacoes():
    st.title("ℹ️ Informações do Projeto e Arquitetura")
    st.write("Documentação técnica do sistema de monitoramento de energia do Projeto Integrador (UNIVESP).")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🔌 Hardware e Circuito de Medição")
        st.markdown("""
        * **Microcontrolador:** ESP32 DevKit V1 (Wi-Fi)
        * **Sensor de Corrente:** SCT-013-000 (100A : 50mA) não invasivo
        * **Condicionamento de Sinal:** 
          * Divisor de tensão com 2 resistores de **10kΩ** (referência de 1.65V)
          * Capacitor eletrolítico de **10µF** para estabilização e filtro
          * Resistor de carga (*Burden*) entre **22Ω e 33Ω**
        * **Ponto de Instalação:** Quadro de Distribuição de Energia (Hotel)
        """)

    with col2:
        st.subheader("💻 Arquitetura de Software e Alertas")
        st.markdown("""
        * **API de Ingestão:** FastAPI + Uvicorn (recebe JSON via HTTP POST do ESP32)
        * **Banco de Dados:** PostgreSQL (`tabela: metricas_eletricas`)
        * **Alertas Automáticos:** Integração com **Bot do Telegram** para disparos em caso de pico de potência acima de **1000 W**
        * **Dashboard Web:** Streamlit com cálculo dinâmico de tarifa (R$/kWh)
        """)

    st.divider()

    st.subheader("🎓 Equipe do Projeto Integrador - UNIVESP")
    st.markdown("""
    * **Polo:** Leme - SP
    * **Integrantes:**
      * **Mateus Silva**
      * **André Oliveira**
    """)

    st.divider()
    st.subheader("⚠️ Recomendações de Segurança Elétrica")
    st.warning(
        "Nunca desconecte o conector P2 do sensor SCT-013 com o circuito energizado sem confirmar que o resistor de carga está firmemente conectado. "
        "Para operação contínua no painel do hotel, utilize placa soldada dentro de caixa isolada."
    )


# --- 5. FLUXO DE EXECUÇÃO E MENU ---
if not st.session_state["autenticado"]:
    tela_login()
else:
    with st.sidebar:
        st.write(f"👤 Logado como: **{st.session_state['usuario_atual']}**")
        if st.button("🚪 Sair (Logout)"):
            st.session_state["autenticado"] = False
            st.rerun()
        st.divider()

    pg = st.navigation([
        st.Page(pagina_dashboard, title="Monitoramento", icon="⚡"),
        st.Page(pagina_informacoes, title="Informações", icon="ℹ️"),
    ])
    pg.run()
