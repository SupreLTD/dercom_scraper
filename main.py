import csv

from playwright.sync_api import sync_playwright
from playwright_stealth.stealth import stealth_sync
from loguru import logger
from tqdm import tqdm

def handle_request(route, request):
    if request.resource_type == 'image':
        route.abort()
    else:
        route.continue_()


def parse():
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False, timeout=60000)
        context = browser.new_context(
            ignore_https_errors=True,
        )
        # context.route('**/*', handle_request)
        page = context.new_page()
        stealth_sync(page)
        page.goto('https://der-com.ru/product/elektrostantsii/vysokovoltnye-generatory/?display=price')
        logger.info('Start parsing')
        flag = True
        page_number = 1
        while flag:
            logger.info(f'loading page {page_number} ...')
            page.wait_for_load_state('domcontentloaded')
            next_load_elements = page.query_selector_all('text=Загрузить еще')
            if len(next_load_elements) < page_number:
                break

            for next_load in next_load_elements[::-1]:
                if next_load.is_visible():
                    next_load.click(timeout=30000)
                    page.wait_for_timeout(2000)
                    break
            page_number += 1

        raw_links = page.query_selector_all('a.dark_link[itemprop="url"]')
        links = []
        for i in raw_links:
            links.append(f'https://der-com.ru{i.get_attribute('href')}')

        for link in tqdm(links):
            page.goto(link)
            page.wait_for_load_state('load')
            char_button = page.wait_for_selector('a[href="#props"]')
            char_button.click()
            title = page.query_selector('h1').inner_text().replace(' в Ярославле', '')
            url = page.url
            page.wait_for_selector('img.img-responsive.inline.b-lazy.b-loaded')
            image_strip_src = page.query_selector('img.img-responsive.inline.b-lazy.b-loaded').get_attribute('src')
            image = f'https://der-com.ru{image_strip_src}'
            table = page.query_selector('table.scheme-red')
            table = table.query_selector_all('tr.prop_line ')
            table_data = []
            for row in table:
                data = row.query_selector_all('td')
                key = data[0].inner_text()
                value = data[1].inner_text()
                table_data.append(f'{key}: {value}')

            characteristics = ', '.join(table_data)

            with open('data/test.csv', 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([title, url, image, characteristics])


if __name__ == '__main__':
    parse()
