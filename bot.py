import os
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Servidor Web interno para enganar o Render
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Telegram Ativo!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

# Configurações do Bot
TOKEN = "8874153543:AAFY348QPQQaugeeZsdRxgmzPIeRbCUvOzk"
BINANCE_FUTURES_URL = "https://fapi.binance.com/fapi/v1/premiumIndex"
TICKER_24HR_URL = "https://fapi.binance.com/fapi/v1/ticker/24hr"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

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
        res_funding = requests.get(BINANCE_FUTURES_URL, params={"symbol": symbol}, headers=HEADERS, timeout=10).json()
        funding_rate = float(res_funding.get("lastFundingRate", 0)) * 100

        res_ticker = requests.get(TICKER_24HR_URL, params={"symbol": symbol}, headers=HEADERS, timeout=10).json()
        if isinstance(res_ticker, list):
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
        await update.message.reply_text(f"❌ Erro ao buscar dados de {symbol}: {str(e)}")

async def scanner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 *Rodando varredura no mercado de futuros... Aguarde.*", parse_mode="Markdown")
    
    try:
        res = requests.get(TICKER_24HR_URL, headers=HEADERS, timeout=10)
        tickers = res.json()
        
        if not isinstance(tickers, list):
            await update.message.reply_text("❌ Não foi possível obter os dados da Binance.")
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

        sorted_tickers = sorted(usdt_list, key=lambda x: x["change"], reverse=True)
        
        top_gainers = sorted_tickers[:5]
        top_losers = sorted_tickers[-5:]
        top_losers.reverse()

        msg = "🚀 *OPORTUNIDADES DE MERCADO EM TEMPO REAL*\n\n"
        
        msg += "📈 *Maiores Altas (Possíveis Alvos / Exaustão):*\n"
        for t in top_gainers:
            msg += f"• `{t['symbol']}`: +{t['change']:.2f}% (Preço: {t['price']})\n"
            
        msg += "\n📉 *Maiores Baixas (Possível Repique / Long):*\n"
        for t in top_losers:
            msg += f"• `{t['symbol']}`: {t['change']:.2f}% (Preço: {t['price']})\n"

        msg += "\n💡 *Dica:* Envie `/analise MOEDA` para checar o Funding Rate!"
        
        await update.message.reply_text(msg, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao executar o scanner: {str(e)}")

def main():
    threading.Thread(target=run_dummy_server, daemon=True).start()

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("analise", analise))
    app.add_handler(CommandHandler("scanner", scanner))
    
    print("🤖 Bot rodando com sucesso...")
    app.run_polling()

if __name__ == "__main__":
    main()
