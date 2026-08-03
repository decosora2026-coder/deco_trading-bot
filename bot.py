import os
import requests
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = "8874153543:AAHJMpuc_q1ZWhBHyG-2jBP9w9DDnw7m_Hg"
PORT = int(os.environ.get("PORT", 10000))
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "")

# Usando a API pública do CoinGecko (100% livre de bloqueios para servidores de nuvem)
COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"

# Mapeamento dos símbolos para os IDs do CoinGecko
MOEDAS_COINGECKO = {
    "PEPEUSDT": "pepe",
    "SHIBUSDT": "shiba-inu",
    "DOGEUSDT": "dogecoin",
    "XRPUSDT": "ripple",
    "ADAUSDT": "cardano",
    "GALAUSDT": "gala",
    "FLOKIUSDT": "floki",
    "BONKUSDT": "bonk",
    "NEARUSDT": "near",
    "ARBUSDT": "arbitrum",
    "OPUSDT": "optimism",
    "SUIUSDT": "sui",
    "RENDERUSDT": "render-token",
    "FETUSDT": "fetch-ai",
    "INJUSDT": "injective-protocol",
    "MATICUSDT": "polygon-ecosystem-token",
    "LINKUSDT": "chainlink",
    "AVAXUSDT": "avalanche-2",
    "CHZUSDT": "chiliz",
    "SANDUSDT": "the-sandbox"
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
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

    if symbol not in MOEDAS_COINGECKO:
        await update.message.reply_text(f"❌ O par `{symbol}` não está cadastrado na lista de altcoins leves.", parse_mode="Markdown")
        return

    coin_id = MOEDAS_COINGECKO[symbol]

    try:
        url = f"https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "ids": coin_id,
            "sparkline": "false"
        }
        res = requests.get(url, params=params, headers=HEADERS, timeout=10)
        
        if res.status_code != 200 or not res.json():
            await update.message.reply_text(f"❌ Erro ao consultar dados de `{symbol}`.", parse_mode="Markdown")
            return
            
        data = res.json()[0]
        last_price = data.get("current_price", 0)
        price_change = data.get("price_change_percentage_24h", 0) or 0

        msg = (
            f"📊 *Análise Instantânea: {symbol}*\n\n"
            f"💰 *Preço Atual:* `${last_price}`\n"
            f"📈 *Variação 24h:* `{price_change:.2f}%`\n"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao processar análise.")

async def scanner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 *Varrendo altcoins de lote leve...*", parse_mode="Markdown")
    try:
        ids_string = ",".join(MOEDAS_COINGECKO.values())
        url = f"https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "ids": ids_string,
            "sparkline": "false"
        }
        
        res = requests.get(url, params=params, headers=HEADERS, timeout=15)
        if res.status_code != 200:
            await update.message.reply_text("❌ Erro ao conectar com o provedor de dados.")
            return

        coins = res.json()
        usdt_list = []
        
        # Mapeia de volta para o símbolo USDT
        id_to_symbol = {v: k for k, v in MOEDAS_COINGECKO.items()}

        for coin in coins:
            coin_id = coin.get("id")
            symbol = id_to_symbol.get(coin_id, coin_id.upper())
            pct = coin.get("price_change_percentage_24h", 0) or 0
            price = coin.get("current_price", 0)
            usdt_list.append({"symbol": symbol, "change": pct, "price": price})

        if not usdt_list:
            await update.message.reply_text("❌ Nenhum dado retornado.")
            return

        sorted_tickers = sorted(usdt_list, key=lambda x: x["change"], reverse=True)
        top_gainers = sorted_tickers[:3]
        top_losers = sorted_tickers[-3:]
        top_losers.reverse()

        msg = "🚀 *RADAR DE ALTCOINS (LOTE LEVE)*\n\n"
        msg += "📈 *Destaques de Alta:*\n"
        for t in top_gainers:
            msg += f"• `{t['symbol']}`: +{t['change']:.2f}% (Preço: ${t['price']})\n"
            
        msg += "\n📉 *Destaques de Baixa:*\n"
        for t in top_losers:
            msg += f"• `{t['symbol']}`: {t['change']:.2f}% (Preço: ${t['price']})\n"

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
