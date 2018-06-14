# -*- coding: utf-8 -*-

import os
from dotenv import load_dotenv

BASE_PATH = os.path.dirname(os.path.realpath(__file__))
DOTENV_PATH = os.path.join(BASE_PATH, '.env')
load_dotenv(DOTENV_PATH)

import logging, time
import unittest, json
import csv, math
from datetime import datetime
from io import StringIO
import requests
from lxml import html

class TestSite(unittest.TestCase):
    def setUp(self):
        # initialize logget
        self.logger = logging.getLogger(__name__)
        logger_path = '/var/log/app'
        logger_handler = logging.FileHandler(os.path.join(logger_path, '{}.log'.format(__name__)))
        logger_formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        logger_handler.setFormatter(logger_formatter)
        self.logger.addHandler(logger_handler)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        self.base_path = 'https://www.fc-moto.de/epages/fcm.sf/ru_RU/'
        self.category_url = 'https://www.fc-moto.de/ru/Mototsikl/Mototsiklitnaya-odizhda/Mototsiklitnyrui-kurtki/Kozhanyrui-mototsiklitnyrui-kurtki'
        self.write_filename = 'output.csv'

    def get_selector_root(self, url):
        response = requests.get(url)
        response.encoding = 'utf-8'
        stream = StringIO(response.text)
        root = html.parse(stream).getroot()
        return root

    def get_xpath_root(self, url):
        response = requests.get(url)
        response.encoding = 'utf-8'
        root = html.fromstring(response.text)
        return root

    def get_category_max_page(self, category_url):
        total_start = datetime.now() # 0
        end_page_id = -1

        try:
            root = self.get_selector_root(category_url)
            pages = root.cssselect('li > a[rel="next"]')
            pages = [page.text for page in pages]

            if len(pages) > 0:
                end_page_id = pages[-2]
            else:
                end_page_id = 0
        except Exception as e:
            self.logger.exception(str(e))

        return int(end_page_id)

    def get_product_links_by_page(self, page_url):
        links = []

        try:
            root = self.get_selector_root(page_url)
            links = root.cssselect('.InfoArea .Headline a[itemprop="url"]')
            links = ['{base_path}{link}'.format(base_path=self.base_path, link=link.get('href', '')) for link in links]
        except Exception as e:
            self.logger.exception(str(e))

        return list(set(links))

    def get_category_names(self, category_url):
        categories = []
        try:
            root = self.get_selector_root(category_url)
            categories = root.cssselect('span[itemprop="itemListElement"] span[itemprop="name"]')
            categories = [category.text for category in categories][1:]

        except Exception as e:
            self.logger.exception(str(e))

        return categories

    def get_pagination_links(self, category_url):
        # TODO: not optimal, run url getter with retriving page
        summary_pages = []
        try:
            page_xpath = '//*[@id="CategoryProducts"]/descendant::li/a[@rel="next" or text()!="..."]'
            next_page_xpath = '//*[@id="CategoryProducts"]/descendant::li/a[@rel="next" and text()="..."]'

            root = self.get_xpath_root(category_url)
            pages = [page.get('href', '') for page in root.xpath(page_xpath)]
            summary_pages.extend(pages)
            next_pages = root.xpath(next_page_xpath)

            while(next_pages):
                if next_pages:
                    next_page_url = '{base_path}{link}'.format(base_path=self.base_path, link=next_pages[0].get('href', ''))
                    # print(next_pages[0].get('href', ''))
                    # print(next_page_url)
                    root = self.get_xpath_root(next_page_url)
                    pages = [page.get('href', '') for page in root.xpath(page_xpath)]
                    next_pages = root.xpath(next_page_xpath)
                    summary_pages.extend(pages)

        except Exception as e:
            self.logger.exception(str(e))

        return len(list(set(summary_pages)))

    # def test_max_page(self):
    #     max_page = self.get_category_max_page(self.category_url)

    def test_pagination_links(self):
        pagination_links = self.get_pagination_links(self.category_url)
        self.logger.info(pagination_links)

if __name__ == '__main__':
    unittest.main()
