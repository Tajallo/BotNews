
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
CHECK_INTERVAL = 3600  # Verificar cada hora
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
                    title = item.find('title').text
                    link = item.find('link').text
                    pub_date = item.find('pubDate').text
                    articles.append({'title': title, 'link': link, 'pub_date': pub_date})
                return articles
            else:
                logging.error(f"Failed to fetch news from Benzinga: {response.status}")
    except Exception as e:
        logging.error(f"Exception occurred while fetching Benzinga news: {e}")

async def get_alpha_vantage_news(session):
    ALPHA_VANTAGE_KEY = "your_alpha_vantage_key"
    url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers=AAPL,MSFT&apikey={ALPHA_VANTAGE_KEY}"
    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                articles = []
                for item in data["feed"]:
                    title = item["title"]
                    link = item["url"]
                    pub_date = item["time_published"]
                    articles.append({'title': title, 'link': link, 'pub_date': pub_date})
                return articles
            else:
                logging.error(f"Failed to fetch news from Alpha Vantage: {response.status}")
    except Exception as e:
        logging.error(f"Exception occurred while fetching Alpha Vantage news: {e}")

async def fetch_and_send_news():
    async with aiohttp.ClientSession() as session:
        benzinga_news = await get_benzinga_news(session)
        alpha_vantage_news = await get_alpha_vantage_news(session)
        
        all_news = benzinga_news + alpha_vantage_news
        
        for article in all_news:
            message = f"{article['title']}\n{article['link']}\n{article['pub_date']}"
            await bot.send_message(chat_id=CHAT_ID, text=message)

async def main():
    while True:
        await fetch_and_send_news()
        await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())
