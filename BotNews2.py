import asyncio
import aiohttp
import logging
from telegram import Bot
import xml.etree.ElementTree as ET
import yfinance as yf
from datetime import datetime, timedelta

# Configuración
TOKEN = "7485891031:AAFC1jn9x3M8-3h7-0rbtG7HeHv7nA-2raI"
CHAT_ID = 6051894693
BENZINGA_API_KEY = "403335b47327439da993a95256457f9e"
CHECK_INTERVAL = 5  # Verificar cada 5 (en segundos)
MAX_PRICE = 20  # Precio máximo para considerar una acción como small cap

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Inicialización del bot de Telegram
bot = Bot(token=TOKEN)

# Set para almacenar los URLs de las noticias ya enviadas
sent_news = set()

async def get_benzinga_news(session):
    url = f"https://api.benzinga.com/api/v2/news?token={BENZINGA_API_KEY}&categories=smallcap&limit=10"
    try:
        async with session.get(url) as response:
            if response.status == 200:
                content = await response.text()
                root = ET.fromstring(content)
                articles = []
                for item in root.findall('item'):
                    article = {
                        'title': item.find('title').text,
                        'url': item.find('url').text,
                        'published': item.find('created').text,
                        'stocks': [stock.find('name').text for stock in item.findall('stocks/item')]
                    }
                    articles.append(article)
                return articles
            else:
                logging.error(f"Error al obtener noticias de Benzinga: {response.status}")
                return []
    except Exception as e:
        logging.error(f"Error en la solicitud a Benzinga: {e}")
        return []

async def get_stock_info(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="5d")
        if len(hist) < 2:
            return None, None
        price = hist['Close'].iloc[-1]
        previous_price = hist['Close'].iloc[-2]
        percent_change = ((price - previous_price) / previous_price) * 100
        return price, percent_change
    except Exception as e:
        logging.error(f"Error al obtener la información de la acción {ticker}: {e}")
        return None, None

async def filter_articles(articles):
    filtered_articles = []
    for article in articles:
        if article['url'] not in sent_news:  # Verificar si la noticia ya ha sido enviada
            for stock in article['stocks']:
                price, percent_change = await get_stock_info(stock)
                if price is not None and price < MAX_PRICE:
                    article['price'] = price
                    article['percent_change'] = percent_change
                    article['ticker'] = stock
                    filtered_articles.append(article)
                    break
    return filtered_articles

async def send_telegram_message(article):
    try:
        message = (
            f"📰 {article['title']}\n\n"
            f"🔗 {article['url']}\n"
            f"🕒 Publicado: {article['published']}\n"
            f"🏷️ Ticker: {article['ticker']}\n"
            f"💰 Precio actual: ${article['price']:.2f}\n"
            f"📈 Cambio porcentual: {article['percent_change']:.2f}%"
        )
        await bot.send_message(chat_id=CHAT_ID, text=message)
        sent_news.add(article['url'])  # Agregar la URL a las noticias enviadas
        logging.info(f"Mensaje enviado para {article['ticker']}")
    except Exception as e:
        logging.error(f"Error al enviar mensaje: {e}")

async def main():
    async with aiohttp.ClientSession() as session:
        while True:
            logging.info("Obteniendo noticias de Benzinga...")
            articles = await get_benzinga_news(session)
            filtered_articles = await filter_articles(articles)
            for article in filtered_articles:
                await send_telegram_message(article)
            await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())