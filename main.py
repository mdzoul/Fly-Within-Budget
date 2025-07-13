from dotenv import load_dotenv
import os
import requests
import json
import asyncio
import csv
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from contextlib import suppress
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramAPIError

load_dotenv(".env")

SEARCH_HEADERS = {
    "apikey": os.getenv("SEARCH_HEADERS"),
}

TODAY = datetime.now()
SIX_MONTHS_FROM_TODAY = TODAY + relativedelta(months=6)

FLIGHT_DEALS = []

# ----------------------- BROWSE ----------------------- #
def search_geolocation(category, user_input=None):
    with open("location.csv", "r") as csvfile:
        location = csv.DictReader(csvfile)
        if category == "continent":
            countries = set()
            for line in location:
                if line[category] == user_input:
                    countries.add(line["country"])
            country_list = '\n'.join(sorted(countries))
            return country_list
        elif category == "country":
            cities = set()
            for line in location:
                if line[category].lower() == user_input.lower():
                    cities.add(line["cityiataCode"])
            cityiata_list = '\n'.join(sorted(cities))
            return cityiata_list

# ----------------------- FLIGHT_SEARCH ----------------------- #
def flight_response(fly_from, fly_to,
                    departure_date=TODAY.strftime("%d/%m/%Y"),
                    return_date=SIX_MONTHS_FROM_TODAY.strftime("%d/%m/%Y"),
                    baggage=1, stopovers=None):
    parameters = {
        "fly_from": fly_from,
        "fly_to": fly_to,
        "date_from": departure_date,
        "date_to": departure_date,
        "return_from": return_date,
        "return_to": return_date,
        "max_stopovers": stopovers,
        "adult_hold_bag": baggage,
        "curr": "SGD",
    }
    r = requests.get(
        url="https://api.tequila.kiwi.com/v2/search",
        params=parameters,
        headers=SEARCH_HEADERS
    ).json().get("data", [])

    if not r:
        FLIGHT_DEALS.append({"error": "No flights found."})
        return

    if return_date is not None:
        def msg():
            return f"Only SGD{price}\n\n" \
                   f"From {city_from}-{fly_from} " \
                   f"to {city_to}-{fly_to}\n" \
                   f"Departing on {origin_depart}.\n\n" \
                   f"From {city_from_r}-{fly_from_r} " \
                   f"to {city_from}-{fly_from}\n" \
                   f"Departing on {destination_depart} (local time)."

        for flight_check in r[:3]:
            price = round(flight_check["price"], 2)
            city_from = flight_check["cityFrom"]
            fly_from = flight_check["flyFrom"]
            city_to = flight_check["cityTo"]
            fly_to = flight_check["flyTo"]
            origin_depart = datetime.strptime(
                flight_check["route"][0]["local_departure"],
                '%Y-%m-%dT%H:%M:%S.%fZ')
            destination_depart = "[Error retrieving data]"
            city_from_r = ""
            fly_from_r = ""
            link = flight_check["deep_link"]

            for route in flight_check["route"]:
                if route["cityFrom"] == city_to:
                    i = flight_check["route"].index(route)
                    destination_depart = datetime.strptime(
                        flight_check["route"][i]["local_departure"],
                        '%Y-%m-%dT%H:%M:%S.%fZ'
                    )
                    city_from_r = city_to
                    fly_from_r = fly_to
                    break
                elif route["cityTo"] == city_to:
                    j = flight_check["route"].index(route) + 1
                    if j < len(flight_check["route"]):
                        city_from_r = flight_check["route"][j]["cityFrom"]
                        fly_from_r = flight_check["route"][j]["flyFrom"]
                        destination_depart = datetime.strptime(
                            flight_check["route"][j]["local_departure"],
                            '%Y-%m-%dT%H:%M:%S.%fZ'
                        )
                    break

            url = rebrandly_link(link)
            FLIGHT_DEALS.append({f"{url}": f"{msg()}"})

    elif return_date is None:
        def msg():
            return f"Only SGD{price}\n\n" \
                   f"From {city_from}-{fly_from} " \
                   f"to {city_to}-{fly_to}\n" \
                   f"Departing on {local_depart}."

        for flight_check in r[:3]:
            price = round(flight_check["price"], 2)
            city_from = flight_check["cityFrom"]
            fly_from = flight_check["flyFrom"]
            city_to = flight_check["cityTo"]
            fly_to = flight_check["flyTo"]
            local_depart = datetime.strptime(
                flight_check["local_departure"],
                '%Y-%m-%dT%H:%M:%S.%fZ'
            )
            stopover = flight_check["route"][0]["cityTo"]
            link = flight_check["deep_link"]

            if len(flight_check["route"]) == 1:
                url = rebrandly_link(link)
                FLIGHT_DEALS.append({f"{url}": f"{msg()}\n\nDirect flight. No stopovers."})
            elif len(flight_check["route"]) == 2:
                url = rebrandly_link(link)
                FLIGHT_DEALS.append({f"{url}": f"{msg()}\n\nFlight has 1 stopover, via {stopover}."})
            else:
                url = rebrandly_link(link)
                FLIGHT_DEALS.append({f"{url}": f"{msg()}\n\nMultiple stopovers."})

