import requests
import json
import asyncio
import csv
import aiogram.utils.markdown as md
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from contextlib import suppress
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.exceptions import MessageCantBeDeleted, MessageToDeleteNotFound

SEARCH_HEADERS = {
    "apikey": "fi7uUtSyu4MjJmFs_fBdi2PQu3nfj0GD",
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
    ).json()["data"]

    if return_date is not None:
        def msg():
            return f"Only SGD{price}\n\n" \
                   f"From {city_from}-{fly_from} " \
                   f"to {city_to}-{fly_to}\n" \
                   f"Departing on {origin_depart}.\n\n" \
                   f"From {city_from_r}-{fly_from_r} " \
                   f"to {city_from}-{fly_from}\n" \
                   f"Departing on {destination_depart} (local time)."

        for index in range(3):
            flight_check = r[index]

            price = round(flight_check["price"], 2)
            city_from = flight_check["cityFrom"]
            fly_from = flight_check["flyFrom"]
            city_to = flight_check["cityTo"]
            fly_to = flight_check["flyTo"]
            origin_depart = datetime.strptime(
                flight_check["route"][0]["local_departure"],
                '%Y-%m-%dT%H:%M:%S.%fZ')
            destination_depart = "[Error retrieving data]"
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
                else:
                    if route["cityTo"] == city_to:
                        j = flight_check["route"].index(route) + 1
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

        for index in range(3):
            flight_check = r[index]

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
            "apikey": "4deR5aEQSpH_f3xlA1iRhaIgXi8FQc1s",
            "Content-Type": "application/json",
        }
    ).json()

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
    ).json()["data"]

    for index in range(3):
        flight_check = r[index]

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
            else:
                if route["cityTo"] == city_to:
                    j = flight_check["route"].index(route) + 1
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

    iata_code = requests.get(
        url="https://api.tequila.kiwi.com/locations/query",
        params=parameters,
        headers=SEARCH_HEADERS
    ).json()["locations"][0]["code"]

    return iata_code


# ----------------------- AIRLINE_SEARCH ----------------------- #
airline_get = requests.get(
    url="https://api.sheety.co/f1810fe8ae8de2f741a0e4c58034e85c/flightDeals/airlines",
    auth=("zoul", "#72rv+vaesj7t#"),
).json()["airlines"]

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
               f"With {name_iata_dict[air_line].title()} ({air_line})\n\n" \
               f"From {city_from}-{fly_from} " \
               f"to {city_to}-{fly_to}\n" \
               f"Departing on {origin_depart}."

    def msg_return():
        return f"Only SGD{price}\n" \
               f"With {name_iata_dict[air_line].title()} ({air_line})\n\n" \
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
    ).json()["data"]

    for index in range(3):
        flight_check = r[index]
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
    "apikey": "0cbd30c1b43d45e6842d72f5faa5675e",
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
bot = Bot(token="5609440570:AAH944kRnv6ze3CCfGygK3I9fbRAyl7XIlc")
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


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


btn_cancel = InlineKeyboardButton(text="Cancel", callback_data="cancel")
keyboard_cancel = InlineKeyboardMarkup().add(btn_cancel)

btn_direct_yes = InlineKeyboardButton(text="Yes", callback_data="yes")
btn_direct_no = InlineKeyboardButton(text="No", callback_data="no")
keyboard_yes_no = InlineKeyboardMarkup().add(btn_direct_no, btn_direct_yes).add(btn_cancel)


async def delete_message(message: types.Message):
    with suppress(MessageCantBeDeleted, MessageToDeleteNotFound):
        await message.delete()


@dp.message_handler(commands="start")
@dp.message_handler(Text(equals='start', ignore_case=False))
async def welcome(message: types.Message):
    btn_about = InlineKeyboardButton(text="About Fly Within Budget (FWB)", callback_data="about")
    keyboard_about = InlineKeyboardMarkup().add(btn_about)
    await bot.send_message(
        message.chat.id,
        md.text("Welcome to Fly Within Budget (FWB)"),
        reply_markup=keyboard_about
    )

    @dp.callback_query_handler(text="about")
    async def about(query: types.CallbackQuery):
        await query.message.answer(
            "This service is currently in its alpha phase"
            "\n\nFly Within Budget (FWB) shows the cheapest flight deals as of the current search"
            "\n\nYou can search by airline, destination city/country, "
            "and one-way, return or multi-city flights"
            "\n\nThinking of going someplace new on your next travel? "
            "Try /browse and see all available international airports"
            "\n\nDo report any bugs experienced or features you want to see implemented @zoulaimi")

    await bot.send_message(
        message.chat.id,
        md.text("Type a city or country to search for flights\n\n"
                "Type /help to see available commands"))


