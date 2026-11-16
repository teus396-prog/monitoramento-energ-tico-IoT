import os
from pathlib import Path
import psycopg2
import telebot
from dotenv import load_dotenv

# Carrega o env.txt ou .env da pasta raiz do projeto
pasta_raiz = Path(__file__).resolve().parent.parent
arquivo_env = pasta_raiz / ".env"
if not arquivo_env.exists():
    arquivo_env = pasta_raiz / "env.txt"

load_dotenv(dotenv_path=arquivo_env, encoding="latin-1")

TOKEN = os.getenv("Telegram_Bot_Token")
bot = telebot.TeleBot(TOKEN)

def conectar_banco():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS")
    )

# Comando inicial de boas-vindas
@bot.message_handler(commands=['start', 'ajuda'])
def boas_vindas(message):
    texto = (
        "⚡ *Monitoramento Energético - PI UNIVESP*\n\n"
        "Comandos disponíveis:\n"
        "• `/registrar DISPOSITIVO CORRENTE POTENCIA CONSUMO` - Salva uma leitura no banco\n"
        "  _Exemplo:_ `/registrar ESP32_SALA 3.5 444.5 0.445`\n"
        "• `/status` - Mostra a última leitura gravada no PostgreSQL"
    )
    bot.reply_to(message, texto, parse_mode="Markdown")

# Comando para inserir dados reais no PostgreSQL
@bot.message_handler(commands=['registrar'])
def registrar_dados(message):
    try:
        partes = message.text.split()
        dispositivo = partes[1]
        corrente = float(partes[2].replace(",", "."))
        potencia = float(partes[3].replace(",", "."))
        consumo = float(partes[4].replace(",", "."))

        conn = conectar_banco()
        cursor = conn.cursor()
        query = """
            INSERT INTO metricas_eletricas (tempo, dispositivo_id, corrente_rms, potencia_ativa, consumo_kwh)
            VALUES (NOW(), %s, %s, %s, %s)
        """
        cursor.execute(query, (dispositivo, corrente, potencia, consumo))
        conn.commit()
        cursor.close()
        conn.close()

        bot.reply_to(message, f"✅ Dados gravados!\nDispositivo: {dispositivo}\nPotência: {potencia} W")

    except (IndexError, ValueError):
        bot.reply_to(message, "⚠️ Formato inválido. Use:\n`/registrar ESP32_SALA 3.5 444.5 0.445`", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Erro no banco de dados: {e}")

# Comando para consultar a última medição direto pelo Telegram
@bot.message_handler(commands=['status'])
def consultar_status(message):
    try:
        conn = conectar_banco()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT dispositivo_id, corrente_rms, potencia_ativa, consumo_kwh, tempo
            FROM metricas_eletricas
            ORDER BY tempo DESC
            LIMIT 1
        """)
        dado = cursor.fetchone()
        cursor.close()
        conn.close()

        if dado:
            resposta = (
                f"📊 *Última Leitura Registrada:*\n"
                f"• Dispositivo: `{dado[0]}`\n"
                f"• Corrente: `{dado[1]} A`\n"
                f"• Potência: `{dado[2]} W`\n"
                f"• Consumo: `{dado[3]} kWh`"
            )
            bot.reply_to(message, resposta, parse_mode="Markdown")
        else:
            bot.reply_to(message, "Nenhum dado registrado no banco ainda.")
    except Exception as e:
        bot.reply_to(message, f"❌ Erro ao consultar: {e}")

@bot.message_handler(commands=['meuid'])
def mostrar_id(message):
    bot.reply_to(message, f"Seu TELEGRAM_CHAT_ID é: `{message.chat.id}`", parse_mode="Markdown")

print("🤖 Bot do Telegram rodando e aguardando mensagens...")
bot.infinity_polling()
