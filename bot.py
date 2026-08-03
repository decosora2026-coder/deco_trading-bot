import os
import requests
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = "8874153543:AAHJMpuc_q1ZWhBHyG-2jBP9w9DDnw7m_Hg"
PORT = int(os.environ.get("PORT", 10000))
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "")

BINANCE_FUTURES_URL = "https://fapi.binance.com/fapi/v1/premiumIndex"
TICKER_24HR_URL = "https://fapi.binance.com/fapi/v1/ticker/24hr"

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
        "🔹 `/analise MOEDA` - Análise de Funding Rate e variação (ex: `/analise BTCUSDT`)\n"
        "🔹 `/scanner` - Varredura das maiores altas e baixas\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def analise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Digite o par correto. Ex: `/analise BTCUSDT`", parse_mode="Markdown")
        return
    
    symbol = context.args[0].upper()
    if not symbol.endswith("USDT"):
        symbol += "USDT"

    try:
        res_funding = requests.get(BINANCE_FUTURES_URL, params={"symbol": symbol}, headers=HEADERS, timeout=15).json()
        if isinstance(res_funding, dict) and "code" in res_funding:
            await update.message.reply_text(f"❌ O par `{symbol}` não foi encontrado nos futuros da Binance.", parse_mode="Markdown")
            return
            
        funding_rate = float(res_funding.get("lastFundingRate", 0)) * 100
        
        res_ticker = requests.get(TICKER_24HR_URL, params={"symbol": symbol}, headers=HEADERS, timeout=15).json()
        if isinstance(res_ticker, list) and len(res_ticker) > 0:
            res_ticker = res_ticker[0]
            
        price_change = float(res_ticker.get("priceChangePercent", 0))
        last_price = float(res_ticker.get("lastPrice", 0))

        alerta = ""
        if funding_rate < -0.1:
            alerta = "\n🚨 *ALERTA:* Funding Rate muito negativo! Risco ALTO de Short Squeeze."
        elif funding_rate > 0.1:
            alerta = "\n⚠️ *ALERTA:* Mercado muito alavancado em Long. Possível correção."

        msg = (
            f"📊 *Análise Instantânea: {symbol}*\n\n"
            f"💰 *Preço Atual:* `{last_price}`\n"
            f"📈 *Variação 24h:* `{price_change:.2f}%`\n"
            f"⚡ *Funding Rate:* `{funding_rate:.4f}%`\n"
            f"{alerta}"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao buscar dados de {symbol} na Binance.")

async def scanner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 *Rodando varredura no mercado de futuros... Aguarde.*", parse_mode="Markdown")
    try:
        res = requests.get(TICKER_24HR_URL, headers=HEADERS, timeout=15)
        
        if res.status_code != 200:
            await update.message.reply_text("❌ A Binance bloqueou temporariamente a consulta. Tente novamente em instantes.")
            return

        tickers = res.json()
        if not isinstance(tickers, list):
            await update.message.reply_text("❌ Não foi possível carregar o mercado no momento.")
            return

        usdt_list = []
        for t in tickers:
            symbol = t.get("symbol", "")
            if symbol.endswith("USDT") and not symbol.startswith("1000"):
                try:
                    pct = float(t.get("priceChangePercent", 0))
                    price = float(t.get("lastPrice", 0))
                    usdt_list.append({"symbol": symbol, "change": pct, "price": price})
                except ValueError:
                    continue

        if not usdt_list:
            await update.message.reply_text("❌ Nenhum dado retornado pela Binance.")
            return

        sorted_tickers = sorted(usdt_list, key=lambda x: x["change"], reverse=True)
        top_gainers = sorted_tickers[:5]
        top_losers = sorted_tickers[-5:]
        top_losers.reverse()

        msg = "🚀 *OPORTUNIDADES DE MERCADO EM TEMPO REAL*\n\n"
        msg += "📈 *Maiores Altas:*\n"
        for t in top_gainers:
            msg += f"• `{t['symbol']}`: +{t['change']:.2f}% (Preço: {t['price']})\n"
            
        msg += "\n📉 *Maiores Baixas:*\n"
        for t in top_losers:
            msg += f"• `{t['symbol']}`: {t['change']:.2f}% (Preço: {t['price']})\n"

        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Não foi possível carregar o mercado no momento.")

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
        print(f"🔗 Webhook registrado com sucesso na Binance/Telegram: {url}")

if __name__ == "__main__":
    setup_webhook_url()
    app_flask.run(host="0.0.0.0", port=PORT)
