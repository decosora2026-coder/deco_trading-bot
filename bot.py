import os
import requests
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = "8874153543:AAHJMpuc_q1ZWhBHyG-2jBP9w9DDnw7m_Hg"
PORT = int(os.environ.get("PORT", 10000))
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "")

# Usando a API pública de Spot da Binance (100% aberta para servidores de cloud)
SPOT_TICKER_URL = "https://api.binance.com/api/v3/ticker/24hr"

# Altcoins de lote leve e acessível presentes em futuros
PRINCIPAIS_PARES = [
    "PEPEUSDT", "SHIBUSDT", "DOGEUSDT", "XRPUSDT", "ADAUSDT",
    "GALAUSDT", "FLOKIUSDT", "BONKUSDT", "NEARUSDT", "ARBUSDT",
    "OPUSDT", "SUIUSDT", "RENDERUSDT", "FETUSDT", "INJUSDT",
    "MATICUSDT", "LINKUSDT", "AVAXUSDT", "CHZUSDT", "SANDUSDT"
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json',
    'Referer': 'https://www.binance.com/'
}

app_flask = Flask(__name__)
telegram_app = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🤖 *Deco Radar Futuros Bot Ativo!*\n\n"
        "Comandos disponíveis:\n"
        "🔹 `/analise MOEDA` - Análise de variação (ex: `/analise PEPEUSDT`)\n"
        "🔹 `/scanner` - Varredura rápida nas altcoins de lote leve\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def analise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Digite o par correto. Ex: `/analise PEPEUSDT`", parse_mode="Markdown")
        return
    
    symbol = context.args[0].upper()
    if not symbol.endswith("USDT"):
        symbol += "USDT"

    try:
        res = requests.get(SPOT_TICKER_URL, params={"symbol": symbol}, headers=HEADERS, timeout=10)
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
    await update.message.reply_text("🔍 *Varrendo altcoins de lote leve...*", parse_mode="Markdown")
    try:
        usdt_list = []
        for symbol in PRINCIPAIS_PARES:
            try:
                res = requests.get(SPOT_TICKER_URL, params={"symbol": symbol}, headers=HEADERS, timeout=5)
                if res.status_code == 200:
                    data = res.json()
                    pct = float(data.get("priceChangePercent", 0))
                    price = float(data.get("lastPrice", 0))
                    usdt_list.append({"symbol": symbol, "change": pct, "price": price})
            except Exception:
                continue

        if not usdt_list:
            await update.message.reply_text("❌ Não foi possível carregar os dados no momento.")
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
    app_flask.run(host="0.0.0.0", port=PORT)