# ----------------------- MULTICITY_SEARCH ----------------------- #
CITY_LIST = []
DEPARTURE_LIST = []

def multicity_search():
    def msg():
        return f"From {city_from}-{fly_from} " \
               f"to {city_to}-{fly_to}\n" \
               f"Departing on {local_depart}."

    city_DEPARTURE_LIST = list(zip(CITY_LIST[1:], DEPARTURE_LIST))
    dictionary = {}
    for i in range(len(CITY_LIST) - 1):
        dictionary[CITY_LIST[i]] = city_DEPARTURE_LIST[i]

    li = []
    for key, value in dictionary.items():
        response = {"to": value[0],
                    "flyFrom": key,
                    "dateFrom": value[1],
                    "dateTo": value[1],
                    "adult_hold_bag": 1,
                    "curr": "SGD"}
        li.append(response)

    parameters = {"requests": li}

    r = requests.post(
        url="https://api.tequila.kiwi.com/v2/flights_multi",
        json=parameters,
        headers={
            "apikey": os.getenv("MULTICITY_HEADERS"),
            "Content-Type": "application/json",
        }
    ).json()

    if not r or not r[0].get("route"):
        return None, "No multicity flights found."

    price = round(r[0]["price"], 2)
    url = rebrandly_link(r[0]["deep_link"])

    for i in range(len(li)):
        city_from = r[0]["route"][i]["cityFrom"]
        fly_from = r[0]["route"][i]["cityCodeFrom"]
        city_to = r[0]["route"][i]["cityTo"]
        fly_to = r[0]["route"][i]["cityCodeTo"]
        local_depart = datetime.strptime(
            r[0]["route"][i]["route"][0]["local_departure"],
            '%Y-%m-%dT%H:%M:%S.%fZ')

        FLIGHT_DEALS.append(f"{msg()}")

    multicity_msg = '\n\n'.join(FLIGHT_DEALS)
    return url, f"Only SGD{price}\n\n{multicity_msg}"

