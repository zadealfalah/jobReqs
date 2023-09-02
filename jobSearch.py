import asyncio
import re
import json
from urllib.parse import urlencode
# from arsenic import get_session
# from arsenic.browsers import Firefox
# from arsenic.services import Geckodriver
from pyppeteer import launch

import time


def parse_search_page(html: str):
    data = re.findall(r'window.mosaic.providerData\["mosaic-provider-jobcards"\]=(\{.+?\});', html)
    data = json.loads(data[0])
    return {
        "results": data["metaData"]["mosaicProviderJobCardsModel"]["results"],
        "meta": data["metaData"]["mosaicProviderJobCardsModel"]["tierSummaries"],
    }
    
async def scrape_search(client, query:str, location:str, max_results:int=50):
    def make_page_url(offset):
        params = {"q":query, "l":location, "filter":0, "start":offset}
        return "https://www.indeed.com/jobs?" + urlencode(params) + ".html"
    print(f"scraping first page of search: {query=}, {location=}")
    print(f"URL: {make_page_url(0)}")
    first_response_page = await client.goto(make_page_url(0))
    # time.sleep(10)
    first_page_data = parse_search_page(first_response_page.content())

    results = first_page_data["results"]
    total_results = sum(category["jobCount"] for category in first_page_data["meta"])
    # there's a page limit on indeed.com of 1000 results per search
    if total_results > max_results:
        total_results = max_results
    print(f"scraping remaining {total_results - 10 / 10} pages")
    other_pages = [make_page_url(offset) for offset in range(10, total_results + 10, 10)]
    for response in await asyncio.gather(*[client.get(url=url) for url in other_pages]):
        results.extend(parse_search_page(response.text))
    return results

async def main():
    browser = await launch()
    page = await browser.newPage()
    
    async with page as client:
        search_data = await scrape_search(client, query='python', location='remote')
        print(json.dumps(search_data, indent=2))
        
asyncio.run(main())