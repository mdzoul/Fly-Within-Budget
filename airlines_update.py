from dotenv import load_dotenv
import os
import requests

load_dotenv(".env")

airline_headers = {
    "X-RapidAPI-Key": os.getenv("X_RAPIDAPI_KEY"),
    "X-RapidAPI-Host": "iata-and-icao-codes.p.rapidapi.com"
}

airline_response = requests.get(
    url="https://iata-and-icao-codes.p.rapidapi.com/airlines",
    headers=airline_headers
).json()

SHEETY_AUTH = ("zoul", os.getenv("SHEETY_AUTH"))

for i in range(len(airline_response)):
    sheety_params = {
        "airline": {
            "airline": airline_response[i]["name"],
            "iataCode": airline_response[i]["iata_code"]
        }
    }

    sheety_post = requests.post(
        url="https://api.sheety.co/f1810fe8ae8de2f741a0e4c58034e85c/flightDeals/airlines",
        json=sheety_params,
        auth=SHEETY_AUTH,
    )
