import logging
from utils.exceptions import GetPageSourseException  # type: ignore
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, NamedTuple
from db_moduls.db_common import BookDBCommon
from bs4 import BeautifulSoup
import requests
import fake_useragent

logger = logging.getLogger('logger')

class ChapterLinkName(NamedTuple):
    chapter_link: str
    chapter_name: str
    chapter_order_position: int


@dataclass
class ChapterInfo:
    chapter_file_name: str = ''
    chapter_link: str = ''
    chapter_name: str = ''
    book_link: str = ''
    chapter_updated_date: int = 0
    chapter_posted_date: int = 0


@dataclass()
class BookInfo:
    book_link: str
    site_name: Literal['https://forums.sufficientvelocity.com', 'https://forums.spacebattles.com', 'https://storiesonline.net'] = field(init=False)
    book_title: str = field(repr=False, init=False)
    author_name: str = field(repr=False, init=False)
    author_link: str = field(repr=False, init=False)
    book_directory: Path = field(repr=False, init=False)
    chapters_links: tuple[ChapterLinkName, ...] = field(repr=False, init=False)
    book_size: int = field(repr=False, init=False)
    book_score: float = field(repr=False, init=False)
    chapters_info_list: list[ChapterInfo] = field(repr=False, init=False)
    book_sex_content: str = field(repr=False, init=False)
    book_posted_date: int = field(repr=False, init=False)
    book_updated_date: int = field(repr=False, init=False)
    book_download_date: int = field(repr=False, init=False)
    book_description: str = field(repr=False, init=False)
    book_genre: str = field(repr=False, init=False)
    book_series: str = field(repr=False, init=False)
    book_tags: tuple[str, ...] = field(repr=False, init=False)
    book_series_order_position: int = field(repr=False, init=False)
    book_votes_count: int = field(repr=False, init=False)
    book_status: Literal['In progress', 'Concluded', 'Frozen'] = field(repr=False, init=False)
    book_monitoring_status: bool = field(repr=False, init=False, default=False)
    book_soup: BeautifulSoup = field(repr=False, init=False)






class Book(BookInfo, BookDBCommon):
    pass


def parse_book_url(book_url):
    logger.debug('парсим url')
    if book_url.startswith('https://forums.sufficientvelocity.com'):
        if not book_url.endswith('/threadmarks'):
            book_url += '/threadmarks'
        book_link = book_url.replace('https://forums.sufficientvelocity.com', '')
        site_name = 'https://forums.sufficientvelocity.com'

    elif 'https://forums.spacebattles.com/' in book_url:
        if not book_url.endswith('/threadmarks'):
            book_url += '/threadmarks'
        book_link = book_url.replace('https://forums.spacebattles.com/', '')
        site_name = 'https://forums.spacebattles.com/'

    elif 'https://storiesonline.net/' in book_url:
        book_link = book_url.replace('https://storiesonline.net/', '')
        site_name = 'https://storiesonline.net/'

    else:
        logger.error(f'{book_url} - wrong url')
        raise GetPageSourseException('wrong url')

    return book_link, site_name


def request_get_image(image_link: str) -> requests.Response:
    user = fake_useragent.UserAgent().random
    header = {'user-agent': user}
    response = requests.get(image_link, headers=header)
    return response
