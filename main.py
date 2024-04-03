#для запуска бота необходимо скачать соответсвующие библиотеки прописав(pip install aiogram, pip install matplotlib, pip install selenium) и запустить код, затем перейти в бота по его названию:parser_wildber_bot
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import FSInputFile
import asyncio
import time
import matplotlib.pyplot as plt
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from aiogram import Bot, types
from aiogram import Dispatcher, Bot 
from aiogram.filters import Command, CommandStart
import logging
import sys
import random


TOKEN='6318591501:AAGaAED6S7pc3yewDMrMlLKVSY58d-v0pns'


options = webdriver.ChromeOptions()
options.add_argument('--ignore-certificate-errors')
options.add_experimental_option('excludeSwitches', ['enable-logging'])
options.add_argument('--headless')

bot = Bot(token=TOKEN)
dp = Dispatcher()

req = None
count = None
min_price = None
max_price = None
min_rating = None
url = None
chat_id = None
message_id = None
prices = []
initial_price = None
is_tracking = False
graph_price = []

async def set_user_data(message: types.Message):
    global req, count, min_price, max_price, min_rating
    data = message.text.split()
    if len(data) >= 5:
        req = " ".join(data[:1])
        count = int(data[1])
        min_price = int(data[2])
        max_price = int(data[3])
        min_rating = float(data[4])
        await message.answer("Пожалуйста, подождите, пока я найду товары...")
        await search_products(message)
    else:
        await message.answer("Недостаточно данных. Пожалуйста, введите название товара, количество страниц для поиска, минимальную цену, максимальную цену и минимальный рейтинг через пробел.")

async def search_products(message: types.Message):
    driver = webdriver.Chrome(options=options)
    driver.get(f'https://www.wildberries.ru/catalog/0/search.aspx?page=1&sort=popular&search={req}')
    time.sleep(2)

    success = 0
    results = []
    filtered_results = []

    for _ in range(1, count + 1):
        for i in range(1, 80):
            try:
                print(i)
                if i % 5:
                    driver.execute_script(f"window.scrollTo(0, {200*i});")
                time.sleep(0.2)

                price = int(driver.find_element(By.XPATH, f'/html/body/div[1]/main/div[2]/div/div[2]/div/div/div[4]/div[1]/div[1]/div/article[{i}]/div/div[3]/p/span/ins').text.replace(" ", "").replace("₽", ""))
                rating = float(driver.find_element(By.XPATH, f'/html/body/div[1]/main/div[2]/div/div[2]/div/div/div[4]/div[1]/div[1]/div/article[{i}]/div/div[4]/p[1]/span[1]').text.replace(",", "."))
            # print('price', driver.find_element(By.XPATH, f'/html/body/div[1]/main/div[2]/div/div[2]/div/div/div[4]/div[1]/div[1]/div/article[{i}]/div/div[3]/p/span/ins').text)
                link = driver.find_element(By.XPATH, f'/html/body/div[1]/main/div[2]/div/div[2]/div/div/div[4]/div[1]/div[1]/div/article[{i}]/div/a').get_attribute('href')
                results.append({'price': price, 'rating': rating, 'url': link})
                if min_price <= price and price <= max_price and rating >= min_rating:
                    filtered_results.append({'price': price, 'rating': rating, 'url': link})
                    print ('рейтинг ',rating )
                    print('Цена:', price)
                    print('URL:', link)
                    print()

                    success += 1

            except:
                time.sleep(1)
        time.sleep(1)
        driver.find_element(By.CSS_SELECTOR, '#catalog > div > div.pagination > div > a.pagination-next.pagination__next.j-next-page').click()
        time.sleep(3)

    await bot.send_message(message.chat.id, f'Найдено {success} товаров по запросу "{req}" в диапазоне цен от {min_price} до {max_price} рублей и с рейтингом не ниже {min_rating} на {count} страницах.')

    chunk_size = 10
    for i in range(0, len(filtered_results), chunk_size):
        chunk = filtered_results[i:i+chunk_size]
        message_text = 'Отфильтрованные результаты:\n'
        for result in chunk:
            message_text += f"Цена: {result['price']}\nРейтинг: {result['rating']}\nURL: {result['url']}\n\n"
        await bot.send_message(message.chat.id, message_text)
        await asyncio.sleep(0.5)  # Добавляем задержку между отправкой сообщений

    await bot.send_message(message.chat.id, "Введите ссылку на товар: ")

