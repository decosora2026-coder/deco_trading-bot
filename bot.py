import os
import time
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import Conflict, NetworkError

# ==========================================
# 1. SERVIDOR WEB FALSO PARA O RENDER FREE
# ==========================================
# O Render Web Service exige que a aplicação responda a uma porta HTTP.
# Esse servidor simples faz exatamente isso para manter o serviço online 24/7.
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot do Deco Ativo e Operante!")
        
    def log_message(self, format, *args):
        pass # Desativa os logs de acesso web para não poluir o terminal

def run_dummy_server():
    # O Render passa a porta dinamicamente pela variável de ambiente $PORT
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

# ==========================================
# 2. CONFIGURAÇÕES E TOKENS
# ==========================================
TOKEN = "8874153543:AAHJMpuc_q1ZWhBHyG-2jBP9w9DDnw7m_Hg"
BINANCE_FUTURES_URL = "https://fapi.binance.com/fapi/v1/premiumIndex"
TICKER_24HR_URL = "https://fapi.binance.com/fapi/v1/ticker/24hr"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# ==========================================
# 3. COMANDOS DO TELEGRAM
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🤖 *Deco Radar Futuros Bot Ativo!*\n\n"
        "Comandos disponíveis:\n"
        "🔹 `/analise MOEDA` - Análise de Funding Rate (ex: `/analise BTCUSDT`)\n"
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
        
        # Verifica se a moeda existe nos futuros da Binance
        if "code" in res_funding:
            await update.message.reply_text(f"❌ O par `{symbol}` não foi encontrado no mercado de futuros da Binance.", parse_mode="Markdown")
            return
            
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
            # Filtra apenas pares em USDT e ignora shitcoins estranhas/índices
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

# ==========================================
# 4. LOOP ANTI-CONFLITO DO RENDER
# ==========================================
def main():
    # 1. Sobe o servidor HTTP em segundo plano para o Render parar de reclamar
    threading.Thread(target=run_dummy_server, daemon=True).start()
    print("🌐 Servidor HTTP Dummy iniciado.")

    # 2. Constrói o aplicativo do bot
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("analise", analise))
    app.add_handler(CommandHandler("scanner", scanner))

    # 3. Mantém o bot insistindo em conectar. Se o Render abrir 2 instâncias, a segunda espera.
    while True:
        try:
            print("🤖 Conectando ao Telegram...")
            # drop_pending_updates ignora mensagens travadas no passado
            app.run_polling(drop_pending_updates=True) 
        except Conflict:
            print("⚠️ Conflito de instância! Render tentou duplicar o bot. Aguardando 10 segundos para reconexão limpa...")
            time.sleep(10)
        except NetworkError:
            print("⚠️ Erro de rede da API do Telegram. Aguardando 5 segundos...")
            time.sleep(5)
        except Exception as e:
            print(f"❌ Erro inesperado: {e}. Reiniciando em 5 segundos...")
            time.sleep(5)

if __name__ == "__main__":
    main()
