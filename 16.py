from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pypika import Query, Table, Parameter

import sqlite3

# Создаем экземпляр драйвера Selenium
driver = webdriver.Chrome()

# Открываем страницу
driver.get("https://en.wikipedia.org/wiki/List_of_highest-grossing_Japanese_films")

# Ждем загрузки таблицы
wait = WebDriverWait(driver, 10)
table = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.wikitable")))

# Извлекаем данные из таблицы
data = []
for row in table.find_elements(By.TAG_NAME, "tr")[1:]:
    cells = row.find_elements(By.TAG_NAME, "td")
    if len(cells) == 5:
        title = cells[0].text.strip()
        director = cells[1].text.strip()
        year = int(cells[2].text.strip())
        try:
            gross = float(cells[3].text.strip().replace(",", ""))
        except ValueError:
            continue  # Пропускаем строку, если значение в ячейке не является числом
        rank = int(cells[4].text.strip())
        data.append((title, director, year, gross, rank))

# Закрываем браузер
driver.quit()


# Создаем подключение к базе данных SQLite
conn = sqlite3.connect("japanese_films.db")
c = conn.cursor()

# Создаем таблицы
c.execute("""CREATE TABLE IF NOT EXISTS films (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             title TEXT,
             director TEXT,
             year INTEGER,
             gross REAL,
             rank INTEGER
         )""")

c.execute("""CREATE TABLE IF NOT EXISTS directors (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             name TEXT
         )""")


# Заполняем таблицу films
for title, director, year, gross, rank in data:
    c.execute("INSERT INTO films (title, director, year, gross, rank) VALUES (:title, :director, :year, :gross, :rank)",
              {"title": title, "director": director, "year": year, "gross": gross, "rank": rank})

# Заполняем таблицу directors
directors = set(row[1] for row in data)
for director in directors:
    c.execute("INSERT INTO directors (name) VALUES (:name)", {"name": director})

conn.commit()
conn.close()


# Создаем объекты таблиц
films = Table("films")
directors = Table("directors")

# Два запроса с JOIN
query1 = (
    Query.from_(films)
    .join(directors, how=films.director == directors.name)
    .select(films.title, directors.name)
)
query2 = (
    Query.from_(films)
    .join(directors, how=films.director == directors.name)
    .where(films.year > 2010)
    .select(films.title, films.year, directors.name)
)

# Три запроса с расчетом статистики/группировкой/агрегирующими функциями
query3 = Query.from_(films).select(films.year, Query.avg(films.gross).as_("avg_gross"))
query4 = Query.from_(films).groupby(films.director).select(films.director, Query.count(films.id).as_("num_films"))
query5 = Query.from_(films).where(films.year >= 2015).select(films.year, Query.sum(films.gross).as_("total_gross"))