import asyncio
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Token do seu Bot fornecido pelo BotFather
TOKEN = "8874153543:AAFY348QPQQaugeeZsdRxgmzPIeRbCUvOzk"

# URL da API de Futuros da Binance
BINANCE_FUTURES_URL = "https://fapi.binance.com/fapi/v1/premiumIndex"
TICKER_24HR_URL = "https://fapi.binance.com/fapi/v1/ticker/24hr"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🤖 *Deco Radar Futuros Bot Ativo!*\n\n"
        "Comandos disponíveis:\n"
        "🔹 `/analise MOEDA` - Análise de Funding Rate e variação (ex: `/analise BLESSUSDT`)\n"
        "🔹 `/scanner` - Varredura de moedas com anomalia de alta/baixa e risco de Short Squeeze\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def analise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Digite o par correto. Exemplo: `/analise BLESSUSDT`", parse_mode="Markdown")
        return
    
    symbol = context.args[0].upper()
    if not symbol.endswith("USDT"):
        symbol += "USDT"

    try:
        # Busca Funding Rate
        res_funding = requests.get(BINANCE_FUTURES_URL, params={"symbol": symbol}).json()
        funding_rate = float(res_funding.get("lastFundingRate", 0)) * 100

        # Busca dados de 24h
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
        # Filtra os pares com maior variação e volume alto
        top_gainers = [t for t in tickers if float(t.get("priceChangePercent", 0)) > 15]
        top_losers = [t for t in tickers if float(t.get("priceChangePercent", 0)) < -15]

        msg = "🚀 *OPORTUNIDADES DE MERCADO EM TEMPO REAL*\n\n"
        
        msg += "📈 *Maior Volume de Alta (Possíveis Alvos / Exaustão):*\n"
        for t in top_gainers[:5]:
            msg += f"• `{t['symbol']}`: +{float(t['priceChangePercent']):.2f}% (Preço: {t['lastPrice']})\n"
            
        msg += "\n📉 *Maior Volume de Queda (Possível Repique / Long):*\n"
        for t in top_losers[:5]:
            msg += f"• `{t['symbol']}`: {float(t['priceChangePercent']):.2f}% (Preço: {t['lastPrice']})\n"

        msg += "\n💡 *Dica do Mentor:* Antes de abrir ordem em qualquer uma dessas, use `/analise NOME` para checar o Funding Rate!"
        
        await update.message.reply_text(msg, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text("❌ Erro ao executar o scanner de mercado.")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("analise", analise))
    app.add_handler(CommandHandler("scanner", scanner))
    
    print("🤖 Bot rodando com sucesso...")
    app.run_polling()

if __name__ == "__main__":
    main()
