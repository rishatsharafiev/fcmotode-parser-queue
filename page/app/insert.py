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

        self.worker_number = 5
        self.worker_timeout = 10
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

    def get_product_links_by_page(self, page_url):
        links = []

        try:
            root = self.get_selector_root(page_url)
            links = root.cssselect('.CategoryList .InfoArea .Headline a[itemprop="url"]')
            links = ['{base_path}{link}'.format(base_path=self.base_path, link=link.get('href', '')) for link in links]
        except Exception as e:
            self.logger.exception(str(e))

        return list(set(links))

    def worker(self, n):
        try:
            while True:
                page_url, page_id, pk, last_page = self.tasks.get(timeout=self.worker_timeout)
                if last_page <= 1:
                    page = page_url
                else:
                    page = '{page_url}{page_id}'.format(page_url=page_url, page_id=page_id)
                links = self.get_product_links_by_page(page)
                with psycopg2.connect(dbname=self.POSTGRES_DB, user=self.POSTGRES_USER, password=self.POSTGRES_PASSWORD, host=self.POSTGRES_HOST, port=self.POSTGRES_PORT) as connection:
                    with connection.cursor() as cursor:
                        counter = 1
                        buffered_values = []
                        for link in links:
                            buffered_values.append("({category_id}, '{url}')".format(category_id=pk, url=link))
                            if counter % 100 == 0 or len(links) == counter:
                                values = ", ".join(buffered_values)
                                sql_string = """
                                    INSERT INTO
                                        "page" ( "category_id", "url")
                                    VALUES {values}
                                    ON CONFLICT (category_id, url) DO UPDATE
                                       SET is_done = FALSE;
                                """.format(values=values)
                                cursor.execute(sql_string)
                                connection.commit()
                            counter +=1

        except Empty:
            print('Worker #{} exited!'.format(n))

    def main(self):
        with psycopg2.connect(dbname=self.POSTGRES_DB, user=self.POSTGRES_USER, password=self.POSTGRES_PASSWORD, host=self.POSTGRES_HOST, port=self.POSTGRES_PORT) as connection:
            with connection.cursor() as cursor:
                sql_string = """
                    SELECT
                        "url",
                        "last_page",
                        "id"
                    FROM "category"
                    WHERE "is_done" = FALSE OR "updated_at" IS NULL
                    ORDER BY "priority" DESC;
                """
                cursor.execute(sql_string)
                for row in cursor.fetchall():
                    page_url = row[0]
                    last_page = row[1]
                    pk = row[2]
                    for page_id in range(1, last_page + 1):
                        self.tasks.put((page_url, page_id, pk, last_page))

    def run_parallel(self):
        gevent.joinall([
            gevent.spawn(self.main),
            *[gevent.spawn(self.worker, n) for n in range(self.worker_number)],
        ])

    def test_loop(self):
        while True:
            self.run_parallel()

if __name__ == '__main__':
    unittest.main()
