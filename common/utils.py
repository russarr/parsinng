import logging
import os
import re
from typing import Callable, Literal

import dotenv
import fake_useragent
import requests
import urllib3
from bs4 import BeautifulSoup

from common.exceptions import GetPageSourseException
from common.project_types import BookInfo

logger = logging.getLogger(__name__)


def parse_book_url(book_url: str, choose_book_class: dict[str, Callable]) -> tuple[str, str, Callable]:
    """возвращает site_name, book_link, book_class"""
    logger.debug(f'{book_url}')
    error_message = f'{book_url=} - неподходящий url'
    site_name_raw = re.match(r'^(https://.+?)/', book_url)
    logger.debug(f'{site_name_raw}')
    if site_name_raw:
        site_name = site_name_raw.group(1)

    else:
        logger.error(error_message)
        raise GetPageSourseException(error_message)

    book_link = book_url.replace(site_name, '')

    return site_name, book_link, choose_book_class[site_name]


def request_get_image(image_link: str) -> requests.Response:
    user = fake_useragent.UserAgent().random
    header = {'user-agent': user}
    response = requests.get(image_link, headers=header)
    return response


def create_soup(page_source: str) -> BeautifulSoup:
    soup = BeautifulSoup(page_source, 'html5lib')
    return soup


def print_book_info(book_info: BookInfo) -> None:
    for line in book_info.__dict__:
        print(line, book_info.__getattribute__(line))


def form_acceptable_name(file_name: str, file_name_length: int) -> str:
    """Функция убирает недопустимые символы из имени файла"""
    logger.debug(f'Имя до очиски {file_name=}')
    for letter in file_name:
        if not letter.isalnum() and letter not in ' -–_$#&@!%(){}¢`~^,':
            file_name = file_name.replace(letter, '~')
    if len(file_name) > file_name_length:
        file_name = file_name[:file_name_length]
    logger.debug(f'Имя после очистки {file_name=}')
    return file_name.strip()


def send_telegram_message(channel_name: Literal['book_chat', 'youtube_chat', 'common'], text: str) -> None:
    dotenv.load_dotenv()
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    book_chat_id = os.getenv('TELEGRAM_BOOK_CHAT_ID')
    youtube_chat_id = os.getenv('TELEGRAM_YOUTUBE_CHAT_ID')
    common_chat_id = os.getenv('TELEGRAM_COMMON_CHAT_ID')
    match channel_name:
        case 'book_chat':
            chat_id = book_chat_id
        case 'youtube_chat':
            chat_id = youtube_chat_id
        case 'common':
            chat_id = common_chat_id
        case _:
            error_message = 'Не указан telegram канал'
            logger.error(error_message)
            raise GetPageSourseException(error_message)


    url = f'https://api.telegram.org/bot{token}/sendMessage'
    post_data = {'chat_id': chat_id,
                 'text': text}
    http = urllib3.PoolManager()
    logger.debug(f'{token=}, {chat_id=}, {text=}')

    http.request(method='POST', url=url, fields=post_data)
