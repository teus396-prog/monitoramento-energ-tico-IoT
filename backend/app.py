import os
import time
from pathlib import Path
import psycopg2
import requests
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Carrega o .env da raiz PII
pasta_raiz = Path(__file__).resolve().parent.parent
arquivo_env = pasta_raiz / ".env"
load_dotenv(dotenv_path=arquivo_env, override=True, encoding="utf-8")

app = FastAPI(title="API IoT - Monitoramento Energético UNIVESP")

# Configurações de alerta automático
POTENCIA_MAXIMA_W = 1000.0
INTERVALO_ALERTA_SEGUNDOS = 60  # Evita spam: envia no máximo 1 alerta por minuto por dispositivo
ultimo_alerta_enviado = {}

class LeituraESP32(BaseModel):
    dispositivo_id: str
    corrente_rms: float
    potencia_ativa: float
    consumo_kwh: float

def enviar_alerta_telegram(mensagem: str):
    token = os.getenv("Telegram_Bot_Token")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("⚠️ Alerta ignorado: Verifique TELEGRAM_TOKEN e TELEGRAM_CHAT_ID no .env")
        return

    url = f"https://telegram.org/bot/{token.strip()}/sendMessage"
    try:
        # Enviado sem Markdown para evitar falhas com caracteres '_' no nome do dispositivo
        resposta = requests.post(url, json={"chat_id": chat_id.strip(), "text": mensagem}, timeout=5)
        if resposta.status_code == 200:
            print("📲 Alerta automático enviado com sucesso para o Telegram!")
        else:
            print(f"❌ Erro do Telegram ({resposta.status_code}): {resposta.text}")
    except Exception as e:
        print(f"❌ Falha de conexão ao enviar alerta: {e}")

@app.post("/api/medicoes")
def receber_medicao(dados: LeituraESP32):
    try:
        # 1. Grava os dados no PostgreSQL
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
        cursor.execute(query, (dados.dispositivo_id, dados.corrente_rms, dados.potencia_ativa, dados.consumo_kwh))
        conn.commit()
        cursor.close()
        conn.close()

        # 2. Verifica automaticamente se ultrapassou a potência máxima
        if dados.potencia_ativa > POTENCIA_MAXIMA_W:
            agora = time.time()
            ultimo_envio = ultimo_alerta_enviado.get(dados.dispositivo_id, 0)

            if (agora - ultimo_envio) >= INTERVALO_ALERTA_SEGUNDOS:
                alerta = (
                    f"🚨 ALERTA DE PICO DE ENERGIA!\n\n"
                    f"• Dispositivo: {dados.dispositivo_id}\n"
                    f"• Potência medida: {dados.potencia_ativa:.1f} W (Limite: {POTENCIA_MAXIMA_W:.0f} W)\n"
                    f"• Corrente RMS: {dados.corrente_rms:.2f} A"
                )
                enviar_alerta_telegram(alerta)
                ultimo_alerta_enviado[dados.dispositivo_id] = agora

        return {"status": "sucesso", "mensagem": "Leitura gravada com sucesso!"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
