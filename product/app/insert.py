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
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common import proxy
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, NoSuchElementException, TimeoutException
from selenium.webdriver.remote.remote_connection import RemoteConnection


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

        self.worker_number = 1
        self.worker_timeout = 30
        self.queue_size = 10
        self.tasks = Queue(maxsize=self.queue_size)
        self.semaphore = BoundedSemaphore(1)

        self.base_path = 'https://www.fc-moto.de/epages/fcm.sf/ru_RU/'

        self.POSTGRES_DB = os.getenv('POSTGRES_DB', '')
        self.POSTGRES_USER = os.getenv('POSTGRES_USER', '')
        self.POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', '')
        self.POSTGRES_HOST = os.getenv('POSTGRES_HOST', '')
        self.POSTGRES_PORT = os.getenv('POSTGRES_PORT', 5432)

        self.SELENIUM_HUB_URL = os.getenv('SELENIUM_HUB_URL', '')
        self.driver = None

    def get_element_by_css_selector(self, driver, selector):
        try:
            element = driver.find_element_by_css_selector(selector)
        except (NoSuchElementException, TimeoutException):
            element = None
        return element

    def get_elements_by_css_selector(self, driver, selector):
        try:
            elements = driver.find_elements_by_css_selector(selector)
        except (NoSuchElementException, TimeoutException):
            elements = None
        return elements

    def get_product_by_link(self, page_url):
        self.driver = None
        product = None

        try:
            self.options = webdriver.ChromeOptions()
            self.options.add_argument('--disable-logging')
            self.options.add_argument('--disable-infobars')
            self.options.add_argument('--disable-extensions')
            self.options.add_argument('--disable-web-security')
            self.options.add_argument('--no-sandbox')
            self.options.add_argument('--headless')
            self.options.add_argument('--window-size=600,480')
            self.options.add_argument('--silent')
            self.options.add_argument('--ignore-certificate-errors')
            self.options.add_argument('--disable-popup-blocking')
            self.options.add_argument('--incognito')
            self.options.add_argument('--lang=ru')
            self.options.add_experimental_option('prefs', {'intl.accept_languages': 'ru_RU'})

            # self.capabilities = {
            #     'browserName': 'chrome',
            #     'chromeOptions':  {
            #         'useAutomationExtension': False,
            #         'forceDevToolsScreenshot': True,
            #         'directConnect': True,
            #         'args': [
            #             # '--start-maximized',
            #             '--disable-infobars',
            #             '--disable-extensions',
            #             '--disable-web-security',
            #             # '--disable-gpu',
            #             # '--disable-dev-shm-usage',
            #             '--no-sandbox',
            #             '--headless',
            #             '--window-size=600,480',
            #             # '--remote-debugging-port=9222',
            #             # '--crash-dumps-dir=/tmp',
            #             '--silent',
            #             '--ignore-certificate-errors',
            #             '--disable-popup-blocking',
            #             '--incognito',
            #             '--lang=ru'
            #         ],
            #     },
            #     'chrome.prefs': {
            #         'intl.accept_languages': 'ru_RU'
            #     }
            # }


            executor = RemoteConnection(self.SELENIUM_HUB_URL, resolve_ip=False)
            self.driver = webdriver.Remote(command_executor=executor, desired_capabilities=self.options.to_capabilities())
            self.driver.set_page_load_timeout(3*60)
            self.driver.get(page_url)

            initial_wait = WebDriverWait(self.driver, 3*60)
            initial_wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.ContentAreaWrapper'))
            )

            # 'Наименование',
            name = self.get_element_by_css_selector(self.driver, '.ICProductVariationArea [itemprop="name"]')
            name = name.text if name else ''
            self.driver.save_screenshot('screen.png')
            # 'Производитель',
            manufacturer = self.get_element_by_css_selector(self.driver, '.ICProductVariationArea [itemprop="manufacturer"]')
            manufacturer = manufacturer.text if manufacturer else ''

            # 'Цвета',
            colors = self.get_element_by_css_selector(self.driver, '.ICVariationSelect .Headline.image .Bold.Value')
            colors = colors.text if colors else ''

            # 'Все размеры',
            all_size = self.get_elements_by_css_selector(self.driver, '.ICVariationSelect li > button')
            all_size = set([size.text for size in all_size] if all_size else [])

            # 'Неактивные размеры',
            disabled_size = self.get_elements_by_css_selector(self.driver, '.ICVariationSelect li.disabled > button')
            disabled_size = set([size.text for size in disabled_size] if disabled_size else [])

            # 'Активные размеры',
            active_size = all_size.difference(disabled_size)

            # 'Цена',
            price = self.get_element_by_css_selector(self.driver, '.PriceArea .Price')
            price = price.text if price else ''
            price_cleaned = price.replace(' ', '').replace(',', '.')

            # 'Фотография'
            front_picture = self.get_element_by_css_selector(self.driver, '#ICImageMediumLarge')
            front_picture = front_picture.get_attribute('src') if front_picture else ''

            activate_second_picture = self.get_element_by_css_selector(self.driver, '#ProductThumbBar > li:nth-child(2) > img')

            if activate_second_picture:
                activate_second_picture.click()
                time.sleep(2)
                back_picture = self.get_element_by_css_selector(self.driver, '#ICImageMediumLarge')
            back_picture = back_picture.get_attribute('src') if activate_second_picture and back_picture else ''

            # 'Описание'
            description = self.get_element_by_css_selector(self.driver, '.description[itemprop="description"]')
            description_text = description.text if description else ''
            description_html = description.get_attribute('innerHTML') if description else ''

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
                'description_html': description_html,

            }
            print(product)
        except WebDriverException as e:
            self.logger.exception('Error worker: {worker}, error: {error}'.format(worker=worker, error=str(e)))
            if self.driver:
                self.driver.quit()
            # self.get_product_by_link(page_url)
        except KeyboardInterrupt:
            if self.driver:
                self.driver.quit()
        except Exception as e:
            self.logger.exception(str(e))
        finally:
            if self.driver:
                self.driver.quit()
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
        try:
            while True:
                self.run_parallel()
        except KeyboardInterrupt:
            if self.driver:
                self.driver.quit()
        finally:
            if self.driver:
                self.driver.quit()

if __name__ == '__main__':
    unittest.main()
