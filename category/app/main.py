# -*- coding: utf-8 -*-

import gevent.monkey
gevent.monkey.patch_all()
import gevent
from gevent.queue import Queue, Empty
from gevent.lock import BoundedSemaphore

import os
from dotenv import load_dotenv

BASE_PATH = os.path.dirname(os.path.realpath(__file__))
DOTENV_PATH = os.path.join(BASE_PATH, '.env')
load_dotenv(DOTENV_PATH)

import logging
import unittest
import re
import psycopg2
from datetime import datetime
from io import StringIO
import requests
from lxml import html

class TestSite(unittest.TestCase):
    def setUp(self):
        # initialize logget
        self.logger = logging.getLogger(__name__)
        logger_path = './'
        logger_handler = logging.FileHandler(os.path.join(logger_path, '{}.log'.format(__name__)))
        logger_formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        logger_handler.setFormatter(logger_formatter)
        self.logger.addHandler(logger_handler)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        self.worker_number = 10
        self.worker_timeout = 30
        self.queue_size = 100
        self.tasks = Queue(maxsize=self.queue_size)
        self.semaphore = BoundedSemaphore(1)

        self.base_path = 'https://www.fc-moto.de/epages/fcm.sf/ru_RU/'
        self.category_url = 'https://www.fc-moto.de/ru/Mototsikl/Mototsiklitnaya-odizhda/Mototsiklitnyrui-kurtki/Kozhanyrui-mototsiklitnyrui-kurtki'

        self.POSTGRES_DB = os.getenv('POSTGRES_DB', '')
        self.POSTGRES_USER = os.getenv('POSTGRES_USER', '')
        self.POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', '')
        self.POSTGRES_HOST = os.getenv('POSTGRES_HOST', '')
        self.POSTGRES_PORT = os.getenv('POSTGRES_PORT', 5432)

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

    def get_category_meta(self, category_url):
        last_page = 0
        page_url = ''
        categories = []

        try:
            response = requests.get(category_url)
            response.encoding = 'utf-8'
            stream = StringIO(response.text)
            root_selector = html.parse(stream).getroot()
            root_xpath = html.fromstring(response.text)

            # last_page
            page_selector = 'li > a[rel="next"]'
            pages = root_selector.cssselect(page_selector)
            texts = [page.text for page in pages]
            if len(texts) > 0:
                last_page = texts[-2]
            else:
                last_page = 1

            page_xpath = '//*[@id="CategoryProducts"]/descendant::li/a[@rel="next" or text()!="..."]'
            hrefs = [page.get('href', '') for page in pages]
            if len(hrefs):
                href = hrefs[0]
                regexp = r'^(?P<page_url>.*Page=)(?P<page_id>\d+)$'
                search = re.search(regexp, href, re.I | re.U)
                page_id = search.group('page_id')
                page_url = '{base_path}{page_url}'.format(base_path=self.base_path, page_url=search.group('page_url'))
            else:
                page_url = category_url

            categories = root_selector.cssselect('span[itemprop="itemListElement"] span[itemprop="name"]')
            categories = [category.text for category in categories if category.text != None][1:]
        except Exception as e:
            self.logger.exception(str(e))

        return (
            int(last_page),
            page_url,
            categories
        )

    def get_category_last_page(self, category_url):
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

    def get_pagination_url(self, category_url):
        page_url = None

        try:
            page_xpath = '//*[@id="CategoryProducts"]/descendant::li/a[@rel="next" or text()!="..."]'

            root = self.get_xpath_root(category_url)
            pages = [page.get('href', '') for page in root.xpath(page_xpath)]

            if len(pages):
                page = pages[0]
                regexp = r'^(?P<page_url>.*Page=)(?P<page_id>\d+)$'
                search = re.search(regexp, page, re.I | re.U)
                page_id = search.group('page_id')
                page_url = search.group('page_url')
        except Exception as e:
            self.logger.exception(str(e))

        return page_url

    def get_category_names(self, category_url):
        categories = []
        try:
            root = self.get_selector_root(category_url)
            categories = root.cssselect('span[itemprop="itemListElement"] span[itemprop="name"]')
            categories = [category.text for category in categories][1:]

        except Exception as e:
            self.logger.exception(str(e))

        return categories


    def get_product_links_by_page(self, page_url):
        links = []

        try:
            root = self.get_selector_root(page_url)
            links = root.cssselect('.InfoArea .Headline a[itemprop="url"]')
            links = ['{base_path}{link}'.format(base_path=self.base_path, link=link.get('href', '')) for link in links]
        except Exception as e:
            self.logger.exception(str(e))

        return list(set(links))

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

    def worker(self, n):
        try:
            while True:
                page_id = self.tasks.get(timeout=self.worker_timeout)
                page = '{page_url}{page_id}'.format(page_url=self.page_url, page_id=page_id)
                print(page_id, len(self.get_product_links_by_page(page)))
        except Empty:
            print('Worker #{} exited!'.format(n))

    def main(self, category_url):
        self.last_page, self.page_url, self.categories = self.get_category_meta(category_url)
        for page_id in range(1, self.last_page + 1):
            self.tasks.put(page_id)

    def run_category_queue(self):
        with psycopg2.connect(dbname=self.POSTGRES_DB, user=self.POSTGRES_USER, password=self.POSTGRES_PASSWORD, host=self.POSTGRES_HOST, port=self.POSTGRES_PORT) as connection:
            with connection.cursor() as cursor:
                sql_string = """
                    SELECT
                        "url"
                    FROM "category_queue"
                    WHERE "is_done" = FALSE
                    ORDER BY "priority" DESC;
                """
                cursor.execute(sql_string)
                for row in cursor.fetchall():
                    category_url = row[0]
                    gevent.joinall([
                        gevent.spawn(self.main, category_url),
                        *[gevent.spawn(self.worker, n) for n in range(self.worker_number)],
                    ])

    def test_loop(self):
        while(True):
            self.run_category_queue()

if __name__ == '__main__':
    unittest.main()
