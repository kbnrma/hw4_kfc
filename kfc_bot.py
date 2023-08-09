from aiogram import Bot, Dispatcher, types, executor
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.storage import FSMContext
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv
import sqlite3, logging, os, time

load_dotenv('.env')

bot = Bot(os.environ.get('token'))
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
logging.basicConfig(level=logging.INFO)


inline_buttons = [
    InlineKeyboardButton('Отправить номер', callback_data='phone_number'),
    InlineKeyboardButton('Отправить локацию', callback_data='location'),
    InlineKeyboardButton('Заказать еду', callback_data='order')
]
inline_keyboard = InlineKeyboardMarkup().add(*inline_buttons)

verify_button1 = [
    KeyboardButton('Отправить номер', request_contact=True)
]
verify_keyboard1 = ReplyKeyboardMarkup(one_time_keyboard=True,resize_keyboard=True).add(*verify_button1)

verify_button2 = [
    KeyboardButton('Отправить локацию', request_location=True)
]
verify_keyboard2 = ReplyKeyboardMarkup(one_time_keyboard=True,resize_keyboard=True).add(*verify_button2)


database = sqlite3.connect('users.db')
cursor = database.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    phone_number VARCHAR(255)
);
""")
cursor.connection.commit()

database = sqlite3.connect('users.db')
cursor = database.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS address(
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    address_latitude DOUBLE(2, 6),
    address_longitude DOUBLE (2, 6)
);
""")
cursor.connection.commit()

database = sqlite3.connect('users.db')
cursor = database.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS orders(
    title VARCHAR(255),
    address_destination VARCHAR(255),
    time_date_order VARCHAR (255)
);
""")
cursor.connection.commit()


class OrderState(StatesGroup):
    food = State()
    address = State()


@dp.message_handler(commands='start')
async def start(message:types.Message):
    cursor.execute(f"SELECT * FROM users WHERE user_id = '{message.from_user.id}';")
    result = cursor.fetchall()
    if result == []:
        cursor.execute(f"""INSERT INTO users (user_id, username, first_name, last_name) VALUES ({message.from_user.id},
                    '{message.from_user.username}',
                    '{message.from_user.first_name}', 
                    '{message.from_user.last_name}');
                    """)
    cursor.connection.commit()
    await message.answer(f"Здравствуйте,{message.from_user.full_name}.\nЧтобы сделать заказ сперва нажмите на кнопку 'Отправить номер'.\nПотом нажмите на кнопку 'Отправить адрес'.\nПосле выполнения этих пунктов нажмите на кнопку 'Заказать еду'.\nЕсли вы выполнили все три пункта, то в скором времени придет ваш заказ.", reply_markup=inline_keyboard)


@dp.callback_query_handler(lambda call: call)
async def inline(call):
    if call.data == "phone_number":
        await send_number(call.message)
    elif call.data == "location":
        await send_location(call.message)
    elif call.data == 'order':
        await bot.send_message(call.message.chat.id, 'Отправьте свой заказ.')
        await OrderState.food.set()


@dp.message_handler(commands="contact")
async def send_number(msg:types.Message):
    await msg.answer("Отправьте свой номер телефона.", reply_markup=verify_keyboard1)

@dp.message_handler(content_types=types.ContentTypes.CONTACT)
async def get_phone_number(message:types.Message):
    cursor.execute(f"""UPDATE users SET phone_number = {message.contact.phone_number} 
                   WHERE user_id = {message.from_user.id};""")
    cursor.connection.commit()
    await message.answer("Ваш номер телефона успешно записан.")


@dp.message_handler(commands="location")
async def send_location(msg:types.Message):
    await msg.answer("Отправьте свой адрес.", reply_markup=verify_keyboard2)

@dp.message_handler(content_types=types.ContentTypes.LOCATION)
async def get_location(message:types.Message):
    cursor.execute(f"SELECT * FROM address WHERE user_id = '{message.from_user.id}';")
    result = cursor.fetchall()
    if result == []:
        cursor.execute(f"""INSERT INTO address (user_id, address_latitude, address_longitude) VALUES ({message.from_user.id},'{message.location.latitude}','{message.location.longitude}');""")
    cursor.connection.commit()
    await message.answer('Ваша локация успешно записана.')


@dp.message_handler(state=OrderState.food)
async def get_order(message:types.Message, state: FSMContext):
    await state.update_data(eda=message.text)
    await message.answer('Еще отправьте свой адрес.')
    await OrderState.address.set()


@dp.message_handler(state=OrderState.address)
async def get_address(message:types.Message, state: FSMContext):
    await state.update_data(adres=message.text)
    data = await state.get_data()
    cursor.execute(f"""INSERT INTO orders (title, address_destination, time_date_order) VALUES ('{data['eda']}','{data['adres']}', '{time.ctime()}');""")
    cursor.connection.commit()
    await state.finish()
    await message.answer('Спасибо, что заказываете еду у нас)\nПриятного вам аппетита')

executor.start_polling(dp)