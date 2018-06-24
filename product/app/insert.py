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
        logger_path =  os.getenv('PRODUCT_LOG_PATH', '')
        logger_handler = logging.FileHandler(os.path.join(logger_path, '{}.log'.format(__name__)))
        logger_formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        logger_handler.setFormatter(logger_formatter)
        self.logger.addHandler(logger_handler)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        self.worker_number = 25
        self.worker_timeout = 3
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

    def get_product_by_link(self, page_url):
        product = None

        try:
            root = self.get_selector_root(page_url)

            # 'Наименование',
            name = root.cssselect('.ICProductVariationArea [itemprop="name"]')
            if name is not None:
                name = name[0].text
            else:
                name = ''

            # 'Производитель',
            manufacturer = root.cssselect('.ICProductVariationArea [itemprop="manufacturer"]')
            if manufacturer is not None:
                manufacturer = manufacturer[0].text
            else:
                manufacturer = ''

            # 'Цвета',
            colors = root.cssselect('.ICVariationSelect .Headline.image .Bold.Value')
            if len(colors):
                colors = colors[0].text
            else:
                colors = ''

            # 'Все размеры',
            all_size = root.cssselect('.ICVariationSelect li > button')
            all_size = set([size.text for size in all_size] if all_size else [])

            # 'Неактивные размеры',
            disabled_size = root.cssselect('.ICVariationSelect li.disabled > button')
            disabled_size = set([size.text for size in disabled_size] if disabled_size else [])

            # 'Активные размеры',
            active_size = all_size.difference(disabled_size)

            # 'Цена',
            price = root.cssselect('.PriceArea .Price')
            if len(price):
                price = price[0].text_content()
            else:
                price = ''
            price_cleaned = price.replace('руб.', '').replace(' ', '').replace(',', '.').strip()
            # 'Фотография'
            front_picture = root.cssselect('#ICImageMediumLarge')
            if front_picture is not None:
                front_picture = 'https://www.fc-moto.de{}'.format(front_picture[0].get('src'))
            else:
                front_picture = ''

            back_picture = ''

            # 'Описание'
            description = root.cssselect('.description[itemprop="description"]')
            if description is not None:
                description_text = description[0].text_content()
            else:
                description_text = ''

            if description is not None:
                description_html = html.tostring(description[0])
            else:
                description_html = ''

            product = {
                'name': name,
                'manufacturer': manufacturer,
                'colors': colors,
                'all_size': all_size,
                'disabled_size': disabled_size,
                'active_size': active_size,
                'price': price,
                'price_cleaned': price_cleaned,
                'front_picture': front_picture,
                'back_picture': back_picture,
                'description_text': description_text,
                'description_html': description_html.decode("utf-8"),

            }
        except Exception as e:
            self.logger.exception(str(e))

        return product

    def worker(self, n):
        try:
            while True:
                url, category_id, pk = self.tasks.get(timeout=self.worker_timeout)
                with psycopg2.connect(dbname=self.POSTGRES_DB, user=self.POSTGRES_USER, password=self.POSTGRES_PASSWORD, host=self.POSTGRES_HOST, port=self.POSTGRES_PORT) as connection:
                    with connection.cursor() as cursor:
                        sql_string = """
                            SELECT
                                "id",
                                "url"
                            FROM "product"
                            WHERE "is_done" = TRUE;
                        """
                        cursor.execute(sql_string)

                        if (pk, url,) not in cursor.fetchall():
                            product = self.get_product_by_link(url)
                            if product:
                                sql_string = """
                                    INSERT INTO "product"
                                        (
                                            "page_id",
                                            "url",
                                            "name_url",
                                            "back_picture",
                                            "colors",
                                            "description_html",
                                            "description_text",
                                            "front_picture",
                                            "manufacturer",
                                            "name",
                                            "price_cleaned",
                                            "is_done"
                                        )
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                                    ON CONFLICT (url, page_id) DO UPDATE
                                        SET
                                            "updated_at"=NOW(),
                                            "is_done" = TRUE,
                                            "name_url" = %s,
                                            "back_picture" = %s,
                                            "colors" = %s,
                                            "description_html" = %s,
                                            "description_text" = %s,
                                            "front_picture" = %s,
                                            "manufacturer" = %s,
                                            "name" = %s,
                                            "price_cleaned" = %s
                                    RETURNING id;
                                """
                                page_id = pk,
                                name_url = url.split('/')[-1][:2044],
                                url = url[:2044],
                                back_picture = product['back_picture'][:2044],
                                colors = product['colors'][:2044],
                                description_html = product['description_html'][:5000],
                                description_text = product['description_text'][:5000],
                                front_picture = product['front_picture'][:2044],
                                manufacturer = product['manufacturer'][:2044],
                                name = product['name'][:2044],
                                price_cleaned = product['price_cleaned'][:2044],

                                parameters = (
                                    page_id,
                                    url,
                                    name_url,
                                    back_picture,
                                    colors,
                                    description_html,
                                    description_text,
                                    front_picture,
                                    manufacturer,
                                    name,
                                    price_cleaned,
                                    name_url,
                                    back_picture,
                                    colors,
                                    description_html,
                                    description_text,
                                    front_picture,
                                    manufacturer,
                                    name,
                                    price_cleaned,
                                )
                                cursor.execute(sql_string, parameters)
                                product_id = cursor.fetchone()[0]
                                connection.commit()

                                if product_id:
                                    sql_string = """
                                        UPDATE "page"
                                        SET "is_done" = TRUE
                                        WHERE "id" = %s;
                                    """
                                    parameters = (pk, )
                                    result = cursor.execute(sql_string, parameters)

                                    all_size = product['all_size']
                                    active_size = product['active_size']
                                    for size in product['all_size']:
                                        if size in active_size:
                                            available = True
                                        else:
                                            available = False
                                        sql_string = """
                                            INSERT INTO "size" ("product_id", "available", "value")
                                                VALUES (%s, %s, %s)
                                            ON CONFLICT (value, product_id) DO UPDATE
                                                SET
                                                    "product_id" = %s,
                                                    "available" = %s,
                                                    "value" = %s;
                                        """
                                        parameters = ( product_id, available, size, product_id, available, size,)
                                        result = cursor.execute(sql_string, parameters)
                                    connection.commit()

        except Empty:
            print('Worker #{} exited!'.format(n))

    def main(self):
        # TODO: join url with page_id in stream, split to parallel routines
        with psycopg2.connect(dbname=self.POSTGRES_DB, user=self.POSTGRES_USER, password=self.POSTGRES_PASSWORD, host=self.POSTGRES_HOST, port=self.POSTGRES_PORT) as connection:
            with connection.cursor() as cursor:
                sql_string = """
                    SELECT
                        "url",
                        "category_id",
                        "id"
                    FROM "page"
                    WHERE "is_done" = FALSE
                    ORDER BY RANDOM()
                    LIMIT {limit};
                """.format(limit=self.worker_number*10)
                cursor.execute(sql_string)
                for row in cursor.fetchall():
                    url = row[0]
                    category_id = row[1]
                    pk = row[2]
                    self.tasks.put((url, category_id, pk,))

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
