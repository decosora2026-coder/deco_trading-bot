import asyncio
import os
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Servidor Dummy para o Render não dar erro de Porta
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Ativo!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

# Token do seu Bot
TOKEN = "8874153543:AAFY348QPQQaugeeZsdRxgmzPIeRbCUvOzk"

# APIs Futuros Binance
BINANCE_FUTURES_URL = "https://fapi.binance.com/fapi/v1/premiumIndex"
TICKER_24HR_URL = "https://fapi.binance.com/fapi/v1/ticker/24hr"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🤖 *Deco Radar Futuros Bot Ativo!*\n\n"
        "Comandos disponíveis:\n"
        "🔹 `/analise MOEDA` - Análise de Funding Rate e variação (ex: `/analise BTCUSDT`)\n"
        "🔹 `/scanner` - Varredura das maiores altas, baixas e risco de Short Squeeze\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def analise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Digite o par correto. Exemplo: `/analise BTCUSDT`", parse_mode="Markdown")
        return
    
    symbol = context.args[0].upper()
    if not symbol.endswith("USDT"):
        symbol += "USDT"

    try:
        res_funding = requests.get(BINANCE_FUTURES_URL, params={"symbol": symbol}).json()
        funding_rate = float(res_funding.get("lastFundingRate", 0)) * 100

        res_ticker = requests.get(TICKER_24HR_URL, params={"symbol": symbol}).json()
        price_change = float(res_ticker.get("priceChangePercent", 0))
        last_price = float(res_ticker.get("lastPrice", 0))

        alerta = ""
        if funding_rate < -0.1:
            alerta = "\n🚨 *ALERTA:* Funding Rate muito negativo! Risco ALTO de Short Squeeze (Cuidado com Short!)."
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
        await update.message.reply_text("❌ Erro ao buscar dados do par. Verifique se o nome está correto.")

async def scanner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 *Rodando varredura no mercado de futuros... Aguarde.*", parse_mode="Markdown")
    
    try:
        tickers = requests.get(TICKER_24HR_URL).json()
        # Filtra apenas pares USDT válidos
        usdt_tickers = [t for t in tickers if t.get("symbol", "").endswith("USDT")]
        
        # Ordena por variação de preço
        sorted_tickers = sorted(usdt_tickers, key=lambda x: float(x.get("priceChangePercent", 0)), reverse=True)
        
        top_gainers = sorted_tickers[:5]
        top_losers = sorted_tickers[-5:]
        top_losers.reverse()

        msg = "🚀 *OPORTUNIDADES DE MERCADO EM TEMPO REAL*\n\n"
        
        msg += "📈 *Maiores Altas (Possíveis Alvos / Exaustão):*\n"
        for t in top_gainers:
            msg += f"• `{t['symbol']}`: +{float(t['priceChangePercent']):.2f}% (Preço: {t['lastPrice']})\n"
            
        msg += "\n📉 *Maiores Baixas (Possível Repique / Long):*\n"
        for t in top_losers:
            msg += f"• `{t['symbol']}`: {float(t['priceChangePercent']):.2f}% (Preço: {t['lastPrice']})\n"

        msg += "\n💡 *Dica:* Envie `/analise MOEDA` para checar o Funding Rate da moeda escolhida!"
        
        await update.message.reply_text(msg, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text("❌ Erro ao executar o scanner de mercado.")

def main():
    # Inicia servidor Web em segundo plano para o Render
    threading.Thread(target=run_dummy_server, daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("analise", analise))
    app.add_handler(CommandHandler("scanner", scanner))
    
    print("🤖 Bot rodando com sucesso...")
    app.run_polling()

if __name__ == "__main__":
    main()
