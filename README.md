Excel → GeoJSON (FastAPI)

Веб-приложение для загрузки Excel, проверки структуры столбцов, автонормализации данных и выдачи результата в формате GeoJSON.

Что делает

Принимает .xlsx.

Склеивает многострочную шапку (3 строки) и сравнивает с эталоном (REFERENCE_HEADERS) по порядку.

Удаляет столбец №.

Переименовывает столбцы в целевые (TARGET_HEADERS), приводит к нижнему регистру.

Приводит типы по правилам (COLUMN_TYPES), нормализует даты и числа.

Парсит coordinates в [lon, lat] с простыми проверками.

Генерирует и отдаёт *.geojson с CRS OGC:CRS84.

Технологии

FastAPI, Uvicorn, Jinja2, pandas, openpyxl, Docker.

Структура
app/
  __init__.py
  main.py           # создание FastAPI, шаблоны, статика
  routes.py         # маршруты: /, /upload, /download/{filename}, /health
  excel_tools.py    # чтение шапки, сравнение с эталоном
  geojson_tools.py  # приведение типов, парсинг координат, сборка GeoJSON
  reference_headers.py  # список эталонных названий
  target_headers.py     # список целевых названий
  templates/
    base.html
    index.html
    result.html
data/               # временные файлы .xlsx/.geojson
requirements.txt
Dockerfile
.dockerignore

Маршруты

GET / — форма загрузки.

POST /upload — приём Excel, валидация, конвертация, ссылка на скачивание.

GET /download/{filename} — отдача готового GeoJSON.

GET /health — проверка живости.

Запуск локально
python -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
# http://127.0.0.1:8000

Запуск в Docker

Сборка:

docker build --pull -t geojson-converter:1.0 .


Запуск (локальная сеть):

docker run -d --name geojson --restart unless-stopped \
  -p 8001:8000 geojson-converter:1.0
# http://<IP_сервера>:8001


Запуск только для localhost сервера:

docker run -d --name geojson --restart unless-stopped \
  -p 127.0.0.1:8001:8000 geojson-converter:1.0

Ожидаемый формат Excel

Первая страница (sheet_name=0).

Три строки шапки, которые склеиваются в один заголовок на колонку.

Полное совпадение с REFERENCE_HEADERS по порядку. Затем удаляется № и присваиваются TARGET_HEADERS.
