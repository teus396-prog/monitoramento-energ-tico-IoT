import os
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

# Carrega as credenciais do banco (mesma lógica do dashboard)
pasta_raiz = Path(__file__).resolve().parent.parent
arquivo_env = pasta_raiz / ".env"
if not arquivo_env.exists():
    arquivo_env = pasta_raiz / "env.txt"

load_dotenv(dotenv_path=arquivo_env, encoding="latin-1")

def salvar_medicao(dispositivo_id: str, corrente_rms: float, potencia_ativa: float, consumo_kwh: float):
    conn = None
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT", "5432"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS")
        )
        cursor = conn.cursor()

        query = """
            INSERT INTO metricas_eletricas (tempo, dispositivo_id, corrente_rms, potencia_ativa, consumo_kwh)
            VALUES (NOW(), %s, %s, %s, %s)
        """
        cursor.execute(query, (dispositivo_id, corrente_rms, potencia_ativa, consumo_kwh))
        
        # O commit() é obrigatório no psycopg2 para gravar os dados de verdade
        conn.commit()
        cursor.close()
        print(f"✅ Dados salvos: {dispositivo_id} | {potencia_ativa}W")
        return True

    except Exception as e:
        print(f"❌ Erro ao salvar no banco: {e}")
        return False

    finally:
        if conn:
            conn.close()