@dp.message_handler(commands="help")
@dp.message_handler(Text(equals='help', ignore_case=False))
async def help_(message: types.Message):
    await message.answer(
        "Available commands:\n"
        "browse - Find your next travel destination\n"
        "airline - Search flights by airline\n"
        "multicity - Search multi-city flights\n"
        "cancel - Cancel any action")


@dp.message_handler(state='*', commands='cancel')
@dp.message_handler(Text(equals='cancel', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer('No active action to cancel')
    else:
        await state.finish()
        await message.answer('Action cancelled')


@dp.message_handler(commands="multicity")
@dp.message_handler(Text(equals='multicity', ignore_case=False))
async def multi_search(message: types.CallbackQuery):
    await Form.multi_city.set()
    await message.answer("You will be asked to input a list of cities and the corresponding departure dates\n\n"
                         "Each city and date are to be separated by using the '>' symbol with no spaces\n\n"
                         "E.g. assuming you are departing from Singapore, visiting 2 cities and "
                         "returning back to Singapore:\n\n"
                         "Singapore>Kuala Lumpur>London>Singapore\n"
                         "01/01/2023>09/01/2023>16/01/2023")
    await message.answer("Please input list of cities", reply_markup=keyboard_cancel)

    @dp.message_handler(state=Form.multi_city)
    async def multi_city(message: types.Message, state: FSMContext):
        async with state.proxy() as data:
            data['multi_city'] = message.text
        await Form.next()
        await message.answer("Please input departure dates")

    @dp.message_handler(state=Form.multi_date)
    async def multi_date(message: types.Message, state: FSMContext):
        load_msg = await message.answer("Fetching data...")
        async with state.proxy() as data:
            data['multi_date'] = message.text
        city_names = data['multi_city'].split(">")
        for city in city_names:
            try:
                iata_code = location_search(city)
            except IndexError:
                asyncio.create_task(delete_message(load_msg))
                await message.answer("Invalid input. Please restart")
                await state.finish()
            else:
                CITY_LIST.append(iata_code)
        DEPARTURE_LIST.extend(data['multi_date'].split(">"))
        asyncio.create_task(delete_message(load_msg))
        if len(DEPARTURE_LIST) == len(CITY_LIST) - 1:
            link, text = multicity_search()
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
        await state.finish()


@dp.message_handler(commands="airline")
@dp.message_handler(Text(equals='airline', ignore_case=False))
async def airline_search(message: types.CallbackQuery):
    await Form.airline.set()
    await message.answer("Please input full airline name (e.g. Singapore Airlines) "
                         "or airline code (e.g. SQ)", reply_markup=keyboard_cancel)

    @dp.message_handler(state=Form.airline)
    async def airline_city(message: types.Message, state: FSMContext):
        async with state.proxy() as data:
            data['airline'] = message.text.upper()
        if len(data["airline"]) == 2:
            if data["airline"] in airline_iata_list:
                await Form.airline_city.set()
                await message.answer("Please input destination city")
            else:
                await message.answer(f"'{data['airline']}' does not exist. Please restart")
                await state.finish()
        else:
            if data["airline"] in airline_name_list:
                for key, value in name_iata_dict.items():
                    if data['airline'] == value:
                        async with state.proxy() as data:
                            data['airline'] = key
                        await Form.airline_city.set()
                        await message.answer("Please input destination city")
            else:
                await message.answer(f"'{data['airline']}' does not exist. Please restart")
                await state.finish()

    @dp.message_handler(state=Form.airline_city)
    async def open_input(message: types.Message, state: FSMContext):
        async with state.proxy() as data:
            data['airline_city'] = message.text.upper()
        try:
            location_search(data["airline_city"])
        except IndexError:
            await message.answer(f"Unable to find {data['city']} on the map 🗺️")
            await state.finish()
        else:
            await Form.airline_origin.set()
            await message.answer("Which city are you departing from?")

    @dp.message_handler(state=Form.airline_origin)
    async def airline_flight(message: types.Message, state: FSMContext):
        async with state.proxy() as data:
            data['airline_origin'] = message.text.upper()

        btn_airline_oneway = InlineKeyboardButton(text="One-way", callback_data="airline_oneway")
        btn_airline_return = InlineKeyboardButton(text="Return", callback_data="airline_return")

        keyboard_airline = InlineKeyboardMarkup().add(btn_airline_oneway, btn_airline_return)

        await message.answer("Choose one-way or return flight",
                             reply_markup=keyboard_airline)

    @dp.callback_query_handler(text=["airline_oneway", "airline_return"], state=Form.airline_origin)
    async def airline_oneway(query: types.CallbackQuery, state: FSMContext):
        if query.data == "airline_oneway":
            await Form.airline_d_date.set()
            await query.message.answer("One-way flight:")
            await query.message.answer("Please input date in the format:\nDD/MM/YYYY")

            @dp.message_handler(state=Form.airline_d_date)
            async def airline_oneway_d_date(message: types.Message, state: FSMContext):
                load_msg = await message.answer("Fetching data...")
                async with state.proxy() as data:
                    data['airline_d_date'] = message.text

                    try:
                        city_code = location_search(data["airline_city"])
                        origin_code = location_search(data["airline_origin"])
                    except KeyError or json.decoder.JSONDecodeError:
                        asyncio.create_task(delete_message(load_msg))
                        await message.answer("Invalid date. Please restart")
                        await state.finish()
                    except IndexError:
                        asyncio.create_task(delete_message(load_msg))
                        await message.answer("Invalid destination city. Please restart")
                        await state.finish()
                    else:
                        try:
                            airline_response(
                                "airline_oneway",
                                data["airline"],
                                origin_code,
                                city_code,
                                data["airline_d_date"])
                        except IndexError:
                            await message.answer(
                                f"{name_iata_dict[data['airline']].title()} does not fly to {data['airline_city'].title()}"
                            )
                        else:
                            asyncio.create_task(delete_message(load_msg))
                            for flight in FLIGHT_DEALS:
                                for link, text in flight.items():
                                    keyboard = InlineKeyboardMarkup()
                                    button = InlineKeyboardButton(link, url=link)
                                    keyboard.add(button)
                                    await message.answer(text, reply_markup=keyboard)
                            await message.answer("Enjoy your travels, fellow wanderer!")
                    finally:
                        FLIGHT_DEALS.clear()

                await state.finish()

        elif query.data == "airline_return":
            await Form.airline_rd_date.set()
            await query.message.answer("Return flight:")
            await query.message.answer("Please input departure date in the format:\nDD/MM/YYYY")

            @dp.message_handler(state=Form.airline_rd_date)
            async def airline_r_search(message: types.Message, state: FSMContext):
                async with state.proxy() as data:
                    data['airline_rd_date'] = message.text
                await Form.airline_rr_date.set()
                await message.answer("Please input return date in the format:\nDD/MM/YYYY")

                @dp.message_handler(state=Form.airline_rr_date)
                async def airline_return_query(message: types.Message, state: FSMContext):
                    load_msg = await message.answer("Fetching data...")
                    async with state.proxy() as data:
                        data['airline_rr_date'] = message.text

                        try:
                            city_code = location_search(data["airline_city"])
                            origin_code = location_search(data["airline_origin"])
                        except KeyError or json.decoder.JSONDecodeError:
                            asyncio.create_task(delete_message(load_msg))
                            await message.answer("Invalid date. Please restart")
                            await state.finish()
                        except IndexError:
                            asyncio.create_task(delete_message(load_msg))
                            await message.answer("Invalid destination city. Please restart")
                            await state.finish()
                        else:
                            try:
                                airline_response(
                                    "airline_return",
                                    data["airline"],
                                    origin_code,
                                    city_code,
                                    data["airline_rd_date"],
                                    data["airline_rr_date"]
                                )
                            except IndexError:
                                await message.answer(
                                    f"{name_iata_dict[data['airline']].title()} does not fly to {data['airline_city'].title()}"
                                )
                            else:
                                asyncio.create_task(delete_message(load_msg))
                                for flight in FLIGHT_DEALS:
                                    for link, text in flight.items():
                                        keyboard = InlineKeyboardMarkup()
                                        button = InlineKeyboardButton(link, url=link)
                                        keyboard.add(button)
                                        await message.answer(text, reply_markup=keyboard)
                                await message.answer("Enjoy your travels, fellow wanderer!")
                        finally:
                            FLIGHT_DEALS.clear()

                    await state.finish()


@dp.message_handler(commands="browse")
@dp.message_handler(Text(equals='browse', ignore_case=False))
async def continent(message: types.Message):
    await Form.continent.set()
    await message.answer("Browse and find your next travel destination\n\n"
                         "IMPORTANT:\nType the exact word for results")
    await message.answer("Available continents:\n\n"
                         "Africa 🌍\nAmericas 🌎\nAsia 🌏\nEurope 🌍\nOceania 🌏\n\n")
    await message.answer("Enter a continent:", reply_markup=keyboard_cancel)

    @dp.message_handler(state=Form.continent)
    async def country(message_country: types.Message, state: FSMContext):
        async with state.proxy() as data:
            data['continent'] = message_country.text.title()
        await Form.country.set()
        await message_country.answer(f"Available countries in {data['continent']}:\n\n"
                                     f"{search_geolocation('continent', data['continent'])}")
        await message_country.answer("Enter a country:", reply_markup=keyboard_cancel)

    @dp.message_handler(state=Form.country)
    async def city(message_city: types.Message, state: FSMContext):
        async with state.proxy() as data:
            data['country'] = message_city.text.title()
        await message_city.answer(f"Available cities in {data['country']}:\n\n"
                                  f"{search_geolocation('country', data['country'])}",
                                  reply_markup=keyboard_cancel)
        await message_city.answer("Enter the 3-character city code:", reply_markup=keyboard_cancel)
        await state.finish()


@dp.message_handler()
async def open_input(message: types.Message, state: FSMContext):
    await Form.city.set()
    async with state.proxy() as data:
        data['city'] = message.text.upper()
    try:
        location_search(data["city"])
    except IndexError:
        await message.answer(f"Unable to find {data['city']} on the map 🗺️")
        await state.finish()
    else:
        await Form.origin.set()
        await message.answer("Which city are you departing from?")

    @dp.message_handler(state=Form.origin)
    async def oneway_d_date(message: types.Message, state: FSMContext):
        async with state.proxy() as data:
            data['origin'] = message.text.upper()

        btn_airline_oneway = InlineKeyboardButton(text="One-way", callback_data="oneway")
        btn_airline_return = InlineKeyboardButton(text="Return", callback_data="return")
        btn_deals = InlineKeyboardButton(text="Current Deals", callback_data="deals")

        keyboard_other = InlineKeyboardMarkup().add(btn_airline_oneway).add(btn_airline_return).add(btn_deals).add(
            btn_cancel)

        await message.answer(
            f"Choose one-way or return flight, or see current deals from {data['origin']} to {data['city']}",
            reply_markup=keyboard_other)

        @dp.callback_query_handler(text=["oneway", "return", "deals"], state=Form.origin)
        async def callback(query: types.CallbackQuery, state: FSMContext):
            if query.data == "oneway":
                await Form.d_date.set()
                await query.message.answer("One-way flight:")
                await query.message.answer("Please input date in the format:\nDD/MM/YYYY")

                @dp.message_handler(state=Form.d_date)
                async def oneway_d_date(message: types.Message, state: FSMContext):
                    async with state.proxy() as data:
                        data['d_date'] = message.text
                    await Form.incl_baggage.set()
                    await message.answer("Include checked baggage?", reply_markup=keyboard_yes_no)

                @dp.callback_query_handler(text=("yes", "no"), state=Form.incl_baggage)
                async def oneway_baggage_query(query: types.CallbackQuery, state: FSMContext):
                    async with state.proxy() as data:
                        data["incl_baggage"] = query.data
                    await Form.search_direct_flight_qn.set()
                    await message.answer("Search for direct flights only?", reply_markup=keyboard_yes_no)

                @dp.callback_query_handler(text=("yes", "no"), state=Form.search_direct_flight_qn)
                async def oneway_direct_flight_query(query: types.CallbackQuery, state: FSMContext):
                    load_msg = await query.message.answer("Fetching data...")
                    async with state.proxy() as data:
                        data["search_direct_flight_qn"] = query.data
                    if data["search_direct_flight_qn"] == "yes":
                        stopover = 0
                    else:
                        stopover = None

                    if data["incl_baggage"] == "yes":
                        baggage = 1
                    else:
                        baggage = 0

                    try:
                        origin_code = location_search(data["origin"])
                        city_code = location_search(data["city"])
                        flight_response(origin_code, city_code, data["d_date"], None, baggage, stopover)
                    except KeyError or json.decoder.JSONDecodeError:
                        asyncio.create_task(delete_message(load_msg))
                        await message.answer("Invalid date. Please restart")
                        await state.finish()
                    except IndexError:
                        asyncio.create_task(delete_message(load_msg))
                        await message.answer(f"No direct flights to {data['city']}. Please restart")
                        await state.finish()
                    else:
                        asyncio.create_task(delete_message(load_msg))
                        for flight in FLIGHT_DEALS:
                            for link, text in flight.items():
                                keyboard = InlineKeyboardMarkup()
                                button = InlineKeyboardButton(link, url=link)
                                keyboard.add(button)
                                await message.answer(text, reply_markup=keyboard)
                        await message.answer("Enjoy your travels, fellow wanderer!")
                    finally:
                        FLIGHT_DEALS.clear()

                    await state.finish()

            elif query.data == "return":
                await Form.rd_date.set()
                await query.message.answer("Return flight:")
                await query.message.answer("Please input departure date in the format:\nDD/MM/YYYY")

                @dp.message_handler(state=Form.rd_date)
                async def return_d_date(message: types.Message, state: FSMContext):
                    async with state.proxy() as data:
                        data['rd_date'] = message.text
                    await Form.rr_date.set()
                    await message.answer("Please input return date in the format:\nDD/MM/YYYY")

                @dp.message_handler(state=Form.rr_date)
                async def return_r_date(message: types.Message, state: FSMContext):
                    async with state.proxy() as data:
                        data['rr_date'] = message.text
                    await Form.incl_baggage.set()
                    await message.answer("Include checked baggage?", reply_markup=keyboard_yes_no)

                @dp.callback_query_handler(text=("yes", "no"), state=Form.incl_baggage)
                async def oneway_baggage_query(query: types.CallbackQuery, state: FSMContext):
                    async with state.proxy() as data:
                        data["incl_baggage"] = query.data
                    await Form.search_direct_flight_qn.set()
                    await message.answer("Search for direct flights only?", reply_markup=keyboard_yes_no)

                @dp.callback_query_handler(text=("yes", "no"), state=Form.search_direct_flight_qn)
                async def return_query(query: types.CallbackQuery, state: FSMContext):
                    load_msg = await query.message.answer("Fetching data...")
                    async with state.proxy() as data:
                        data["search_direct_flight_qn"] = query.data
                    if data["search_direct_flight_qn"] == "yes":
                        stopover = 0
                    else:
                        stopover = None

                    if data["incl_baggage"] == "yes":
                        baggage = 1
                    else:
                        baggage = 0

                    try:
                        origin_code = location_search(data["origin"])
                        city_code = location_search(data["city"])
                        flight_response(origin_code, city_code, data["rd_date"], data["rr_date"], baggage, stopover)
                    except KeyError or json.decoder.JSONDecodeError:
                        asyncio.create_task(delete_message(load_msg))
                        await message.answer("Invalid date. Please restart")
                        await state.finish()
                    except IndexError:
                        asyncio.create_task(delete_message(load_msg))
                        await message.answer("Invalid destination city. Please restart")
                        await state.finish()
                    else:
                        asyncio.create_task(delete_message(load_msg))
                        for flight in FLIGHT_DEALS:
                            for link, text in flight.items():
                                keyboard = InlineKeyboardMarkup()
                                button = InlineKeyboardButton(link, url=link)
                                keyboard.add(button)
                                await message.answer(text, reply_markup=keyboard)
                        await message.answer("Enjoy your travels, fellow wanderer!")
                    finally:
                        FLIGHT_DEALS.clear()

                    await state.finish()

            elif query.data == "deals":
                await Form.month_year.set()
                await query.message.answer("Current deals:")
                await query.message.answer("Please input month and year of interest:\nMM/YYYY")

                @dp.message_handler(state=Form.month_year)
                async def month_year(message: types.Message, state: FSMContext):
                    async with state.proxy() as data:
                        data['month_year'] = message.text
                        data['city'] = data['city']
                    await Form.stay_length.set()
                    await message.answer(f"Number of days staying in {data['city']}")

                @dp.message_handler(state=Form.stay_length)
                async def return_d_date(message: types.Message, state: FSMContext):
                    load_msg = await query.message.answer("Fetching data...")
                    async with state.proxy() as data:
                        data['stay_length'] = int(message.text)

                    month = int(data['month_year'].split("/")[0])
                    year = int(data['month_year'].split("/")[1])

                    try:
                        cheapest_return(location_search(data['origin']), location_search(data['city']), month, year,
                                        data['stay_length'])
                    except IndexError:
                        asyncio.create_task(delete_message(load_msg))
                        await query.message.answer(f"No current deals to {data['city']}")
                        await state.finish()
                    else:
                        asyncio.create_task(delete_message(load_msg))
                        for flight in FLIGHT_DEALS:
                            for link, text in flight.items():
                                keyboard = InlineKeyboardMarkup()
                                button = InlineKeyboardButton(link, url=link)
                                keyboard.add(button)
                                await message.answer(text, reply_markup=keyboard)
                        await message.answer("Enjoy your travels, fellow wanderer!")
                    finally:
                        FLIGHT_DEALS.clear()
                    await state.finish()


@dp.callback_query_handler(state='*', text='cancel')
async def cancel_handler(query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await query.message.answer('Action cancelled')


executor.start_polling(dp)
