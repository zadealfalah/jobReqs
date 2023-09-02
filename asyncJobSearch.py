import asyncio
import re
import json
from urllib.parse import urlencode
# from arsenic import get_session
# from arsenic.browsers import Firefox
# from arsenic.services import Geckodriver
from pyppeteer import launch

from typing import List

import time


def parse_search_page(html: str):
    data = re.findall(r'window.mosaic.providerData\["mosaic-provider-jobcards"\]=(\{.+?\});', html)
    data = json.loads(data[0])
    return {
        "results": data["metaData"]["mosaicProviderJobCardsModel"]["results"],
        "meta": data["metaData"]["mosaicProviderJobCardsModel"]["tierSummaries"],
    }

async def scrape_search(client: launch(), query: str, location: str, max_results: int = 50):
    def make_page_url(offset):
        parameters = {"q": query, "l": location, "filter": 0, "start": offset}
        return "https://www.indeed.com/jobs?" + urlencode(parameters)

    print(f"scraping first page of search: {query=}, {location=}")
    response_first_page = await client.get(make_page_url(0))
    data_first_page = parse_search_page(response_first_page.text)

    results = data_first_page["results"]
    total_results = sum(category["jobCount"] for category in data_first_page["meta"])
    # there's a page limit on indeed.com of 1000 results per search
    if total_results > max_results:
        total_results = max_results
    print(f"scraping remaining {total_results - 10 / 10} pages")
    other_pages = [make_page_url(offset) for offset in range(10, total_results + 10, 10)]
    for response in await asyncio.gather(*[client.get(url=url) for url in other_pages]):
        results.extend(parse_search_page(response.text))
    return results

def parse_job_page(html):
    """parse job data from job listing page"""
    data = re.findall(r"_initialData=(\{.+?\});", html)
    data = json.loads(data[0])
    return data["jobInfoWrapperModel"]["jobInfoModel"]


async def scrape_jobs(client: launch(), job_keys: List[str]):
    """scrape job details from job page for given job keys"""
    urls = [f"https://www.indeed.com/m/basecamp/viewjob?viewtype=embedded&jk={job_key}" for job_key in job_keys]
    scraped = []
    for response in await asyncio.gather(*[client.get(url=url) for url in urls]):
        scraped.append(parse_job_page(response.text))
    return scraped

async def main():
    async with launch() as client:
        job_data = await scrape_jobs(client, ["a82cf0bd2092efa3"])
        print(job_data[0]['sanitizedJobDescription']['content'])
        print(job_data)

asyncio.run(main())