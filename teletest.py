elif query.data == "return":
await Form.d_date.set()
await query.message.answer("Return flight:")
await query.message.answer("Please input departure date in the format:\nDD/MM/YYYY")


@dp.message_handler(state=Form.d_date)
async def return_d_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['d_date'] = message.text
    await Form.next()
    await message.answer("Please input return date in the format:\nDD/MM/YYYY")


@dp.message_handler(state=Form.r_date)
async def return_r_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['r_date'] = message.text

        await Form.search_direct_flight_qn.set()
        await message.answer("Search for direct flights only?", reply_markup=yes_no)

    @dp.callback_query_handler(text=("yes", "no"), state=Form.search_direct_flight_qn)
    async def return_query(query: types.CallbackQuery, state: FSMContext):
        load_msg = await query.message.answer("Fetching data...")
        async with state.proxy() as data:
            data["search_direct_flight_qn"] = query.data

            if data["search_direct_flight_qn"] == "yes":
                stopover = 0
            else:
                stopover = None

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