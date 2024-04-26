import asyncio
import requests
import aiohttp
from aiohttp import web
from bs4 import BeautifulSoup
import json
import time
import re
from telegram import Bot
from telegram.ext import Application, CallbackContext, JobQueue

URL = "https://mta.ua/telefoni-ta-smartfoni/671723-smartfon-apple-iphone-14-pro-256gb-deep-purple"
TELEGRAM_TOKEN = '7146403916:AAG5cLCGPeuSs__PWD7ZU5RhWmpHZL4Im5I'
CHAT_ID = '530420753'
ADMIN_CHAT_ID = '530420753'
STORE_NAME = "MTA"
IN_STOCK_TEXT = "В наявності"
last_in_stock_status = IN_STOCK_TEXT
product_name = None

bot = Bot(token=TELEGRAM_TOKEN)
last_price = None
last_success_time = None

async def start_server():
    app = web.Application()
    app.router.add_get('/', lambda request: web.Response(text="Server is running"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 80)  # Змініть порт, якщо необхідно
    await site.start()

async def fetch_price():
    global last_success_time, last_in_stock_status, product_name
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
    try:
        response = requests.get(URL, headers=headers)
        if response.status_code != 200:
            print(f"{STORE_NAME}: Не вдалося завантажити сторінку, статус код: {response.status_code}")
            return None
        soup = BeautifulSoup(response.text, 'html.parser')
        title_element = soup.find('h1', class_='product__title')
        if title_element:
            product_name = ' '.join(re.findall(r'\b[a-zA-Z0-9]+\b', title_element.text))
        product_element = soup.find(class_='product_page')
        stock_element = soup.find(class_='product__stock_text')
        if stock_element:
            current_stock_status = stock_element.text.strip()
            if current_stock_status != last_in_stock_status:
                if current_stock_status != IN_STOCK_TEXT:
                    message = f"{STORE_NAME}: {product_name} - Статус наявності товару змінився: {current_stock_status}"
                    await bot.send_message(chat_id=CHAT_ID, text=message)
                last_in_stock_status = current_stock_status
        if not product_element or 'data-ecommerce' not in product_element.attrs:
            print("Не знайдено важливі елементи на сторінці.")
            return None
        data = json.loads(product_element['data-ecommerce'])
        if '_price' not in data or 'special' not in data['_price']:
            print("Дані про ціни відсутні або не відповідають очікуваному формату.")
            return None
        last_success_time = time.time()
        return data['_price']['special']
    except Exception as e:
        print(f"Помилка під час обробки даних: {e}")
        return None

async def check_availability(context: CallbackContext):
    global last_success_time
    if last_success_time and (time.time() - last_success_time > 172800):
        message = f"{STORE_NAME}: Увага: Бот не отримував доступ до даних більше 2 діб."
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=message)

async def check_price(context: CallbackContext):
    global last_price
    current_price = await fetch_price()
    if current_price is None:
        print("Ціну не знайдено.")
    else:
        print(f"{STORE_NAME}: Актуальна ціна: {current_price}")
        if last_price != current_price:
            if last_price is not None:
                message = f"{STORE_NAME}: {product_name} - Ціна змінилася з {last_price} на {current_price}"
                await context.bot.send_message(chat_id=CHAT_ID, text=message)
            last_price = current_price

def main():
    loop = asyncio.get_event_loop()
    loop.create_task(start_server())  # Запускаємо HTTP сервер у фоні
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    job_queue = application.job_queue
    job_queue.run_repeating(check_price, interval=3600)
    job_queue.run_repeating(check_availability, interval=3600)
    application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
