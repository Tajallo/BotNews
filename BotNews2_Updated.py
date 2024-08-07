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
ALPHA_VANTAGE_API_KEY = "VYK850ZTSAONOL4Z"
CHECK_INTERVAL = 4  # Verificar cada hora
MAX_PRICE = 20  # Precio máximo para considerar una acción como small cap

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Inicialización del bot de Telegram
bot = Bot(token=TOKEN)

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

async def get_alpha_vantage_news(session):
    url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&apikey={ALPHA_VANTAGE_API_KEY}"
    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                if 'feed' not in data:
                    logging.error(f"La respuesta de Alpha Vantage no contiene el campo 'feed': {data}")
                    return []
                
                articles = []
                for item in data['feed']:
                    article = {
                        'title': item['title'],
                        'url': item['url'],
                        'published': item['time_published'],
                        'stocks': item.get('tickers', [])
                    }
                    articles.append(article)
                return articles
            else:
                logging.error(f"Error al obtener noticias de Alpha Vantage: {response.status}")
                return []
    except Exception as e:
        logging.error(f"Error en la solicitud a Alpha Vantage: {e}")
        return []

async def get_alpha_vantage_info(ticker):
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={ticker}&interval=5min&apikey={ALPHA_VANTAGE_API_KEY}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    time_series = data.get("Time Series (5min)")
                    if time_series:
                        latest_timestamp = sorted(time_series.keys())[-1]
                        latest_data = time_series[latest_timestamp]
                        price = float(latest_data['4. close'])
                        return price
                else:
                    logging.error(f"Error al obtener datos de Alpha Vantage: {response.status}")
    except Exception as e:
        logging.error(f"Error en la solicitud a Alpha Vantage: {e}")
    return None

async def get_stock_info(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="5d")  # Cambiado de "2d" a "5d"
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
        for stock in article['stocks']:
            price = await get_alpha_vantage_info(stock)
            if price is not None and price < MAX_PRICE:
                previous_price, percent_change = await get_stock_info(stock)
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
        logging.info(f"Mensaje enviado para {article['ticker']}")
    except Exception as e:
        logging.error(f"Error al enviar mensaje: {e}")

async def main():
    last_check = datetime.now() - timedelta(hours=1)  # Inicializar para que la primera ejecución obtenga noticias
    async with aiohttp.ClientSession() as session:
        while True:
            current_time = datetime.now()
            if (current_time - last_check).total_seconds() >= CHECK_INTERVAL:
                logging.info("Obteniendo noticias de Benzinga y Alpha Vantage...")
                benzinga_articles = await get_benzinga_news(session)
                alpha_vantage_articles = await get_alpha_vantage_news(session)
                all_articles = benzinga_articles + alpha_vantage_articles
                filtered_articles = await filter_articles(all_articles)
                for article in filtered_articles:
                    await send_telegram_message(article)
                last_check = current_time
            await asyncio.sleep(60)  # Verificar cada minuto si es hora de obtener noticias

if __name__ == "__main__":
    asyncio.run(main())