async def get_price_async(url):
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    time.sleep(2)
    try:
        current_price = int(driver.find_element(By.XPATH, f'/html/body/div[1]/main/div[2]/div/div[3]/div/div[3]/div[3]/div[1]/div/div/div/p/span/span').text.replace(" ", "").replace("₽", ""))
        return current_price
    except:
        return None

async def check_price():
    global initial_price, graph_price
    current_price = await asyncio.gather(get_price_async(url))
    if current_price is not None:
        graph_price.append(current_price[0])  # Добавляем цену в список graph_price каждую минуту
        if current_price != initial_price:
            await bot.send_message(chat_id, f"Цена товара была изменена на: {current_price}руб.", reply_to_message_id=message_id)
            initial_price = current_price

async def set_url(message: types.Message):
    global url, chat_id, message_id, initial_price, is_tracking, graph_price
    url = message.text
    chat_id = message.chat.id
    message = await bot.send_message(chat_id, "Цена товара будет отслеживаться.")
    message_id = message.message_id
    initial_price = await get_price_async(url)
    print(initial_price)
    graph_price.append(initial_price)  # Добавляем начальную цену в список graph_price

    is_tracking = True

    while True:
        await asyncio.sleep(720 * 60)  # Спит 12 часов
        await check_price()

async def send_graph(chat_id):
    if len(graph_price) >= 2:  # Проверяем, что список graph_price содержит как минимум 2 цены
        fig = plt.figure(figsize=(10, 5))
        temp_name=str(random.randint(1000000, 9999999))
        plt.plot(graph_price)
        plt.xlabel('Время')
        plt.ylabel('Цена')
        plt.title('График изменения цены')
        plt.grid(True)

        fig.savefig(f'x{temp_name}.png')

        await bot.send_photo(chat_id=chat_id,  photo=types.FSInputFile(path=f'x{temp_name}.png'),caption = 'График цены')
        os.remove(f'x{temp_name}.png')
    else:
        await bot.send_message(chat_id, 'Недостаточно данных для построения графика.')

async def stop_tracking(message: types.Message):
    global is_tracking
    is_tracking = False
    await bot.send_message(message.chat.id, "Отслеживание цены остановлено.")

@dp.message(CommandStart())
async def start_command(message: types.Message):
    builder = InlineKeyboardBuilder()
    button1 = InlineKeyboardButton(text="Парс по значениям", callback_data="pars")
    button2 = InlineKeyboardButton(text="Следить за конкретным товаром", callback_data="watch")
    button3 = InlineKeyboardButton(text="Смотреть статистику", callback_data="statistics")
    builder.add(button1, button2, button3)
    await message.answer("Выберите функцию:", reply_markup=builder.as_markup())

@dp.callback_query(lambda c: c.data == "pars")
async def process_pars_button(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, "Введите название товара, количество страниц для поиска, минимальную цену, максимальную цену и минимальный рейтинг через пробел:")

@dp.callback_query(lambda c: c.data == "watch")
async def process_watch_button(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, "Введите ссылку на товар:")

@dp.callback_query(lambda c: c.data == "statistics")
async def process_statistics_button(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await send_graph(callback_query.from_user.id)

@dp.message(Command('graph'))
async def graph_command(message: types.Message):
    await send_graph(message.chat.id)

@dp.message(Command('stop'))
async def stop_command(message: types.Message):
    await stop_tracking(message)
@dp.message(Command('help'))
async def fun_command(message: types.Message):
    await message.reply(text='пропишите /start, выберите нужную функцию, нажмите и действуете как просит бот')
@dp.message()
async def process_user_data(message: types.Message):
    if message.text.startswith('https://www.wildberries.ru/'):
        await set_url(message)
    else:
        await set_user_data(message)

async def main() -> None:
    # Initialize Bot instance with a default parse mode which will be passed to all API calls
    
    # And the run events dispatching
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
    