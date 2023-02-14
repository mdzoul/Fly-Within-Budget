import requests
import json
import datetime
import asyncio
import csv
import aiogram.utils.markdown as md
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

TODAY = datetime.datetime.now()
SIX_MONTHS_FROM_TODAY = TODAY + relativedelta(months=6)
# TODO: GLOBAL VARIABLES WON'T WORK BECAUSE ALL USERS WILL HAVE THE SAME USERNAME AND ORIGIN
USERNAME = "User"
ORIGIN = None


# ----------------------- GEOLOCATION_SEARCH ----------------------- #
def search_geolocation(category, user_input=None):
    location_list = []
    with open("location.csv", "r") as csvfile:
        location = csv.DictReader(csvfile)
        for line in location:
            location_list.append(line)

    if category == "continent":
        countries = []
        for i in location_list:
            if i[category] == user_input:
                countries.append(i["country"])
        country_list = '\n'.join(sorted(list(dict.fromkeys(countries))))
        return f"{country_list}\n\nEnter a country"

    elif category == "country":
        cities = []
        for i in location_list:
            if i[category].lower() == user_input.lower():
                cities.append(i["cityiataCode"])
        cityiata_list = '\n'.join(sorted(list(dict.fromkeys(cities))))
        return f"{cityiata_list}\n\nEnter the 3-character city code"


