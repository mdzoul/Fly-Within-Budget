# Fly Within Budget ✈️

**Fly Within Budget** is a Telegram bot that helps users find and book the cheapest flights. Users interact with the bot via Telegram, search for flights by city, airline, or multi-city routes, and receive booking links powered by [Tequila by Kiwi.com](https://tequila.kiwi.com/).

## Features

- Search for flights by city, country, or continent
- Search by airline (name or IATA code)
- Multi-city flight search
- Get current flight deals
- Receive booking links directly in Telegram

## How It Works

1. Users interact with the Telegram bot using commands or text input.
2. The bot queries the Kiwi Tequila API for flight data.
3. Results are formatted and sent back to the user, including a short booking link via Rebrandly.

## Setup

> **⚠️ WARNING: THIS PROJECT IS CURRENTLY BROKEN!**
>
> This bot was working as of 2 years ago, but updates to dependencies and APIs have broken the app.  
> **You will need to update dependencies, check API changes, and refactor code to restore functionality.**
>
> **#TODO:**
> - Audit and update all dependencies in `requirements.txt` and `requirements.in`
> - Refactor code to work with the latest versions of `aiogram`, `requests`, and other libraries
> - Check for breaking changes in the Kiwi Tequila API and Rebrandly API
> - Add error handling for API changes and missing data
> - Add tests and CI/CD for future-proofing
> - Document environment variables and setup steps

### Prerequisites

- Python 3.8+
- Telegram Bot Token
- Kiwi Tequila API Key
- Rebrandly API Key
- Sheety API credentials (for airline data)

### Environment Variables

Create a `.env` file with the following (see code for exact variable names):

```
TELE_TOKEN=your-telegram-bot-token
SEARCH_HEADERS=your-kiwi-tequila-api-key
REBRANDLY_AUTH=your-rebrandly-api-key
SHEETY_AUTH=your-sheety-api-key
MULTICITY_HEADERS=your-kiwi-tequila-api-key
X_RAPIDAPI_KEY=your-rapidapi-key
```

### Installation

```sh
pip install -r requirements.txt
```

### Running the Bot

```sh
python main.py
```

## Usage

- `/start` - Start the bot and see instructions
- `/help` - List available commands
- `/browse` - Browse destinations by continent/country/city
- `/airline` - Search flights by airline
- `/multicity` - Search for multi-city flights
- `/cancel` - Cancel current action

## File Structure

- `main.py` - Main bot logic and handlers
- `airlines_update.py` - Script to update airline data
- `cleanup.py` - Script to clean up short links
- `location.csv` - Location data for search
- `requirements.txt` / `requirements.in` - Python dependencies

---

## ⚠️ MASSIVE TODO / WARNING

**This project is currently not working due to outdated dependencies and API changes.  
You must update and refactor the code before it will work again!**

---

## License

MIT License

---

*Created by Zoul Aimi.*