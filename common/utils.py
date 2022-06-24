import fake_useragent
import logging
import requests
from bs4 import BeautifulSoup
from common.project_types import BookInfo
from common.exceptions import GetPageSourseException
from requests import Session


logger = logging.getLogger(__name__)


def parse_book_url(book_url: str) -> tuple[str, str]:
    """возвращает site_name, book_link"""
    logger.debug(f'парсим url {book_url}')
    for site_name in ['https://forums.sufficientvelocity.com', 'https://forums.spacebattles.com', 'https://storiesonline.net']:
        if book_url.startswith(site_name):
            if site_name in ['https://forums.sufficientvelocity.com', 'https://forums.spacebattles.com'] and not book_url.endswith('/threadmarks'):
                book_url += '/threadmarks'
            book_link = book_url.replace(site_name, '')
            logger.debug(f'результат парсинга:{site_name=}, {book_link=}')
            return site_name, book_link
    else:
        error_message = f'{book_url} - wrong url'
        logger.error(error_message)
        raise GetPageSourseException(error_message)


def request_get_image(image_link: str) -> requests.Response:
    user = fake_useragent.UserAgent().random
    header = {'user-agent': user}
    response = requests.get(image_link, headers=header)
    return response


def create_soup(page_source: str) -> BeautifulSoup:
    soup = BeautifulSoup(page_source, 'html5lib')
    return soup


def create_request_session() -> Session:
    logger.debug('Создаем сессию')
    user = fake_useragent.UserAgent().random
    header = {'user-agent': user,
              'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
              'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
              'DNT': '1',
              'Upgrade-Insecure-Requests': '1'
              }
    session = Session()
    session.headers.update(header)
    return session

def print_book_info(book_info: BookInfo) -> None:
    for line in book_info.__dict__:
        print(line, book_info.__getattribute__(line))


def form_acceptable_name(file_name: str, file_name_length: int) -> str:
    """Функция убирает недопустимые символы из имени файла"""
    for letter in file_name:
        if not letter.isalnum() and letter not in ' -–_$#&@!%(){}¢`~^':
            file_name = file_name.replace(letter, '~')
    if len(file_name) > file_name_length:
        file_name = file_name[:file_name_length]
    return file_name.strip()
