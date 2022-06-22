from pathlib import Path
from common.exceptions import DataBaseExceptions  # type: ignore
import logging
from datetime import datetime
import sqlite3 as sq
from common.common import BookInfo, ChapterInfo  # type: ignore
from common.utils import raise_exception  # type: ignore

logger = logging.getLogger(__name__)


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


class BookDBWrite(BookDBCommon, BookInfo):
    def add_book_to_db(self) -> None:
        logger.debug('Добавляем книгу в БД')
        db_path = self.check_db_file()
        data_to_add = self._form_data_add_db()
        self._write_data_to_add(data_to_add, db_path)

    def update_book_in_db(self) -> None:
        logger.debug('Обновляем книгу в БД')
        db_path = self.check_db_file()
        data_to_upd = self._form_data_to_upd()
        self._write_data_to_upd(data_to_upd, db_path)

    def _form_data_add_db(self) -> tuple[tuple, tuple[str, str], tuple, tuple]:
        data_book = self._form_data_book_table_to_add()
        data_author = self._form_data_author_table_add_db()
        data_chapters = self._form_data_chapters_table_to_add()
        data_tags = self._form_data_tags_table_add_db()
        return data_book, data_author, data_chapters, data_tags

    def _form_data_book_table_to_add(self) -> tuple[str, str, str, str, str, str, int, int, int, float, str, int, int, int, str, int, str, str]:
        self.book_download_date = self._get_download_date()
        data_book_table_to_add = (
            self.book_link,
            self.author_link,
            self.book_title,
            self.book_description,
            self.book_genre,
            self.book_series,
            self.book_series_order_position,
            self.book_size,
            self.book_votes_count,
            self.book_score,
            self.book_sex_content,
            self.book_posted_date,
            self.book_updated_date,
            self.book_download_date,
            self.book_status,
            self.book_monitoring_status,
            self.site_name,
            str(self.book_directory)
        )
        return data_book_table_to_add

    @staticmethod
    def _get_download_date() -> int:
        return int(datetime.now().timestamp())

    def _form_data_author_table_add_db(self) -> tuple[str, str]:
        data_author = (self.author_link, self.author_name)
        return data_author

    def _form_data_chapters_table_to_add(self) -> tuple[tuple[str, str, str, int, int, str], ...]:
        data_chapters = tuple((chapter.chapter_link,
                               chapter.chapter_name,
                               chapter.chapter_file_name,
                               chapter.chapter_posted_date,
                               chapter.chapter_updated_date,
                               chapter.book_link) for chapter in self.chapters_info_list)
        return data_chapters

    def _form_data_tags_table_add_db(self) -> tuple[tuple[str, str], ...]:
        data_tags = tuple((tag, self.book_link) for tag in self.book_tags)
        return data_tags

    def _write_data_to_add(self, data_to_add:
                                    tuple[tuple[str, ...],
                                          tuple[str, str],
                                          tuple[tuple[str, str, str, int, int, str], ...],
                                          tuple[tuple[str, str], ...]], db_path: Path) -> None:
                                        book_table, authors_table, chapters_table, tags_table = data_to_add
                                        with sq.connect(db_path) as books_db:
                                            cur = books_db.cursor()
                                            self._write_data_book_table_to_add(cur, book_table)
                                            self._write_data_author_table_to_add(cur, authors_table)
                                            self._write_data_chapters_table_to_add(cur, chapters_table)
                                            self._write_data_tags_table_to_add(cur, tags_table)

    @staticmethod
    def _write_data_book_table_to_add(cur: sq.Cursor, data_book) -> None:
        try:
            cur.execute("""INSERT OR REPLACE INTO books (
                book_link,
                author_link,
                book_title,
                book_description,
                book_genre,
                series_link,
                series_order,
                book_size,
                votes_count,
                book_score,
                sex_content,
                posted_date,
                updated_date,
                download_date,
                book_status,
                book_monitor_status,
                site_name,
                book_directory) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", data_book)
        except sq.Error as e:
            raise_exception(DataBaseExceptions, f'Проблемы с записью в таблицу books: {data_book}. {e}')

    @staticmethod
    def _write_data_author_table_to_add(cur: sq.Cursor, data_author: tuple[str, str]) -> None:
        try:
            cur.execute("""INSERT OR REPLACE INTO authors (
                author_link,
                author_name) VALUES (?,?)""", data_author)
        except sq.Error as e:
            raise_exception(DataBaseExceptions, f'Проблемы с записью в таблицу authors {data_author}. {e}')

    @staticmethod
    def _write_data_chapters_table_to_add(cur: sq.Cursor, data_chapters: tuple[tuple[str, str, str, int, int, str], ...]) -> None:
        try:
            cur.executemany("""INSERT OR REPLACE INTO chapters (
                chapter_link,
                chapter_name,
                chapter_file_name,
                chapter_posted_date,
                chapter_updated_date,
                book_link
                ) VALUES(?,?,?,?,?,?)""", data_chapters)
        except sq.Error as e:
            raise_exception(DataBaseExceptions, f'Проблемы с записью в таблицу chapters {data_chapters}. {e}')

    @staticmethod
    def _write_data_tags_table_to_add(cur: sq.Cursor, data_tags: tuple[tuple[str, str], ...]) -> None:
        try:
            cur.executemany("""INSERT OR REPLACE INTO book_tags (
                tag,
                book_link
                ) VALUES(?,?)""", data_tags)
        except sq.Error as e:
            raise_exception(DataBaseExceptions, f'Проблемы с записью в таблицу tags {data_tags} {e}')

    def _form_data_to_upd(self) -> tuple[tuple, tuple, tuple]:
        data_book = self._form_data_book_table_to_upd()
        data_chapters = self._form_data_chapters_table_to_add()
        data_tags = self._form_data_tags_table_add_db()
        return data_book, data_chapters, data_tags

    def _form_data_book_table_to_upd(self) -> tuple[str, str, str, int, int, int, float, str, int, int, str, str]:
        self.book_download_date = self._get_download_date()
        data_book = (
            self.book_description,
            self.book_genre,
            self.book_series,
            self.book_series_order_position,
            self.book_size,
            self.book_votes_count,
            self.book_score,
            self.book_sex_content,
            self.book_updated_date,
            self.book_download_date,
            self.book_status,
            self.book_link
        )
        return data_book

    def _write_data_to_upd(self, data_to_upd: tuple[tuple, tuple, tuple], db_path: Path):
        book_table, chapters_table, tags_table = data_to_upd
        with sq.connect(db_path) as books_db:
            cur = books_db.cursor()
            # делаем UPDATE только таблицы books, в остальных можно просто перезаписать данные
            self._write_data_book_table_to_upd(cur, book_table)
            self._write_data_chapters_table_to_add(cur, chapters_table)
            self._write_data_tags_table_to_add(cur, tags_table)

    @staticmethod
    def _write_data_book_table_to_upd(cur: sq.Cursor, data_books) -> None:
        try:
            cur.execute("""UPDATE books
             SET book_description=?,
                book_genre=?,
                series_link=?,
                series_order=?,
                book_size=?,
                votes_count=?,
                book_score=?,
                sex_content=?,
                updated_date=?,
                download_date=?,
                book_status=?
                WHERE book_link=? """, data_books)
        except sq.Error as e:
            raise_exception(DataBaseExceptions, f'Проблемы обновления таблицы boosk{data_books}. {e}')


class BookDBRead(BookDBCommon, BookInfo):
    def read_book_info_from_db(self) -> None:
        db_path = self.check_db_file()
        with sq.connect(db_path) as books_db:
            cur = books_db.cursor()
            self._fetch_book_details(cur, self.book_link)
            self._fetch_book_tags(cur, self.book_link)
            self._fetch_chapters_info_list(cur, self.book_link)

    def _fetch_book_details(self, cur: sq.Cursor, book_link: str) -> None:
        try:
            cur.execute("""SELECT books.*, authors.author_name
             FROM books
             JOIN authors ON books.author_link = authors.author_link
             WHERE book_link = ? """, (book_link,))
            book_details = cur.fetchone()
        except sq.Error:
            error_message = f'Ошбика получения информации из БД по ссылке:{book_link}'
            logger.error(error_message)
            raise DataBaseExceptions(error_message)

        boods_column_list = ('book_link', 'author_link', 'book_title', 'book_description', 'book_genre', 'book_series',
                             'book_series_order_position', 'book_size', 'book_votes_count', 'book_score', 'book_sex_content',
                             'book_posted_date', 'book_updated_date', 'book_download_date', 'book_status', 'book_monitoring_status',
                             'site_name', 'book_directory', 'author_name')
        if len(book_details) == len(boods_column_list):
            book_data = zip(boods_column_list, book_details, strict=True)
            for item in book_data:
                self.__setattr__(item[0], item[1])

    def _fetch_book_tags(self, cur: sq.Cursor, book_link: str) -> None:
        try:
            cur.execute("""SELECT tag FROM book_tags WHERE book_link = ?""", (book_link,))
        except sq.Error:
            error_message = f'Ошбика получения информации о тэгах из БД по ссылке:{book_link}'
            logger.error(error_message)
            raise DataBaseExceptions(error_message)

        book_tags = cur.fetchall()
        if book_tags:
            self.book_tags = tuple(tag[0] for tag in book_tags)

    def _fetch_chapters_info_list(self, cur: sq.Cursor, book_link: str) -> None:
        try:
            cur.execute("""SELECT chapter_name, chapter_file_name, chapter_link, chapter_posted_date, chapter_updated_date, book_link FROM chapters WHERE book_link = ?""", (book_link,))
        except sq.Error:
            error_message = f'Ошбика получения информации о глвах из БД по ссылке:{book_link}'
            logger.error(error_message)
            raise DataBaseExceptions(error_message)
        chapters_info_list = cur.fetchall()

        if chapters_info_list:
            for chapter in chapters_info_list:
                chapter_info = ChapterInfo(chapter_name=chapter[0], chapter_file_name=chapter[1], chapter_link=chapter[2],
                                           chapter_posted_date=chapter[3], chapter_updated_date=chapter[4], book_link=chapter[5])
                self.chapters_info_list.append(chapter_info)
        else:
            error_message = f'Ошибка загрузки информации по главам книги:{book_link}'
            logger.error(error_message)
            raise DataBaseExceptions(error_message)


class BookDB(BookDBWrite, BookDBRead):
    pass
