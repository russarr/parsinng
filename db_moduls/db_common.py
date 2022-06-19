from pathlib import Path
from utils.exceptions import DataBaseExceptions
import logging
import sqlite3 as sq

logger = logging.getLogger('logger')


class BookDBCommon:

    @staticmethod
    def check_db_file() -> Path:
        logger.debug('проверяем наличие файла БД')
        db_path = Path('book_database/_books.db')
        if not db_path.exists():
            logger.debug('Отсутствует файл базы данных')
            raise DataBaseExceptions('Отсутсвует файл базы данных')
        return db_path

    @staticmethod
    def create_db():
        logger.debug('создаем БД')
        db_path = Path('book_database/_books.db')
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with sq.connect(db_path) as books_db:
            cur = books_db.cursor()
            cur.execute("""DROP TABLE IF EXISTS books""")
            cur.execute("""CREATE TABLE IF NOT EXISTS books (
                book_link TEXT(100) NOT NULL PRIMARY KEY,
                author_link TEXT(50) NOT NULL DEFAULT '',
                book_title TEXT(50) NOT NULL DEFAULT '',
                book_description TEXT(1500),
                book_genre TEXT(100) DEFAULT '',
                series_link TEXT(100) DEFAULT '',
                series_order INTEGER UNSIGNED NULL,
                book_size INTEGER UNSIGNED,
                votes_count INTEGER UNSIGNED,
                book_score REAL(4,2),
                sex_content TEXT(50) DEFAULT '',
                posted_date INTEGER NOT NULL DEFAULT 0,
                updated_date INTEGER NOT NULL DEFAULT 0,
                download_date INTEGER NOT NULL DEFAULT 0,
                book_status TEXT(50) DEFAULT '',
                book_monitor_status INTEGER NOT NULL DEFAULT 0,
                site_name TEXT(100) NOT NULL DEFAULT '',
                book_directory TEXT(100) NOT NULL DEFAULT '',
                FOREIGN KEY (author_link) REFERENCES authors(author_link)
                ON DELETE CASCADE
                ON UPDATE CASCADE,
                FOREIGN KEY (series_link) REFERENCES series(series_link)
                ON DELETE SET NULL
                ON UPDATE CASCADE
                )""")

            cur.execute("""DROP TABLE IF EXISTS authors""")
            cur.execute("""CREATE TABLE IF NOT EXISTS authors (
                author_link TEXT(100) NOT NULL PRIMARY KEY,
                author_name TEXT(50) NULL DEFAULT '',
                monitor_status INTEGER NOT NULL DEFAULT 0,
                author_followers INTEGER NULL DEFAULT 0
                )""")

            cur.execute("""DROP TABLE IF EXISTS chapters""")
            cur.execute("""CREATE TABLE IF NOT EXISTS chapters (
                chapter_link TEXT(100) NOT NULL PRIMARY KEY,
                chapter_name TEXT(100) NOT NULL DEFAULT '',
                chapter_file_name TEXT(50) NOT NULL DEFAULT '',
                chapter_posted_date INTEGER NULL DEFAULT 0,
                chapter_updated_date INTEGER NULL DEFAULT 0,
                book_link TEXT(100) NOT NULL,
                FOREIGN KEY (book_link) REFERENCES books(book_link)
                ON DELETE CASCADE
                ON UPDATE CASCADE
                )""")

            cur.execute("""DROP TABLE IF EXISTS series""")
            cur.execute("""CREATE TABLE IF NOT EXISTS series (
                series_link TEXT(100) NOT NULL PRIMARY KEY,
                series_name TEXT(100) NULL DEFAULT '',
                series_description TEXT(100) NULL DEFAULT '',
                author_link TEXT(50) NOT NULL DEFAULT '',
                FOREIGN KEY (author_link) REFERENCES authors(author_link)
                ON DELETE SET NULL
                ON UPDATE CASCADE
                )""")

            cur.execute("""DROP TABLE IF EXISTS book_tags""")
            cur.execute("""CREATE TABLE IF NOT EXISTS book_tags (
                tag TEXT(50) NOT NULL,
                book_link TEXT(100) NOT NULL,
                FOREIGN KEY (book_link) REFERENCES books(book_link),
                CONSTRAINT book_tag UNIQUE (tag,book_link)
                )""")
            logger.info(f'Создана БД: {db_path}')
