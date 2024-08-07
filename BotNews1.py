import asyncio
import requests
import logging
from telegram import Bot
import xml.etree.ElementTree as ET
import yfinance as yf

# Configuración
TOKEN = "7485891031:AAFC1jn9x3M8-3h7-0rbtG7HeHv7nA-2raI"
CHAT_ID = 6051894693  # Reemplaza esto con tu CHAT_ID real
BENZINGA_API_KEY = "403335b47327439da993a95256457f9e"  # Tu API key de Benzinga
CHECK_INTERVAL = 3600  # Verificar cada hora

# Configuración de logging
logging.basicConfig(level=logging.INFO)

# Inicialización del bot de Telegram
bot = Bot(token=TOKEN)

def get_benzinga_news():
    url = f"https://api.benzinga.com/api/v2/news?token={BENZINGA_API_KEY}&categories=smallcap&limit=10"
    response = requests.get(url)
    logging.info(f"Respuesta de la API de Benzinga: {response.text}")
    
    if response.status_code == 200:
        try:
            root = ET.fromstring(response.content)
            articles = []
            for item in root.findall('item'):
                title = item.find('title').text
                url = item.find('url').text
                published_at = item.find('created').text
                stocks = [stock.find('name').text for stock in item.findall('stocks/item')]
                articles.append({'title': title, 'url': url, 'published': published_at, 'stocks': stocks})
            return articles
        except ET.ParseError:
            logging.error("Error al analizar la respuesta XML de Benzinga")
            return []
    else:
        logging.error(f"Error al obtener noticias de Benzinga: {response.status_code}")
        return []

def get_stock_price(ticker):
    try:
        stock = yf.Ticker(ticker)
        price = stock.history(period="1d")['Close'][0]
        return price
    except Exception as e:
        logging.error(f"Error al obtener el precio de la acción {ticker}: {e}")
        return None

def filter_articles(articles):
    filtered_articles = []
    for article in articles:
        for stock in article['stocks']:
            price = get_stock_price(stock)
            if price is not None and price < 20:
                filtered_articles.append(article)
                break
    return filtered_articles

async def send_telegram_message(text):
    try:
        await bot.send_message(chat_id=CHAT_ID, text=text)
        logging.info(f"Mensaje enviado: {text}")
    except Exception as e:
        logging.error(f"Error al enviar mensaje: {e}")

async def main():
    while True:
        logging.info("Obteniendo noticias de Benzinga...")
        articles = get_benzinga_news()
        filtered_articles = filter_articles(articles)
        for article in filtered_articles:
            title = article.get('title')
            url = article.get('url')
            published_at = article.get('published')
            message = f"{title}\n{url}\nPublicado: {published_at}"
            await send_telegram_message(message)
        await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())