# ----------------------- CURRENT_DEALS ----------------------- #
def cheapest_return(fly_from, fly_to, month, year, stay_len):
    def msg():
        return f"Only SGD{price}\n\n" \
               f"From {city_from}-{fly_from} " \
               f"to {city_to}-{fly_to}\n" \
               f"Departing on {origin_depart}.\n\n" \
               f"From {city_from_r}-{fly_from_r} " \
               f"to {city_from}-{fly_from}\n" \
               f"Departing on {destination_depart} (local time)."

    one_month_from_date = date(year, month, 1) + relativedelta(months=1)
    parameters = {
        "fly_from": fly_from,
        "fly_to": fly_to,
        "date_from": f"01/{month}/{year}",
        "date_to": one_month_from_date.strftime("%d/%m/%Y"),
        "nights_in_dst_from": stay_len,
        "nights_in_dst_to": stay_len,
        "adult_hold_bag": 1,
        "curr": "SGD",
    }
    r = requests.get(
        url="https://api.tequila.kiwi.com/v2/search",
        params=parameters,
        headers=SEARCH_HEADERS
    ).json().get("data", [])

    if not r:
        FLIGHT_DEALS.append({"error": "No flights found."})
        return

    for flight_check in r[:3]:
        price = round(flight_check["price"], 2)
        link = flight_check["deep_link"]
        city_from = flight_check["cityFrom"]
        fly_from = flight_check["flyFrom"]
        city_to = flight_check["cityTo"]
        fly_to = flight_check["flyTo"]
        origin_depart = datetime.strptime(
            flight_check["route"][0]["local_departure"],
            '%Y-%m-%dT%H:%M:%S.%fZ'
        )
        destination_depart = "[Error retrieving data]"
        city_from_r = ""
        fly_from_r = ""
        for route in flight_check["route"]:
            if route["cityFrom"] == city_to:
                i = flight_check["route"].index(route)
                destination_depart = datetime.strptime(
                    flight_check["route"][i]["local_departure"],
                    '%Y-%m-%dT%H:%M:%S.%fZ'
                )
                city_from_r = city_to
                fly_from_r = fly_to
                break
            elif route["cityTo"] == city_to:
                j = flight_check["route"].index(route) + 1
                if j < len(flight_check["route"]):
                    city_from_r = flight_check["route"][j]["cityFrom"]
                    fly_from_r = flight_check["route"][j]["flyFrom"]
                    destination_depart = datetime.strptime(
                        flight_check["route"][j]["local_departure"],
                        '%Y-%m-%dT%H:%M:%S.%fZ'
                    )
                break

        url = rebrandly_link(link)
        FLIGHT_DEALS.append({f"{url}": f"{msg()}"})

# ----------------------- LOCATION_SEARCH ----------------------- #
def location_search(loc):
    parameters = {
        "term": loc,
        "location_types": tuple(location_type for location_type in ["airport", "city", "country"]),
    }
    response = requests.get(
        url="https://api.tequila.kiwi.com/locations/query",
        params=parameters,
        headers=SEARCH_HEADERS
    ).json()
    if not response["locations"]:
        raise IndexError("No location found for input")
    iata_code = response["locations"][0]["code"]
    return iata_code

# ----------------------- AIRLINE_SEARCH ----------------------- #
try:
    airline_get = requests.get(
        url="https://api.sheety.co/f1810fe8ae8de2f741a0e4c58034e85c/flightDeals/airlines",
        auth=("zoul", os.getenv("SHEETY_AUTH")),
    ).json().get("airlines", [])
except KeyError:
    airline_get = []

airline_iata_list = []
airline_name_list = []
for airline in airline_get:
    airline_iata_list.append(airline["iataCode"])
    airline_name_list.append(airline["airline"].upper())

name_iata_dict = dict(zip(airline_iata_list, airline_name_list))

