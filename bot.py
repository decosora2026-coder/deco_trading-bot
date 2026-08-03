import os
import requests
import asyncio
import threading
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = "8874153543:AAHJMpuc_q1ZWhBHyG-2jBP9w9DDnw7m_Hg"
PORT = int(os.environ.get("PORT", 10000))
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "")

BINANCE_ALT_URL = "https://data-api.binance.vision/api/v3/ticker/24hr"

PARES_LEVES = [
    "PEPEUSDT", "SHIBUSDT", "DOGEUSDT", "XRPUSDT", "ADAUSDT",
    "GALAUSDT", "FLOKIUSDT", "BONKUSDT", "NEARUSDT", "ARBUSDT",
    "OPUSDT", "SUIUSDT", "RENDERUSDT", "FETUSDT", "INJUSDT",
    "MATICUSDT", "LINKUSDT", "AVAXUSDT", "CHZUSDT", "SANDUSDT"
]

app_flask = Flask(__name__)
telegram_app = None

# Armazena o ID do último chat que interagiu com o bot para enviar os alertas automáticos
last_chat_id = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_chat_id
    last_chat_id = update.effective_chat.id
    msg = (
        "🤖 *Deco Radar Futuros Bot Ativo!*\n\n"
        "Comandos disponíveis:\n"
        "🔹 `/analise MOEDA` - Análise de variação (ex: `/analise PEPEUSDT`)\n"
        "🔹 `/scanner` - Varredura rápida nas altcoins de lote leve\n\n"
        "⚡ *Monitoramento automático ativado!* Avisarei se alguma moeda romper ±5%."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def analise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_chat_id
    last_chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text("⚠️ Digite o par correto. Ex: `/analise PEPEUSDT`", parse_mode="Markdown")
        return
    
    symbol = context.args[0].upper()
    if not symbol.endswith("USDT"):
        symbol += "USDT"

    try:
        res = requests.get(BINANCE_ALT_URL, params={"symbol": symbol}, timeout=10)
        if res.status_code != 200:
            await update.message.reply_text(f"❌ O par `{symbol}` não foi encontrado.", parse_mode="Markdown")
            return
            
        data = res.json()
        price_change = float(data.get("priceChangePercent", 0))
        last_price = float(data.get("lastPrice", 0))

        msg = (
            f"📊 *Análise Instantânea: {symbol}*\n\n"
            f"💰 *Preço Atual:* `{last_price}`\n"
            f"📈 *Variação 24h:* `{price_change:.2f}%`\n"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao buscar dados de {symbol}.")

async def scanner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_chat_id
    last_chat_id = update.effective_chat.id
    await update.message.reply_text("🔍 *Varrendo altcoins de lote leve...*", parse_mode="Markdown")
    try:
        usdt_list = []
        for symbol in PARES_LEVES:
            try:
                res = requests.get(BINANCE_ALT_URL, params={"symbol": symbol}, timeout=4)
                if res.status_code == 200:
                    data = res.json()
                    pct = float(data.get("priceChangePercent", 0))
                    price = float(data.get("lastPrice", 0))
                    usdt_list.append({"symbol": symbol, "change": pct, "price": price})
            except Exception:
                continue

        if not usdt_list:
            await update.message.reply_text("❌ Erro de conexão com o servidor de cotação.")
            return

        sorted_tickers = sorted(usdt_list, key=lambda x: x["change"], reverse=True)
        top_gainers = sorted_tickers[:3]
        top_losers = sorted_tickers[-3:]
        top_losers.reverse()

        msg = "🚀 *RADAR DE ALTCOINS (LOTE LEVE)*\n\n"
        msg += "📈 *Destaques de Alta:*\n"
        for t in top_gainers:
            msg += f"• `{t['symbol']}`: +{t['change']:.2f}% (Preço: {t['price']})\n"
            
        msg += "\n📉 *Destaques de Baixa:*\n"
        for t in top_losers:
            msg += f"• `{t['symbol']}`: {t['change']:.2f}% (Preço: {t['price']})\n"

        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao processar o scanner.")

def monitor_mercado():
    """Loop em segundo plano que verifica o mercado a cada 10 minutos"""
    global last_chat_id
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    import time
    time.sleep(15) # Aguarda o bot inicializar completamente

    moedas_notificadas = set()

    while True:
        try:
            if last_chat_id:
                for symbol in PARES_LEVES:
                    res = requests.get(BINANCE_ALT_URL, params={"symbol": symbol}, timeout=5)
                    if res.status_code == 200:
                        data = res.json()
                        pct = float(data.get("priceChangePercent", 0))
                        price = float(data.get("lastPrice", 0))

                        # Alerta se passar de +5% ou -5%
                        if abs(pct) >= 5.0 and symbol not in moedas_notificadas:
                            tipo = "🚀 ESTICADA DE ALTA (Oportunidade de Short?)" if pct > 0 else "🩸 QUEDA FORTE (Oportunidade de Long?)"
                            alerta_msg = (
                                f"🚨 *ALERTA DE MOVIMENTO IMPORTANTE!*\n\n"
                                f"🔹 *Par:* `{symbol}`\n"
                                f"📊 *Variação 24h:* `{pct:.2f}%`\n"
                                f"💰 *Preço:* `{price}`\n\n"
                                f"_{tipo}_"
                            )
                            loop.run_until_complete(telegram_app.bot.send_message(chat_id=last_chat_id, text=alerta_msg, parse_mode="Markdown"))
                            moedas_notificadas.add(symbol)
                        
                        # Reseta o aviso se o preço normalizar abaixo de 4%
                        elif abs(pct) < 4.0 and symbol in moedas_notificadas:
                            moedas_notificadas.remove(symbol)
        except Exception as e:
            print(f"Erro no monitoramento: {e}")
        
        time.sleep(600) # Roda a cada 10 minutos

def init_telegram():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("analise", analise))
    app.add_handler(CommandHandler("scanner", scanner))
    return app

telegram_app = init_telegram()

@app_flask.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        json_data = request.get_json(force=True)
        update = Update.de_json(json_data, telegram_app.bot)
        
        async def process():
            await telegram_app.initialize()
            await telegram_app.process_update(update)

        asyncio.run(process())
    except Exception as e:
        print(f"Erro ao processar mensagem: {e}")
    return "OK", 200

@app_flask.route("/", methods=["GET"])
def index():
    return "Bot Operando via Webhook com Sucesso!"

def setup_webhook_url():
    if RENDER_EXTERNAL_URL:
        url = f"{RENDER_EXTERNAL_URL}/{TOKEN}"
        requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook", params={"url": url})
        print(f"🔗 Webhook registrado com sucesso: {url}")

if __name__ == "__main__":
    setup_webhook_url()
    # Inicia a thread de monitoramento automático em segundo plano
    t = threading.Thread(target=monitor_mercado, daemon=True)
    t.start()
    app_flask.run(host="0.0.0.0", port=PORT)
