@dp.callback_query_handler(text=("yes", "no"), state=Form.incl_baggage)
async def oneway_baggage_query(query: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data["incl_baggage"] = query.data
    await Form.search_direct_flight_qn.set()
    await message.answer("Search for direct flights only?", reply_markup=keyboard_yes_no)