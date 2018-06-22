# coding: utf-8
# Импортирует поддержку UTF-8.
from __future__ import unicode_literals

# Импортируем модули для работы с JSON и логами.
import json
import logging
import os
import psycopg2
import csv
import math
from io import StringIO
from flask import Flask, request, redirect, url_for, render_template, make_response
from werkzeug.utils import secure_filename
from flask_restful import Resource, Api

app = Flask(__name__)
api = Api(app)

logging.basicConfig(level=logging.DEBUG)

# utils
def str_to_float(value):
    try:
        return float(value), True
    except ValueError:
        return value, False

# db call
POSTGRES_DB = os.getenv('POSTGRES_DB', '')
POSTGRES_USER = os.getenv('POSTGRES_USER', '')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', '')
POSTGRES_HOST = os.getenv('POSTGRES_HOST', '')
POSTGRES_PORT = os.getenv('POSTGRES_PORT', 5432)

def db_get_categories():
    categories = []
    try:
        with psycopg2.connect(dbname=POSTGRES_DB, user=POSTGRES_USER, password=POSTGRES_PASSWORD, host=POSTGRES_HOST, port=POSTGRES_PORT) as connection:
            with connection.cursor() as cursor:
                sql_string = """
                    SELECT
                        "id",
                        "url",
                        "title",
                        "last_page",
                        "created_at",
                        "updated_at"
                    FROM "category"
                    ORDER BY "priority" DESC;
                """
                cursor.execute(sql_string)
                for row in cursor.fetchall():
                    category = {
                        "id": row[0],
                        "url": row[1],
                        "title": row[2],
                        "last_page": row[3],
                        "created_at": row[4],
                        "update_at": row[5],
                    }
                    categories.append(category)
    except Exception as e:
        logging.warning(str(e))

    return categories