def airline_response(
        flight_type,
        air_line,
        fly_from,
        fly_to,
        departure_date,
        return_date=None
):
    def msg_oneway():
        return f"Only SGD{price}\n" \
               f"With {name_iata_dict.get(air_line, air_line).title()} ({air_line})\n\n" \
               f"From {city_from}-{fly_from} " \
               f"to {city_to}-{fly_to}\n" \
               f"Departing on {origin_depart}."

    def msg_return():
        return f"Only SGD{price}\n" \
               f"With {name_iata_dict.get(air_line, air_line).title()} ({air_line})\n\n" \
               f"From {city_from}-{fly_from} " \
               f"to {city_to}-{fly_to}\n" \
               f"Departing on {origin_depart}.\n\n" \
               f"From {city_to}-{fly_to} " \
               f"to {city_from}-{fly_from}\n" \
               f"Departing on {destination_depart} (local time)."

    parameters = {
        "fly_from": fly_from,
        "fly_to": fly_to,
        "date_from": departure_date,
        "date_to": departure_date,
        "return_from": return_date,
        "return_to": return_date,
        "max_stopovers": 0,
        "adult_hold_bag": 1,
        "select_airlines": air_line,
        "select_airlines_exclude": False,
        "curr": "SGD",
    }
    r = requests.get(
        url="https://api.tequila.kiwi.com/v2/search",
        params=parameters,
        headers=SEARCH_HEADERS
    ).json().get("data", [])

    if not r:
        FLIGHT_DEALS.append({"error": "No flights found."})
        return

    for flight_check in r[:3]:
        price = round(flight_check["price"], 2)
        link = flight_check["deep_link"]
        city_from = flight_check["cityFrom"]
        fly_from = flight_check["flyFrom"]
        city_to = flight_check["cityTo"]
        fly_to = flight_check["flyTo"]
        origin_depart = datetime.strptime(
            flight_check["route"][0]["local_departure"],
            '%Y-%m-%dT%H:%M:%S.%fZ'
        )
        destination_depart = "[Not specified by airline]"
        for route in flight_check["route"]:
            if route["flyFrom"] == fly_to:
                i = flight_check["route"].index(route)
                destination_depart = datetime.strptime(
                    flight_check["route"][i]["local_departure"],
                    '%Y-%m-%dT%H:%M:%S.%fZ'
                )
                break
        url = rebrandly_link(link)
        if flight_type == "airline_oneway":
            FLIGHT_DEALS.append({f"{url}": f"{msg_oneway()}"})
        elif flight_type == "airline_return":
            FLIGHT_DEALS.append({f"{url}": f"{msg_return()}"})

# ----------------------- SHORT_URL ----------------------- #
HEADERS = {
    "Content-type": "application/json",
    "apikey": os.getenv("REBRANDLY_AUTH"),
}

def rebrandly_link(link):
    link_params = {
        "destination": link,
        "domain": {
            "fullName": "flywithinbudget.link",
        },
    }
    rebranded_link_post = requests.post(
        url="https://api.rebrandly.com/v1/links",
        data=json.dumps(link_params),
        headers=HEADERS
    )
    if rebranded_link_post.status_code == requests.codes.ok:
        short_link = rebranded_link_post.json()["shortUrl"]
        return f"https://{short_link}"

# ----------------------- TELEGRAM_BOT ----------------------- #
bot = Bot(token=os.getenv("TELE_TOKEN"))
dp = Dispatcher()
storage = MemoryStorage()  # Only needed if you use custom storage, but default is fine

# When starting polling, pass bot and storage:
async def main():
    print("Bot is running and polling Telegram...")
    await dp.start_polling(bot, storage=storage)

class Form(StatesGroup):
    user = State()
    origin = State()
    airline = State()
    search_direct_flight_qn = State()
    incl_baggage = State()
    city = State()
    d_date = State()
    rd_date = State()
    rr_date = State()
    month_year = State()
    stay_length = State()
    continent = State()
    country = State()
    user_input = State()
    multi_city = State()
    multi_date = State()
    airline_city = State()
    airline_origin = State()
    airline_d_date = State()
    airline_rd_date = State()
    airline_rr_date = State()
    city_code = State()  # <-- add this

btn_cancel = InlineKeyboardButton(text="Cancel", callback_data="cancel")
keyboard_cancel = InlineKeyboardMarkup(inline_keyboard=[[btn_cancel]])

btn_direct_yes = InlineKeyboardButton(text="Yes", callback_data="yes")
btn_direct_no = InlineKeyboardButton(text="No", callback_data="no")
keyboard_yes_no = InlineKeyboardMarkup(inline_keyboard=[[btn_direct_no, btn_direct_yes], [btn_cancel]])

async def delete_message(message: types.Message):
    with suppress(TelegramAPIError):
        await message.delete()

