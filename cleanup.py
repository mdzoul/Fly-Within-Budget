from dotenv import load_dotenv
import os
import os
import requests
import json
from urllib.parse import urlencode
from ratelimit import limits
from retry import retry

load_dotenv(".env")

# CONFIGURATION
apiKey = os.getenv("REBRANDLY_AUTH")
domainFullname = "flywithinbudget.link"

# CONSTRAINTS
MAX_PAGE_SIZE = 25

requestHeaders = {
    "Content-type": "application/json",
    "apikey": apiKey,
}


@retry()
@limits(calls=10, period=1)
def getLinksAfter(lastLink):
    querystring = urlencode({
        "limit": MAX_PAGE_SIZE,
        "last": lastLink["id"] if lastLink else "",
        "orderBy": "createdAt",
        "orderDir": "desc",
        "domain.fullName": domainFullname
    })
    endpoint = f"https://api.rebrandly.com/v1/links?{querystring}"
    r = requests.get(endpoint, headers=requestHeaders)
    if (r.status_code != requests.codes.ok):
        raise Exception(f"Could not retrieve links, response code was {r.status_code}")
    links = r.json()
    return links


@retry()
@limits(calls=1, period=1)
def deleteLinksByID(ids):
    deletedLinks = []
    r = requests.delete(f"https://api.rebrandly.com/v1/links",
                        data=json.dumps({
                            "links": ids
                        }),
                        headers=requestHeaders)
    if (r.status_code == requests.codes.ok):
        deletedLinks = r.json()["links"]
    else:
        print(r.json())
        raise Exception(f"Could not delete links with id {json.dumps(id)}, response code was {r.status_code}")
    return deletedLinks


def cleanup():
    processedAll = False
    links = None

    def lastOne():
        return links[-1] if links else None

    def delete(links):
        deletedLinks = deleteLinksByID([link["id"] for link in links])
        if (deletedLinks):
            print(f"Deleted {len(deletedLinks)} links (last deleted: {deletedLinks[-1]})")

    while (not processedAll):
        links = getLinksAfter(lastOne())
        if any(links):
            delete(links)
        else:
            processedAll = True


cleanup()
