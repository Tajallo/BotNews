import asyncio
import requests
import yfinance as yf
from bs4 import BeautifulSoup
from datetime import datetime
import logging
from telegram.ext import Application

# Configuración
TOKEN = "7485891031:AAFC1jn9x3M8-3h7-0rbtG7HeHv7nA-2raI"
CHAT_ID = 6051894693  # Reemplaza esto con tu CHAT_ID real
SOURCES = {
    "Finviz": "https://finviz.com/screener.ashx?v=111&f=cap_small",
    "Benzinga": "https://www.benzinga.com/category/small-cap",
    "Yahoo Finance": "https://finance.yahoo.com/small-cap",
    "MarketWatch": "https://www.marketwatch.com/tools/stockresearch/screener.asp?small-cap=true",
    "Seeking Alpha": "https://seekingalpha.com/market-news/small-cap"
}
CHECK_INTERVAL = 5  # Verificar cada 5 segundos

# Configuración de logging
logging.basicConfig(filename='bot_log.txt', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

async def obtener_noticias_small_caps():
    noticias = set()
    for fuente, url in SOURCES.items():
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            if fuente == "Finviz":
                noticias_en_sitio = soup.find_all('tr', class_='news-link-row')
            elif fuente == "Benzinga":
                noticias_en_sitio = soup.find_all('div', class_='card')
            elif fuente == "Yahoo Finance":
                noticias_en_sitio = soup.find_all('li', class_='js-stream-item')
            elif fuente == "MarketWatch":
                noticias_en_sitio = soup.find_all('div', class_='article__content')
            elif fuente == "Seeking Alpha":
                noticias_en_sitio = soup.find_all('div', class_='article')
            else:
                noticias_en_sitio = []
            
            for noticia in noticias_en_sitio:
                noticia_texto = noticia.text.strip()
                noticias.add(noticia_texto)
        except Exception as e:
            logging.error(f"Error al obtener noticias de {fuente} ({url}): {str(e)}")
    return list(noticias)

async def obtener_datos_accion(ticker):
    try:
        stock = yf.Ticker(ticker)
        datos = stock.info
        precio_actual = datos.get('currentPrice')
        cambio_porcentual = datos.get('regularMarketChangePercent')
        return precio_actual, cambio_porcentual
    except Exception as e:
        logging.error(f"Error al obtener datos de {ticker}: {str(e)}")
        return None, None

async def enviar_notificacion(application, mensaje):
    try:
        await application.bot.send_message(chat_id=CHAT_ID, text=mensaje)
        logging.info(f"Notificación enviada: {mensaje[:50]}...")
    except Exception as e:
        logging.error(f"Error al enviar notificación: {str(e)}")

async def enviar_estado(application):
    mensaje = f"🟢 Bot en funcionamiento\nÚltima verificación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    await enviar_notificacion(application, mensaje)

async def main():
    application = Application.builder().token(TOKEN).build()
    noticias_anteriores = set()
    contador = 0
    
    logging.info("Bot iniciado")
    await enviar_notificacion(application, "🚀 Bot de noticias small caps iniciado")
    
    while True:
        try:
            noticias_actuales = await obtener_noticias_small_caps()
            
            for noticia in noticias_actuales:
                if noticia not in noticias_anteriores:
                    ticker = noticia.split()[0]  # Asumimos que el ticker es la primera palabra
                    precio, cambio = await obtener_datos_accion(ticker)
                    
                    if precio is not None and cambio is not None:
                        mensaje = f"🔔 Actualización de {ticker}\n\n"
                        mensaje += f"📰 Noticia: {noticia}\n"
                        mensaje += f"💰 Precio actual: ${precio:.2f}\n"
                        mensaje += f"📈 Cambio porcentual: {cambio:.2f}%"
                        
                        await enviar_notificacion(application, mensaje)
                        
                        noticias_anteriores.add(noticia)
            
            contador += 1
            if contador >= 720:  # Enviar estado cada hora (720 * 5 segundos = 1 hora)
                await enviar_estado(application)
                contador = 0
            
            await asyncio.sleep(CHECK_INTERVAL)
        except Exception as e:
            logging.error(f"Error en el ciclo principal: {str(e)}")
            await asyncio.sleep(60)  # Esperar un minuto antes de intentar de nuevo

if __name__ == "__main__":
    asyncio.run(main())