@dp.message(Command("start"))
async def welcome(message: types.Message):
    btn_about = InlineKeyboardButton(text="About Fly Within Budget (FWB)", callback_data="about")
    keyboard_about = InlineKeyboardMarkup().add(btn_about)
    await message.answer(
        "Welcome to Fly Within Budget (FWB)",
        reply_markup=keyboard_about
    )
    await message.answer(
        "Type a city or country to search for flights\n\n"
        "Type /help to see available commands"
    )

@dp.callback_query(lambda c: c.data == "about")
async def about(query: types.CallbackQuery):
    await query.message.answer(
        "This service is currently in its alpha phase"
        "\n\nFly Within Budget (FWB) shows the cheapest flight deals as of the current search"
        "\n\nYou can search by airline, destination city/country, "
        "and one-way, return or multi-city flights"
        "\n\nThinking of going someplace new on your next travel? "
        "Try /browse and see all available international airports"
        "\n\nEnjoy your travels, fellow wanderer!"
    )

@dp.message(Command("help"))
async def help_(message: types.Message):
    await message.answer(
        "Available commands:\n"
        "browse - Find your next travel destination\n"
        "airline - Search flights by airline\n"
        "multicity - Search multi-city flights\n"
        "cancel - Cancel any action"
    )

@dp.message(Command("cancel"), StateFilter(None))
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer('No active action to cancel')
    else:
        await state.clear()
        await message.answer('Action cancelled')

