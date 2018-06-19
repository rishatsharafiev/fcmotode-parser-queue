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
        logger_path = '/var/log'
        logger_handler = logging.FileHandler(os.path.join(logger_path, '{}.log'.format(__name__)))
        logger_formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        logger_handler.setFormatter(logger_formatter)
        self.logger.addHandler(logger_handler)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        self.worker_number = 5
        self.worker_timeout = 15
        self.queue_size = 100
        self.tasks = Queue(maxsize=self.queue_size)
        self.semaphore = BoundedSemaphore(1)

        self.base_path = 'https://www.fc-moto.de/epages/fcm.sf/ru_RU/'

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

    def worker(self, n):
        try:
            while True:
                category_url, pk = self.tasks.get(timeout=self.worker_timeout)
                last_page, page_url, categories = self.get_category_meta(category_url)
                title = ",".join([category for category in categories if category != None])
                with psycopg2.connect(dbname=self.POSTGRES_DB, user=self.POSTGRES_USER, password=self.POSTGRES_PASSWORD, host=self.POSTGRES_HOST, port=self.POSTGRES_PORT) as connection:
                    with connection.cursor() as cursor:
                        if last_page and page_url and categories:
                            sql_string = """
                                UPDATE "category"
                                SET
                                    "updated_at" = NOW(),
                                    "title" = %s,
                                    "url" = %s,
                                    "last_page" = %s
                                WHERE
                                    "id" = %s
                                RETURNING id;
                            """
                            parameters = (title, page_url, last_page, pk,)
                            cursor.execute(sql_string, parameters)

        except Empty:
            print('Worker #{} exited!'.format(n))

    def main(self):
        with psycopg2.connect(dbname=self.POSTGRES_DB, user=self.POSTGRES_USER, password=self.POSTGRES_PASSWORD, host=self.POSTGRES_HOST, port=self.POSTGRES_PORT) as connection:
            with connection.cursor() as cursor:
                sql_string = """
                    SELECT
                        "url",
                        "id"
                    FROM "category"
                    WHERE "is_done" = FALSE OR "updated_at" IS NULL
                    ORDER BY "priority" DESC;
                """
                cursor.execute(sql_string)
                for row in cursor.fetchall():
                    category_url = row[0]
                    pk = row[1]
                    self.tasks.put((category_url, pk))

    def run_parallel(self):
        gevent.joinall([
            gevent.spawn(self.main),
            *[gevent.spawn(self.worker, n) for n in range(self.worker_number)],
        ])

    def test_loop(self):
        while(True):
            self.run_parallel()

if __name__ == '__main__':
    unittest.main()
