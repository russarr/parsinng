import re
from typing import Literal

import bs4

from common.utils import create_soup
from db_modules.db_common import BookDB
from epub.epub import BookEpub
from bs4 import BeautifulSoup
from requests import Session
from requests.exceptions import JSONDecodeError
from common.exceptions import GetPageSourseException, ParsingException
import logging
from common.project_types import ChapterInfo

logger = logging.getLogger(__name__)


class SfSbBook(BookDB, BookEpub):
    __slots__ = ("book_link",
                 "site_name",
                 "book_title",
                 "author_name",
                 "author_link",
                 "book_directory",
                 "chapters_links",
                 "book_size",
                 "chapters_info_list",
                 "book_posted_date",
                 "book_updated_date",
                 "book_download_date",
                 "book_description",
                 "book_status",
                 "book_monitoring_status")

    def __init__(self, site_name: Literal['https://forums.sufficientvelocity.com', 'https://forums.spacebattles.com', 'https://storiesonline.net'], book_link: str):
        super().__init__(book_link)
        self.site_name = site_name
        self.book_link = book_link

    def _get_book_info(self) -> None:
        # session = create_request_session()
        # book_soup = self._get_sf_sb_soup(session)
        pass

    def _get_sf_sb_soup(self, session: Session) -> None:
        logger.debug('Получаем page sourse основной страницы')
        response = session.get(self.site_name + self.book_link)
        page_soup = create_soup(response.text)
        page_soup = self._open_hidden_chapters(page_soup, session)
        self._get_chapters_info(page_soup)

    def _open_hidden_chapters(self, page_soup: BeautifulSoup, session: Session) -> BeautifulSoup:
        logger.debug('Проверяем есть ли скрытые главы')
        hidden_block = page_soup.find('div', class_="structItem structItem--threadmark structItem--threadmark-filler")
        if hidden_block:
            logger.debug('открываем скрытые главы')
            hidden_url = self._find_hidden_url(page_soup)
            post_data = self._get_bot_protection_token(page_soup)
            response = session.post(self.site_name + hidden_url, data=post_data)
            try:
                json_data = response.json()
                json_data = json_data['html']['content']
                hidden_soup = create_soup(json_data)
                hidden_block.replace_with(hidden_soup)
            except (JSONDecodeError, KeyError):
                error_message = f'Ошибка получения json ответа, при запросе скрытых глав, по книге {self.book_link}'
                logger.error(error_message)
                raise GetPageSourseException(error_message)
        return page_soup

    def _get_bot_protection_token(self, page_soup: BeautifulSoup) -> dict[str, str]:
        find_token = page_soup.find('html')
        assert isinstance(find_token, bs4.Tag)
        token = find_token.get('data-csrf')
        if isinstance(token, str):
            logger.debug(f'{token=}')
            post_data = {'_xfRequestUri': self.book_link,
                         '_xfWithData': '1',
                         '_xfToken': token,
                         '_xfResponseType': "json"
                         }
            return post_data
        else:
            error_message = f'Ошибка получения токена со страницы {self.book_link}'
            logger.error(error_message)
            raise GetPageSourseException(error_message)

    def _get_chapters_info(self, page_soup: BeautifulSoup) -> None:
        logger.debug('Получаем информацию о главах')
        # в название атрибута добавляется unread, если глава не прочитана, и она пролетает мимо поиска, поэтому regex
        chapter_lines = page_soup.find_all('div', class_=re.compile(r"structItem structItem--threadmark\D*"))
        if chapter_lines:
            for number, chapter in enumerate(chapter_lines):
                self._parse_chapter_info(number, chapter)

        else:
            error_message = f'Ошибка при получении списка глав в книге {self.book_link}'
            logger.error(error_message)
            raise ParsingException(error_message)

    def _find_hidden_url(self, page_soup: BeautifulSoup) -> str:
        find_hidden_url = page_soup.find('div', {'data-fetchurl': re.compile(r'(\D*)')})
        if isinstance(find_hidden_url, bs4.Tag):
            hidden_url = find_hidden_url.get('data-fetchurl')
            assert isinstance(hidden_url, str)
        else:
            error_message = f'Ошибка получения ссылки на скрытые главы в книге {self.book_link}'
            logger.error(error_message)
            raise ParsingException(error_message)
        return hidden_url

    def _parse_chapter_info(self, number: int, chapter_info_block: bs4.Tag) -> None:
        chapter_order_position = number
        chapter_link, chapter_name = self._get_chapter_link_name(chapter_info_block)
        chapter_posted_date = self._get_chapter_posted_date(chapter_info_block)

        chapter_info = ChapterInfo(
            chapter_name=chapter_name,
            chapter_link=chapter_link,
            chapter_file_name=f'chapter_{str(chapter_order_position).zfill(4)}.html',
            book_link=self.book_link,
            chapter_posted_date=chapter_posted_date
        )
        self.chapters_info_list.append(chapter_info)

    @staticmethod
    def _get_chapter_posted_date(chapter_info_block: bs4.Tag) -> int:
        chapter_date_block = chapter_info_block.find('time')
        if isinstance(chapter_date_block, bs4.Tag):
            chapter_posted_date = chapter_date_block.get('data-time')
            assert isinstance(chapter_posted_date, str)
        else:
            error_message = f'Ошибка получения posted date: не могу найти блоr time'
            logger.error(error_message)
            raise ParsingException(error_message)
        if chapter_posted_date and chapter_posted_date.isdecimal():
            return int(chapter_posted_date)
        else:
            error_message = f'Ошибка получения posted date'
            logger.error(error_message)
            raise ParsingException(error_message)

    @staticmethod
    def _get_chapter_link_name(chapter_info_block: bs4.Tag) -> tuple[str, str]:
        info_block = chapter_info_block.find('div', class_="structItem-cell structItem-cell--main")
        if isinstance(info_block, bs4.Tag):
            info_block = info_block.find('a')
            if isinstance(info_block, bs4.Tag):
                chapter_link = str(info_block.get('href'))
                chapter_name = info_block.get_text().strip()
                return chapter_link, chapter_name
            else:
                error_message = f'Ошибка получения блока с именем и ссылкой главы'
                logger.error(error_message)
                raise ParsingException(error_message)

        else:
            error_message = f'Ошибка получения блока с именем и ссылкой главы'
            logger.error(error_message)
            raise ParsingException(error_message)