@dp.callback_query(lambda c: c.data == "cancel", StateFilter(None))
async def cancel_callback(query: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await query.message.answer('Action cancelled')

@dp.message(Command("multicity"))
async def multi_search(message: types.Message, state: FSMContext):
    await state.set_state(Form.multi_city)
    await message.answer(
        "You will be asked to input a list of cities and the corresponding departure dates\n\n"
        "Each city and date are to be separated by using the '>' symbol with no spaces\n\n"
        "E.g. assuming you are departing from Singapore, visiting 2 cities and "
        "returning back to Singapore:\n\n"
        "Singapore>Kuala Lumpur>London>Singapore\n"
        "01/01/2023>09/01/2023>16/01/2023"
    )
    await message.answer("Please input list of cities", reply_markup=keyboard_cancel)

@dp.message(StateFilter(Form.multi_city))
async def multi_city_handler(message: types.Message, state: FSMContext):
    await state.update_data(multi_city=message.text)
    await state.set_state(Form.multi_date)
    await message.answer("Please input departure dates")

@dp.message(StateFilter(Form.multi_date))
async def multi_date_handler(message: types.Message, state: FSMContext):
    load_msg = await message.answer("Fetching data...")
    data = await state.get_data()
    city_names = data['multi_city'].split(">")
    for city in city_names:
        try:
            iata_code = location_search(city)
        except IndexError:
            asyncio.create_task(delete_message(load_msg))
            await message.answer("Invalid input. Please restart")
            await state.clear()
            return
        else:
            CITY_LIST.append(iata_code)
    DEPARTURE_LIST.extend(message.text.split(">"))
    asyncio.create_task(delete_message(load_msg))
    if len(DEPARTURE_LIST) == len(CITY_LIST) - 1:
        link, text = multicity_search()
        if link is None:
            await message.answer(text)
        else:
            keyboard = InlineKeyboardMarkup()
            button = InlineKeyboardButton(link, url=link)
            keyboard.add(button)
            await message.answer(text, reply_markup=keyboard)
            await message.answer("Enjoy your travels, fellow wanderer!")
    else:
        await message.answer("Number of departure dates do not tally. Please restart")
    FLIGHT_DEALS.clear()
    CITY_LIST.clear()
    DEPARTURE_LIST.clear()
    await state.clear()

@dp.message(Command("airline"))
async def airline_search(message: types.Message, state: FSMContext):
    await state.set_state(Form.airline)
    await message.answer(
        "Please input full airline name (e.g. Singapore Airlines) "
        "or airline code (e.g. SQ)", reply_markup=keyboard_cancel
    )

@dp.message(StateFilter(Form.airline))
async def airline_city_handler(message: types.Message, state: FSMContext):
    airline = message.text.upper()
    await state.update_data(airline=airline)
    if len(airline) == 2:
        if airline in airline_iata_list:
            await state.set_state(Form.airline_city)
            await message.answer("Please input destination city")
        else:
            await message.answer(f"'{airline}' does not exist. Please restart")
            await state.clear()
    else:
        if airline in airline_name_list:
            for key, value in name_iata_dict.items():
                if airline == value:
                    await state.update_data(airline=key)
                    await state.set_state(Form.airline_city)
                    await message.answer("Please input destination city")
        else:
            await message.answer(f"'{airline}' does not exist. Please restart")
            await state.clear()

@dp.message(StateFilter(Form.airline_city))
async def airline_origin_handler(message: types.Message, state: FSMContext):
    airline_city = message.text.upper()
    await state.update_data(airline_city=airline_city)
    try:
        location_search(airline_city)
    except IndexError:
        await message.answer(f"Unable to find {airline_city} on the map 🗺️")
        await state.clear()
    else:
        await state.set_state(Form.airline_origin)
        await message.answer("Which city are you departing from?")

@dp.message(StateFilter(Form.airline_origin))
async def airline_flight_handler(message: types.Message, state: FSMContext):
    airline_origin = message.text.upper()
    await state.update_data(airline_origin=airline_origin)
    btn_airline_oneway = InlineKeyboardButton(text="One-way", callback_data="airline_oneway")
    btn_airline_return = InlineKeyboardButton(text="Return", callback_data="airline_return")
    keyboard_airline = InlineKeyboardMarkup().add(btn_airline_oneway, btn_airline_return)
    await message.answer("Choose one-way or return flight", reply_markup=keyboard_airline)

@dp.callback_query(lambda c: c.data in ["airline_oneway", "airline_return"], StateFilter(Form.airline_origin))
async def airline_type_handler(query: types.CallbackQuery, state: FSMContext):
    if query.data == "airline_oneway":
        await state.set_state(Form.airline_d_date)
        await query.message.answer("One-way flight:")
        await query.message.answer("Please input date in the format:\nDD/MM/YYYY")
    elif query.data == "airline_return":
        await state.set_state(Form.airline_rd_date)
        await query.message.answer("Return flight:")
        await query.message.answer("Please input departure date in the format:\nDD/MM/YYYY")

@dp.message(StateFilter(Form.airline_d_date))
async def airline_oneway_date_handler(message: types.Message, state: FSMContext):
    load_msg = await message.answer("Fetching data...")
    data = await state.get_data()
    try:
        city_code = location_search(data["airline_city"])
        origin_code = location_search(data["airline_origin"])
        airline_response(
            "airline_oneway",
            data["airline"],
            origin_code,
            city_code,
            message.text
        )
    except Exception:
        asyncio.create_task(delete_message(load_msg))
        await message.answer("Invalid input. Please restart")
        await state.clear()
        return
    else:
        asyncio.create_task(delete_message(load_msg))
        for flight in FLIGHT_DEALS:
            for link, text in flight.items():
                keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=link, url=link)]])
                await message.answer(text, reply_markup=keyboard)
        await message.answer("Enjoy your travels, fellow wanderer!")
    FLIGHT_DEALS.clear()
    await state.clear()

@dp.message(StateFilter(Form.airline_rd_date))
async def airline_return_departure_handler(message: types.Message, state: FSMContext):
    await state.update_data(airline_rd_date=message.text)
    await state.set_state(Form.airline_rr_date)
    await message.answer("Please input return date in the format:\nDD/MM/YYYY")

