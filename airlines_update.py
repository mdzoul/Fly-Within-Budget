import requests

airline_headers = {
    "X-RapidAPI-Key": "78cff0cd39mshe26bf15ae20c3cbp149cf8jsn5b10c6c19240",
    "X-RapidAPI-Host": "iata-and-icao-codes.p.rapidapi.com"
}

airline_response = requests.get(
    url="https://iata-and-icao-codes.p.rapidapi.com/airlines",
    headers=airline_headers
).json()

SHEETY_AUTH = ("zoul", "#72rv+vaesj7t#")

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