def export_webassyst_csv(stream, category_id, gender=''):
        with psycopg2.connect(dbname=POSTGRES_DB, user=POSTGRES_USER, password=POSTGRES_PASSWORD, host=POSTGRES_HOST, port=POSTGRES_PORT) as connection:
            with connection.cursor() as cursor:
                csv_writer = csv.writer(stream, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL, lineterminator='\n')
                # заголовок
                col_names = [
                    'Наименование',
                    'Наименование артикула',
                    'Код артикула',
                    'Валюта',
                    'Цена',
                    'Доступен для заказа',
                    'Зачеркнутая цена',
                    'Закупочная цена',
                    'В наличии',
                    'Основной артикул',
                    'В наличии @Склад в Москве',
                    'В наличии @Склад в Европе',
                    'Краткое описание',
                    'Описание',
                    'Наклейка',
                    'Статус',
                    'Тип товаров',
                    'Теги',
                    'Облагается налогом',
                    'Заголовок',
                    'META Keywords',
                    'META Description',
                    'Ссылка на витрину',
                    'Адрес видео на YouTube или Vimeo',
                    'Дополнительные параметры',
                    'Производитель',
                    'Бренд',
                    'Подходящие модели автомобилей',
                    'Вес',
                    'Страна происхождения',
                    'Пол',
                    'Цвет',
                    'Материал',
                    'Материал подошвы',
                    'Уровень',
                    'Максимальный вес пользователя',
                    'Размер',
                    'Изображения',
                    'Изображения',
                ]
                csv_writer.writerow([item.encode('utf8').decode('utf8') for item in col_names])
                # подзаголовок 1
                col_names = [
                    '<Категория>',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '<Ссылка на категорию>',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                ]
                csv_writer.writerow([item.encode('utf8').decode('utf8') for item in col_names])
                # подзаголовок 2
                col_names = [
                    '<Подкатегория>',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '<Ссылка на подкатегорию>',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                ]
                csv_writer.writerow([item.encode('utf8').decode('utf8') for item in col_names])

                cursor.execute('SELECT DISTINCT "id" FROM "product";')
                for row in cursor.fetchall():
                    sql_string = """
                        SELECT
                            "product"."back_picture",
                            "product"."colors",
                            "product"."description_html",
                            "product"."description_text",
                            "product"."front_picture",
                            "product"."manufacturer",
                            "product"."name",
                            "product"."name_url",
                            "price_cleaned",
                            "product"."url",
                            "size"."available",
                            "size"."value"
                        FROM "product"
                        INNER JOIN "size" ON "product"."id" = "size"."product_id"
                        INNER JOIN "page" ON "page"."id" = "product"."page_id"
                        WHERE "product"."id" = %s AND "page"."category_id" = %s
                        ORDER BY "value";
                    """
                    product_id = row[0]
                    parameters = (product_id, category_id,)
                    cursor.execute(sql_string, parameters)

                    product_list = []

                    counter = 1
                    all_size=[]
                    items = list(cursor.fetchall())
                    for item in items:
                        back_picture = item[0].replace('"', "'")
                        colors = item[1].replace('"', "'")
                        description_html = item[2].replace('"', "'")
                        description_text = item[3].replace('"', "'")
                        front_picture = item[4]
                        manufacturer = item[5]
                        name = item[6].replace('"', "'")
                        name_url = item[7].replace('"', "'")
                        is_float, price_cleaned = str_to_float(item[8])
                        price_cleaned = math.ceil(price_cleaned) if is_float else ''
                        url = item[9]
                        available = item[10]
                        value = item[11].replace('"', "'")

                        all_size.append(value)
                        keywords = ", ".join(name.split(' '))

                        if counter == 1:
                            item = [
                                name,
                                '{size}, {colors}'.format(size=value, colors=colors).strip(', '),
                                '',
                                'RUB',
                                price_cleaned,
                                1 if available else 0,
                                '0',
                                price_cleaned,
                                1 if available else 0,
                                '',
                                '0',
                                1 if available else 0,
                                name,
                                description_html,
                                '',
                                '1',
                                'Одежда',
                                keywords,
                                '',
                                name,
                                keywords,
                                description_text,
                                name_url,
                                '',
                                '',
                                manufacturer,
                                manufacturer,
                                '',
                                '',
                                '',
                                '',
                                '{colors}'.format(colors=colors),
                                '',
                                '',
                                '',
                                '',
                                value,
                                front_picture,
                                back_picture,
                            ]
                            product_list.append(item)
                        else:
                            item = [
                                name,
                                '{size}, {colors}'.format(size=value, colors=colors).strip(', '),
                                '',
                                'RUB',
                                price_cleaned,
                                1 if available else 0,
                                '0',
                                price_cleaned,
                                1 if available else 0,
                                '',
                                '0',
                                1 if available else 0,
                                name,
                                description_html,
                                '',
                                '1',
                                'Одежда',
                                keywords,
                                '',
                                name,
                                keywords,
                                description_text,
                                name_url,
                                '',
                                '',
                                manufacturer,
                                manufacturer,
                                '',
                                '',
                                '',
                                '',
                                '{colors}'.format(colors=colors),
                                '',
                                '',
                                '',
                                '',
                                value,
                                '',
                                '',
                            ]
                            product_list.append(item)


                        if len(items) == counter:
                            all_size = ",".join(sorted(all_size))
                            available_order = sum([item[10] for item in items])

                            main_item = [
                                name,
                                '',
                                '',
                                'RUB',
                                price_cleaned,
                                available_order,
                                '0',
                                price_cleaned,
                                available_order,
                                '',
                                '0',
                                available_order,
                                name,
                                description_html,
                                '',
                                '1',
                                'Одежда',
                                keywords,
                                '',
                                name,
                                keywords,
                                description_text,
                                name_url,
                                '',
                                '',
                                manufacturer,
                                manufacturer,
                                '',
                                '',
                                '',
                                gender,
                                '<{{{colors}}}>'.format(colors=colors).replace('<{}>', ''),
                                '',
                                '',
                                '',
                                '',
                                '<{{{all_size}}}>'.format(all_size=all_size).replace('<{}>', ''),
                                front_picture,
                                back_picture,
                            ]
                            product_list.insert(0, main_item)
                        counter+=1

                    # write end rows
                    [csv_writer.writerow(item) for item in product_list]
                    # write ending row
                    col_names = [
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                    ]
                    csv_writer.writerow([item.encode('utf8').decode('utf8') for item in col_names])

# server rendering
@app.route("/", methods=['GET'])
def index():
    categories = db_get_categories()
    print(categories)
    return render_template('index.html', categories=categories)

@app.route('/category/webassyst/<int:category_id>', methods=['GET', 'POST'])
def category_webassyst(category_id):
    if request.method == 'POST':
        gender = request.form.get('gender', '')
        stream = StringIO()
        export_webassyst_csv(stream, category_id, gender)

        output = make_response(stream.getvalue())
        output.headers["Content-Disposition"] = "attachment; filename=export_webasyst_{category_id}.csv".format(category_id=category_id)
        output.headers["Content-type"] = "text/csv"
        return output
    elif request.method == 'GET':
        return render_template('category/webasyst.html', category_id=category_id)

# api resources
class StatusResource(Resource):
    def get(self):
        return {
            'categories': [
                {
                    "id": 1
                }
            ]
        }

api.add_resource(StatusResource,
    '/category/status',
    endpoint='category_status')

# errors
def page_not_found(e):
    return render_template('error/404.html'), 404

app.register_error_handler(404, page_not_found)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)