@dp.message(StateFilter(Form.airline_rr_date))
async def airline_return_date_handler(message: types.Message, state: FSMContext):
    load_msg = await message.answer("Fetching data...")
    data = await state.get_data()
    try:
        city_code = location_search(data["airline_city"])
        origin_code = location_search(data["airline_origin"])
        airline_response(
            "airline_return",
            data["airline"],
            origin_code,
            city_code,
            data["airline_rd_date"],
            message.text
        )
    except Exception:
        asyncio.create_task(delete_message(load_msg))
        await message.answer("Invalid input. Please restart")
        await state.clear()
        return
    else:
        asyncio.create_task(delete_message(load_msg))
        for flight in FLIGHT_DEALS:
            for link, text in flight.items():
                keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(link, url=link)]])
                await message.answer(text, reply_markup=keyboard)
        await message.answer("Enjoy your travels, fellow wanderer!")
    FLIGHT_DEALS.clear()
    await state.clear()

@dp.message(Command("browse"))
async def continent(message: types.Message, state: FSMContext):
    await state.set_state(Form.continent)
    await message.answer(
        "Browse and find your next travel destination\n\n"
        "IMPORTANT:\nType the exact word for results"
    )
    await message.answer(
        "Available continents:\n\n"
        "Africa 🌍\nAmericas 🌎\nAsia 🌏\nEurope 🌍\nOceania 🌏\n\n"
    )
    await message.answer("Enter a continent:", reply_markup=keyboard_cancel)

@dp.message(StateFilter(Form.continent))
async def country_handler(message: types.Message, state: FSMContext):
    continent = message.text.title()
    await state.update_data(continent=continent)
    await state.set_state(Form.country)
    await message.answer(
        f"Available countries in {continent}:\n\n"
        f"{search_geolocation('continent', continent)}"
    )
    await message.answer("Enter a country:", reply_markup=keyboard_cancel)

@dp.message(StateFilter(Form.country))
async def city_handler(message: types.Message, state: FSMContext):
    country = message.text.title()
    await message.answer(
        f"Available cities in {country}:\n\n"
        f"{search_geolocation('country', country)}",
        reply_markup=keyboard_cancel
    )
    await message.answer("Enter the 3-character city code:", reply_markup=keyboard_cancel)
    await state.set_state(Form.city_code)  # <-- set state for city code input

@dp.message(StateFilter(Form.city_code))
async def city_code_handler(message: types.Message, state: FSMContext):
    city_code = message.text.strip().upper()
    load_msg = await message.answer("Searching for cheapest flights...")
    try:
        # You may want to use a default origin, or ask for it earlier in the flow
        origin_code = "SIN"  # Example: Singapore as origin
        flight_response(origin_code, city_code)
        if not FLIGHT_DEALS or (len(FLIGHT_DEALS) == 1 and "error" in FLIGHT_DEALS[0]):
            await message.answer("No flights found.")
        else:
            for flight in FLIGHT_DEALS:
                for link, text in flight.items():
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=link, url=link)]])
                    await message.answer(text, reply_markup=keyboard)
            await message.answer("Enjoy your travels, fellow wanderer!")
    except Exception as e:
        await message.answer(f"Error searching flights: {e}")
    finally:
        FLIGHT_DEALS.clear()
        await state.clear()
        asyncio.create_task(delete_message(load_msg))

@dp.message()
async def handle_text(message: types.Message, state: FSMContext):
    text = message.text.strip().lower()
    if text == "start":
        await welcome(message)
    elif text == "help":
        await help_(message)
    elif text == "cancel":
        await cancel_handler(message, state)
    elif text == "multicity":
        await multi_search(message, state)
    elif text == "airline":
        await airline_search(message, state)
    elif text == "browse":
        await continent(message, state)
    else:
        await message.answer("Sorry, I didn't understand that. Type /help for available commands.")

# TODO: Check all API endpoints (Tequila, Sheety, Rebrandly) for reliability and error handling
# TODO: Migrate location.csv data to a MySQL database for future-proofing
# TODO: Refactor location.csv usage to use database queries instead

async def main():
    print("Bot is running and polling Telegram...")
    await dp.start_polling(bot, storage=storage)

if __name__ == "__main__":
    asyncio.run(main())
