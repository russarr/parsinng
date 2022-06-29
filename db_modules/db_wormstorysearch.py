import logging
import sqlite3 as sq
from common.exceptions import DataBaseExceptions
from typing import Iterable

logger = logging.getLogger(__name__)


def write_wormstorysearch_in_db(cur: sq.Cursor, books_data: Iterable[tuple[str, str]]) -> None:
    try:
        cur.executemany("""INSERT OR REPLACE INTO wormstorysearch (book_url, book_name) VALUES (?,?)""", books_data)
    except sq.Error:
        error_message = 'Ошибка записи данных в таблицу wormstorysearch'
        logger.exception(error_message)
        raise DataBaseExceptions(error_message)


def read_wormstorysearch_in_db(cur: sq.Cursor) -> list[tuple[str, str]]:
    try:
        cur.execute("""SELECT book_url, book_name FROM wormstorysearch""")
        books_data = cur.fetchall()
        return books_data
    except sq.Error:
        error_message = 'Ошибка записи данных в таблицу wormstorysearch'
        logger.exception(error_message)
        raise DataBaseExceptions(error_message)
