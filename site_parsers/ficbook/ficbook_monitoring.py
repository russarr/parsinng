import logging.config
import re
import time

from bs4 import BeautifulSoup

from common.exceptions import ParsingException
from common.request_authorization import create_auth_session
from common.utils import create_soup
from settings.settings import LOGGING_CONFIG
from site_parsers.ficbook.ficbook_book import FicbookBook
from site_parsers.ficbook.ficbook_book import _extract_book_link_ficbook

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)


def _get_updated_books_list(soup: BeautifulSoup) -> list[str | None]:
    logger.debug('Извлекаем ссылки на обновленные книги')
    links_raw = soup.find_all('a', href=re.compile(r'(/readfic/\d+)'))
    upd_books_list = []
    if links_raw:
        for link in links_raw:
            link_raw = link.get('href')
            error_message = 'Ошибка получения ссылки на обновленную книгу'
            if isinstance(link_raw, str):
                book_link = _extract_book_link_ficbook(link_raw)
                upd_books_list.append(book_link)
            else:
                logger.error(error_message)
                raise ParsingException(error_message)
    return upd_books_list


def check_ficbook_updates() -> None:
    logger.debug('Проверяем обновления ficbook')
    session = create_auth_session(site_alias='ficbook')
    update_url = 'https://ficbook.net/notifications?type=19'
    response = session.get(update_url)
    if response.status_code == 200:
        soup = create_soup(response.text)
        updated_books_list = _get_updated_books_list(soup)
        if updated_books_list:
            for book_link in updated_books_list:
                book = FicbookBook(book_link)
                session = book.downoload_book(session)
                time.sleep(2)
            logger.debug('Попытка пометить события прочитанными')
            session.post('https://ficbook.net/user_notifications/delete_all', data={"type": "19"})
    session.close()