# ----------------------- FLIGHT_SEARCH ----------------------- #
flight_deals = []


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
            origin_depart = datetime.datetime.strptime(
                flight_check["route"][0]["local_departure"],
                '%Y-%m-%dT%H:%M:%S.%fZ')
            destination_depart = "[Error retrieving data]"
            link = flight_check["deep_link"]

            for route in flight_check["route"]:
                if route["cityFrom"] == city_to:
                    i = flight_check["route"].index(route)
                    destination_depart = datetime.datetime.strptime(
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
                        destination_depart = datetime.datetime.strptime(
                            flight_check["route"][j]["local_departure"],
                            '%Y-%m-%dT%H:%M:%S.%fZ'
                        )
                        break

            url = rebrandly_link(link)
            flight_deals.append(f"{msg()}"
                                f"\n\nClick on the link to book now!\n{url}")

    elif return_date is None:
        def msg():
            return f"Only SGD{price}\n" \
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
            local_depart = datetime.datetime.strptime(
                flight_check["local_departure"],
                '%Y-%m-%dT%H:%M:%S.%fZ'
            )
            stopover = flight_check["route"][0]["cityTo"]
            link = flight_check["deep_link"]

            if len(flight_check["route"]) == 1:
                url = rebrandly_link(link)
                flight_deals.append(f"{msg()}\nDirect flight. No stopovers.\n\nClick on the link to book now!\n{url}")

            elif len(flight_check["route"]) == 2:
                url = rebrandly_link(link)
                flight_deals.append(
                    f"{msg()}\nFlight has 1 stopover, via {stopover}.\n\nClick on the link to book now!\n{url}")

            else:
                url = rebrandly_link(link)
                flight_deals.append(f"{msg()}\nMultiple stopovers.\n\nClick on the link to book now!\n{url}")


# ----------------------- MULTICITY_SEARCH ----------------------- #
city_list = ["SIN"]
departure_list = []


def multicity_search():
    def msg():
        return f"From {city_from}-{fly_from} " \
               f"to {city_to}-{fly_to}\n" \
               f"Departing on {local_depart}."

    city_departure_list = list(zip(city_list[1:], departure_list))

    dictionary = {}
    for i in range(len(city_list) - 1):
        dictionary[city_list[i]] = city_departure_list[i]

    li = []
    for key, value in dictionary.items():
        response = {"to": value[0],
                    "flyFrom": key,
                    "dateFrom": value[1],
                    "dateTo": value[1],
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

    price = r[0]["price"]
    url = rebrandly_link(r[0]["deep_link"])

    for i in range(len(li)):
        city_from = r[0]["route"][i]["cityFrom"]
        fly_from = r[0]["route"][i]["cityCodeFrom"]
        city_to = r[0]["route"][i]["cityTo"]
        fly_to = r[0]["route"][i]["cityCodeTo"]
        local_depart = datetime.datetime.strptime(
            r[0]["route"][i]["route"][0]["local_departure"],
            '%Y-%m-%dT%H:%M:%S.%fZ')

        flight_deals.append(f"{msg()}")

    multicity_msg = '\n\n'.join(flight_deals)

    return f"Only SGD{price}\n\n{multicity_msg}" \
           f"\n\nClick on the link to book now!\n{url} "


# ----------------------- CURRENT_DEALS ----------------------- #
def cheapest_return(fly_to):
    def msg():
        return f"Only SGD{price}\n\n" \
               f"From {city_from}-{fly_from} " \
               f"to {city_to}-{fly_to}\n" \
               f"Departing on {origin_depart}.\n\n" \
               f"From {city_from_r}-{fly_from_r} " \
               f"to {city_from}-{fly_from}\n" \
               f"Departing on {destination_depart} (local time)."

    parameters = {
        "fly_from": "SIN",
        "fly_to": fly_to,
        "date_from": TODAY.strftime("%d/%m/%Y"),
        "date_to": SIX_MONTHS_FROM_TODAY.strftime("%d/%m/%Y"),
        "return_from": SIX_MONTHS_FROM_TODAY.strftime("%d/%m/%Y"),
        "return_to": SIX_MONTHS_FROM_TODAY.strftime("%d/%m/%Y"),
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

        origin_depart = datetime.datetime.strptime(
            flight_check["route"][0]["local_departure"],
            '%Y-%m-%dT%H:%M:%S.%fZ'
        )
        destination_depart = "[Error retrieving data]"
        for route in flight_check["route"]:
            if route["cityFrom"] == city_to:
                i = flight_check["route"].index(route)
                destination_depart = datetime.datetime.strptime(
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
                    destination_depart = datetime.datetime.strptime(
                        flight_check["route"][j]["local_departure"],
                        '%Y-%m-%dT%H:%M:%S.%fZ'
                    )
                    break

        url = rebrandly_link(link)
        flight_deals.append(f"{msg()}"
                            f"\n\nClick on the link to book now!\n{url}")


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
        "fly_from": "SIN",
        "fly_to": fly_to,
        "date_from": departure_date,
        "date_to": departure_date,
        "return_from": return_date,
        "return_to": return_date,
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

        price = flight_check["price"]
        link = flight_check["deep_link"]

        city_from = flight_check["cityFrom"]
        fly_from = flight_check["flyFrom"]

        city_to = flight_check["cityTo"]
        fly_to = flight_check["flyTo"]

        origin_depart = datetime.datetime.strptime(
            flight_check["route"][0]["local_departure"],
            '%Y-%m-%dT%H:%M:%S.%fZ'
        )
        destination_depart = "[Not specified by airline]"
        for route in flight_check["route"]:
            if route["flyFrom"] == fly_to:
                i = flight_check["route"].index(route)
                destination_depart = datetime.datetime.strptime(
                    flight_check["route"][i]["local_departure"],
                    '%Y-%m-%dT%H:%M:%S.%fZ'
                )
                break

        url = rebrandly_link(link)
        if flight_type == "airline_oneway":
            flight_deals.append(f"{msg_oneway()}"
                                f"\n\nClick on the link to book now!\n{url}")
        elif flight_type == "airline_return":
            flight_deals.append(f"{msg_return()}"
                                f"\n\nClick on the link to book now!\n{url}")


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
    r_date = State()
    continent = State()
    country = State()
    user_input = State()
    multi_city = State()
    multi_date = State()
    airline_city = State()
    airline_d_date = State()
    airline_r_date = State()


btn_direct_yes = InlineKeyboardButton(text="Yes", callback_data="yes")
btn_direct_no = InlineKeyboardButton(text="No", callback_data="no")
keyboard_yes_no = InlineKeyboardMarkup().add(btn_direct_no, btn_direct_yes)


async def delete_message(message: types.Message):
    with suppress(MessageCantBeDeleted, MessageToDeleteNotFound):
        await message.delete()


@dp.message_handler(commands="start")
async def welcome(message: types.Message):
    btn_about = InlineKeyboardButton(text="About Fly Within Budget (FWB)", callback_data="about")
    keyboard_about = InlineKeyboardMarkup().add(btn_about)
    await bot.send_message(
        message.chat.id,
        md.text("Welcome to FWB (Fly Within Budget)"),
        reply_markup=keyboard_about
    )

    @dp.callback_query_handler(text="about")
    async def about(query: types.CallbackQuery):
        await query.message.answer(
            "This service is currently in its alpha phase"
            "\n\nFWB shows the cheapest flight deals as of the current search"
            "\n\nYou can search by airline, destination city/country, "
            "and one-way, return or multi-city flights"
            "\n\nThinking of going someplace new on your next travel? "
            "Try /browse and see all available international airports"
            "\n\nDeals shown are flights that originate from Singapore\nDo report any bugs experienced or "
            "features you want to see implemented @zoulaimi")

    await Form.user.set()
    await message.answer("What's your name?")

    @dp.message_handler(state=Form.user)
    async def city_search(message: types.Message, state: FSMContext):
        global USERNAME
        USERNAME = message.text.title()
        await Form.origin.set()
        await message.answer(f"And which city are you in now, {USERNAME}?")

    @dp.message_handler(state=Form.origin)
    async def city_search(message: types.Message, state: FSMContext):
        global ORIGIN
        ORIGIN = message.text.title()
        await message.answer(f"Ah, beautiful place. I have set {ORIGIN} as your city of origin\n\n"
                             f"To change your name or city of origin, you can type /profile")
        await message.answer("You can start typing a city or country to search for flights\n\n"
                             "You can also type /help to see available commands")
        await message.answer(f"Happy travels, {USERNAME}!")
        await state.finish()

# TODO: Fix the global variable issue first, then /profile will be easy to update
# @dp.message_handler(commands="profile")
# async def city_search(message: types.Message, state: FSMContext):
#     await message.answer(f"Hi {USERNAME}. Your current city of origin has been set to {ORIGIN}")
#     await message.answer(f"Would you like to change your name and city of origin?", reply_markup=keyboard_yes_no)
#
#     @dp.callback_query_handler(text=("yes", "no"))
#     async def change_name(query: types.CallbackQuery, state: FSMContext):
#         if query.data == "yes":
#             await Form.user.set()
#             await message.answer("What name shall I address you?")
#
#             @dp.message_handler(state=Form.user)
#             async def change_city(message: types.Message, state: FSMContext):
#                 global USERNAME
#                 USERNAME = message.text.title()
#                 await Form.origin.set()
#                 await message.answer(f"And which city are you in now, {USERNAME}?")
#
#             @dp.message_handler(state=Form.origin)
#             async def city_search(message: types.Message, state: FSMContext):
#                 global ORIGIN
#                 ORIGIN = message.text.title()
#                 await message.answer(f"ALright. Your name has been changed to {USERNAME} "
#                                      f"and city of origin is now {ORIGIN}")
#
#         elif query.data == "no":
#             await message.answer(f"Wanderlust is calling you, {USERNAME}\n\n"
#                                  "Time to book tickets!")

@dp.message_handler(commands="help")
async def help_(message: types.Message):
    await message.answer(
        "Available commands:\n"
        # "/profile - See and edit your profile\n"
        "/browse - Find your next travel destination\n"
        "/search - Search flights by airline or multi-city flights\n"
        "/cancel - Cancel any action")


@dp.message_handler(state='*', commands='cancel')
@dp.message_handler(Text(equals='cancel', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer('No active action to cancel')
    else:
        await state.finish()
        await message.answer('Action cancelled')


@dp.message_handler(commands="search")
async def searchflight(message: types.Message):
    btn_airline = InlineKeyboardButton(text="Preferred Airline", callback_data="airline")
    btn_multi = InlineKeyboardButton(text="Multi-city", callback_data="multi")

    keyboard_search = InlineKeyboardMarkup().add(btn_airline).add(btn_multi)

    await message.answer("Search flights by airline or multi-city flights",
                         reply_markup=keyboard_search)

    @dp.callback_query_handler(text="multi")
    async def search_multi(query: types.CallbackQuery):
        await Form.multi_city.set()
        await query.message.answer("You will be asked to input a list of destination cities and "
                                   "the corresponding departure dates for each city\n\n"
                                   "Each city and date are to be separated by using the '>' symbol with no spaces\n\n"
                                   "For example, assuming you are visiting 2 cities and returning back to Singapore:\n"
                                   "Kuala Lumpur>Jakarta>Singapore\n"
                                   "01/01/2023>09/01/2023>16/01/2023")
        await query.message.answer("Please input list of destination cities")

        @dp.message_handler(state=Form.multi_city)
        async def city_search(message: types.Message, state: FSMContext):
            async with state.proxy() as data:
                data['multi_city'] = message.text

            await Form.next()
            await message.answer("Please input departure dates")

        @dp.message_handler(state=Form.multi_date)
        async def oneway_query(message: types.Message, state: FSMContext):
            load_msg = await message.answer("Fetching data...")
            async with state.proxy() as data:
                data['multi_date'] = message.text
                city_names = data['multi_city'].split(">")
                for city in city_names:
                    try:
                        iata_code = location_search(city)
                    except IndexError:
                        asyncio.create_task(delete_message(load_msg))
                        await message.answer("Invalid destination city. Please restart")
                        await state.finish()
                    else:
                        city_list.append(iata_code)
                departure_list.extend(data['multi_date'].split(">"))
                result = multicity_search()

                asyncio.create_task(delete_message(load_msg))
                await bot.send_message(message.chat.id, md.text(f"{result}"))

                flight_deals.clear()
                del city_list[1:]
                departure_list.clear()

            await state.finish()

    # TODO: Include airline query to the last open input
    @dp.callback_query_handler(text="airline")
    async def search_airline(query: types.CallbackQuery):
        await Form.airline.set()
        await query.message.answer("Please input full airline name (e.g. Singapore Airlines) "
                                   "or airline code (e.g. SQ)")

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
        async def searchairline_flight(message: types.Message, state: FSMContext):
            async with state.proxy() as data:
                data['airline_city'] = message.text.upper()

            btn_airline_oneway = InlineKeyboardButton(text="One-way", callback_data="airline_oneway")
            btn_airline_return = InlineKeyboardButton(text="Return", callback_data="airline_return")

            keyboard_airline = InlineKeyboardMarkup().add(btn_airline_oneway, btn_airline_return)

            await message.answer("Choose one-way or return flight",
                                 reply_markup=keyboard_airline)

        @dp.callback_query_handler(text=["airline_oneway", "airline_return"], state=Form.airline_city)
        async def airline_oneway_callback(query: types.CallbackQuery, state: FSMContext):
            if query.data == "airline_oneway":
                await Form.airline_d_date.set()
                await query.message.answer("One-way flight:")
                await query.message.answer("Please input date in the format:\nDD/MM/YYYY")

                @dp.message_handler(state=Form.airline_d_date)
                async def airline_oneway_query(message: types.Message, state: FSMContext):
                    load_msg = await message.answer("Fetching data...")
                    async with state.proxy() as data:
                        data['airline_d_date'] = message.text

                        try:
                            city_code = location_search(data["airline_city"])
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
                                    city_code,
                                    data["airline_d_date"])
                            except IndexError:
                                await message.answer(
                                    f"{name_iata_dict[data['airline']].title()} does not fly to {data['airline_city'].title()}"
                                )
                            else:
                                asyncio.create_task(delete_message(load_msg))
                                for flight in flight_deals:
                                    await bot.send_message(message.chat.id, md.text(f"{flight}"))
                        finally:
                            flight_deals.clear()

                    await state.finish()

            elif query.data == "airline_return":
                await Form.airline_d_date.set()
                await query.message.answer("Return flight:")
                await query.message.answer("Please input departure date in the format:\nDD/MM/YYYY")

                @dp.message_handler(state=Form.airline_d_date)
                async def airline_r_search(message: types.Message, state: FSMContext):
                    async with state.proxy() as data:
                        data['airline_d_date'] = message.text
                    await Form.airline_r_date.set()
                    await message.answer("Please input return date in the format:\nDD/MM/YYYY")

                    @dp.message_handler(state=Form.airline_r_date)
                    async def airline_return_query(message: types.Message, state: FSMContext):
                        load_msg = await message.answer("Fetching data...")
                        async with state.proxy() as data:
                            data['airline_r_date'] = message.text

                            try:
                                city_code = location_search(data["airline_city"])
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
                                        city_code,
                                        data["airline_d_date"],
                                        data["airline_r_date"]
                                    )
                                except IndexError:
                                    await message.answer(
                                        f"{name_iata_dict[data['airline']].title()} does not fly to {data['airline_city'].title()}"
                                    )
                                else:
                                    asyncio.create_task(delete_message(load_msg))
                                    for flight in flight_deals:
                                        await bot.send_message(message.chat.id, md.text(f"{flight}"))
                            finally:
                                flight_deals.clear()

                        await state.finish()


@dp.message_handler(commands="browse")
async def continent(message: types.Message):
    await Form.continent.set()
    await message.answer("Browse and find your next travel destination\n\n"
                         "IMPORTANT:\nType the exact word for results\n"
                         "If no results appear, type /cancel to restart")
    await message.answer("Continents:\n\n"
                         "Africa 🌍\nAmericas 🌎\nAsia 🌏\nEurope 🌍\nOceania 🌏\n\n"
                         "Enter a continent")

    @dp.message_handler(state=Form.continent)
    async def country(message: types.Message, state: FSMContext):
        async with state.proxy() as data:
            data['continent'] = message.text.title()
        await Form.next()
        await message.answer(f"Countries in {data['continent']}:\n\n"
                             f"{search_geolocation('continent', data['continent'])}")

    @dp.message_handler(state=Form.country)
    async def country(message: types.Message, state: FSMContext):
        async with state.proxy() as data:
            data['country'] = message.text.title()
        await Form.next()
        await message.answer(f"Cities in {data['country']}:\n\n"
                             f"{search_geolocation('country', data['country'])}")
        await state.finish()


# TODO: Figure out a way to filter through valid and invalid inputs
# TODO: Allow users to input departing country
@dp.message_handler()
async def open_input(message: types.Message, state: FSMContext):
    await Form.city.set()
    async with state.proxy() as data:
        data['city'] = message.text.upper()

    btn_airline_oneway = InlineKeyboardButton(text="One-way", callback_data="oneway")
    btn_airline_return = InlineKeyboardButton(text="Return", callback_data="return")
    btn_deals = InlineKeyboardButton(text="Current Deals", callback_data="deals")

    keyboard_other = InlineKeyboardMarkup().add(btn_airline_oneway, btn_airline_return).add(btn_deals)

    await message.answer(f"Choose one-way or return flight, or see current deals to {data['city']}",
                         reply_markup=keyboard_other)

    @dp.callback_query_handler(text=["oneway", "return", "deals"], state=Form.city)
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
                            city_code = location_search(data["city"])
                            flight_response("SIN", city_code, data["d_date"], None, baggage, stopover)
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
                            for flight in flight_deals:
                                await bot.send_message(message.chat.id, md.text(f"{flight}"))
                        finally:
                            flight_deals.clear()

                    await state.finish()

        elif query.data == "return":
            await Form.d_date.set()
            await query.message.answer("Return flight:")
            await query.message.answer("Please input departure date in the format:\nDD/MM/YYYY")

            @dp.message_handler(state=Form.d_date)
            async def return_d_date(message: types.Message, state: FSMContext):
                async with state.proxy() as data:
                    data['d_date'] = message.text
                await Form.r_date.set()
                await message.answer("Please input return date in the format:\nDD/MM/YYYY")

            @dp.message_handler(state=Form.r_date)
            async def return_r_date(message: types.Message, state: FSMContext):
                async with state.proxy() as data:
                    data['r_date'] = message.text
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
                            city_code = location_search(data["city"])
                            flight_response("SIN", city_code, data["d_date"], data["r_date"], 1, stopover)
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
                            for flight in flight_deals:
                                await bot.send_message(message.chat.id, md.text(f"{flight}"))
                        finally:
                            flight_deals.clear()

                    await state.finish()

        elif query.data == "deals":
            load_msg = await query.message.answer("Fetching data...")
            async with state.proxy() as data:
                data['city'] = data['city']
            try:
                cheapest_return(location_search(data['city']))
            except IndexError:
                asyncio.create_task(delete_message(load_msg))
                await query.message.answer(f"No current deals to {data['city']}")
                await state.finish()
            else:
                asyncio.create_task(delete_message(load_msg))
                for flight in flight_deals:
                    await bot.send_message(query.message.chat.id, md.text(f"{flight}"))
            finally:
                flight_deals.clear()
            await state.finish()


executor.start_polling(dp)
