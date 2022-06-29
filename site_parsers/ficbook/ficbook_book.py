import re
import time
from typing import Literal
import bs4
from common.utils import create_soup
from db_modules.db_common import BookDB
from common.common import Book
from bs4 import BeautifulSoup
from requests import Session
from requests.exceptions import JSONDecodeError
from common.exceptions import GetPageSourseException, ParsingException
import logging
from common.project_types import ChapterInfo, BookInfo, site_names_type, book_status_type
from datetime import datetime
from common.request_authorization import create_auth_session
from common.utils import form_acceptable_name
from pathlib import Path

logger = logging.getLogger(__name__)


class FicbookBook(Book, BookDB, BookInfo):
    __slots__ = ("book_link",
                 "site_name",
                 "book_title",
                 "author_name",
                 "author_link",
                 "book_size",
                 "book_posted_date",
                 "book_updated_date",
                 "book_download_date",
                 "book_description",
                 "book_status",
                 "book_monitoring_status")

    def __init__(self, book_link: str, site_name: site_names_type = 'https://ficbook.net'):
        super().__init__(book_link, site_name)

    def downoload_book(self, session: Session | None = None, redownload: bool = False) -> Session:
        if session is None:
            session = create_auth_session(site_alias='ficbook')
        self._get_book_info(session)
        self._download_epub(session)
        self.add_book_to_db()

        return session

    def _get_book_info(self, session: Session) -> None:
        logger.debug(f'Получаем информацию о книге {self.book_link}')
        book_soup = self._get_ficbook_soup(session)
        self._get_book_details(book_soup)

    def _download_epub(self, session: Session) -> None:
        logger.debug(f'Скачиваем epub файл книги {self.book_link}')
        book_id = self._extract_book_id()
        epub_url = f'{self.site_name}/fanfic_download/{book_id}/epub'
        response = session.get(epub_url)
        file_name = self._create_file_name()
        file_path = Path('C:\\Users\\Necros\\YandexDisk\\books').joinpath(file_name)
        if response.status_code == 200:
            try:
                with open(file_path, 'wb') as file:
                    file.write(response.content)
                logger.info(f'C ficbook сохранена книга {file_name}')
            except FileNotFoundError:
                error_message = 'Ошибка сохранения fb2 файла книги на диск'
                logger.error(error_message)
                raise GetPageSourseException(error_message)
        else:
            error_message = f'Ошибка скачивания fb2 {self.book_link}'
            logger.error(error_message)
            raise GetPageSourseException(error_message)

    def _extract_book_id(self) -> str:
        logger.debug(f'извлекаем book_id из {self.book_link=}')
        book_id = self.book_link.split('/')[-1]
        return book_id

    def _get_ficbook_soup(self, session: Session) -> BeautifulSoup:
        logger.debug('Получаем page sourse основной страницы книги')
        response = session.get(self.site_name + self.book_link)
        page_soup = create_soup(response.text)
        return page_soup

    def _get_book_details(self, book_soup: BeautifulSoup) -> None:
        self.book_title = self._get_book_title(book_soup)
        self.author_name, self.author_link = self._get_author_name_link(book_soup)
        self.book_status = self._get_book_status(book_soup)
        self.book_description = self._get_book_description(book_soup)
        self.book_posted_date, self.book_updated_date = self._get_book_dates(book_soup)

    @staticmethod
    def _get_book_title(book_soup: BeautifulSoup) -> str:
        logger.debug('Получаем название книги')
        book_title_raw = book_soup.find('h1', class_="mb-10")
        if book_title_raw and isinstance(book_title_raw, bs4.Tag):
            book_title: str = book_title_raw.get_text()
            logger.debug(f'{book_title=}')
            return book_title
        else:
            error_message = 'Ошибка получения названия книги'
            logger.error(error_message)
            raise ParsingException(error_message)

    @staticmethod
    def _get_author_name_link(book_soup: BeautifulSoup) -> tuple[str, str]:
        logger.debug('Получаем имя автора и ссылку автора')
        author_name_raw = book_soup.find('a', class_="creator-nickname")
        error_message = 'Ошибка получения имени автора и ссылки автора'
        if author_name_raw and isinstance(author_name_raw, bs4.Tag):
            author_name = author_name_raw.get_text()
            author_link = author_name_raw.get('href')
            if isinstance(author_name, str) and isinstance(author_link, str):
                logger.debug(f'{author_name=}, {author_link=}')
                return author_name, author_link
            else:
                logger.error(error_message)
                raise ParsingException(error_message)
        else:
            logger.error(error_message)
            raise ParsingException(error_message)

    @staticmethod
    def _get_book_status(book_soup: BeautifulSoup) -> book_status_type:
        logger.debug('Получаем book_status')
        book_status_raw = book_soup.find('div', class_=re.compile("badge-with-icon badge-secondary badge-status(.*)"))
        if isinstance(book_status_raw, bs4.Tag):
            book_status_raw: str = book_status_raw.get_text()
            book_status_raw = book_status_raw.strip()
            if book_status_raw == 'В процессе':
                book_status: book_status_type = 'In progress'
            elif book_status_raw == 'Завершён':
                book_status = 'Concluded'
            elif book_status_raw == 'Заморожен':
                book_status = 'Frozen'
            else:
                error_message = f'Неизвестный статус книги {book_status_raw}'
                logger.error(error_message)
                raise ParsingException(error_message)
        else:
            error_message = 'Ошибка получения статуса книги'
            logger.error(error_message)
            raise ParsingException(error_message)
        logger.debug(f'{book_status=}')
        return book_status

    @staticmethod
    def _get_book_description(book_soup: BeautifulSoup) -> str:
        logger.debug('Получаем описание')
        book_description_raw = book_soup.find('div', class_="fanfic-hat-body rounded-block clearfix")
        if isinstance(book_description_raw, bs4.Tag):
            book_descripton = book_description_raw.get_text().strip()
            while '  ' in book_descripton:
                book_descripton = book_descripton.replace('  ', ' ')
            while '\n\n' in book_descripton:
                book_descripton = book_descripton.replace('\n\n', '\n')
            while '\n \n ' in book_descripton:
                book_descripton = book_descripton.replace('\n \n ', '\n')
            while '\n\n' in book_descripton:
                book_descripton = book_descripton.replace('\n\n', '\n')
            logger.debug(f'{book_descripton=}')
            return book_descripton
        else:
            error_message = 'Ошибка получения описания книги'
            logger.error(error_message)
            raise ParsingException(error_message)

    def _get_book_dates(self, book_soup: BeautifulSoup) -> tuple[int, int]:
        logger.debug('Получаем даты публикации и обновления')
        chapters = book_soup.find_all('div', class_="part-info text-muted")
        if chapters:
            book_posted_date_raw = chapters[0].find('span')
            error_message = 'Ошибка получения даты публикации'
            book_posted_date = self._parse_book_dates(book_posted_date_raw, error_message)
            error_message = 'Ошибка получения даты обновления'
            book_updated_date_raw = chapters[-1].find('span')
            book_updated_date = self._parse_book_dates(book_updated_date_raw, error_message)
            logger.debug(f'{book_posted_date=}, {book_updated_date=}')
            return book_posted_date, book_updated_date
        else:
            error_message = 'Ошибка получения дат книги'
            logger.error(error_message)
            raise ParsingException(error_message)

    @staticmethod
    def _parse_book_dates(date_raw: bs4.Tag, error_message: str) -> int:
        months = {'января': 'jan',
                  'февраля': 'feb',
                  'марта': 'mar',
                  'апреля': 'apr',
                  'мая': 'may',
                  'июня': 'jun',
                  'июля': 'jul',
                  'августа': 'aug',
                  'сентябся': 'sep',
                  'октября': 'oct',
                  'ноября': 'nov',
                  'декабря': 'dec', }
        if isinstance(date_raw, bs4.Tag):
            date_raw = date_raw.get_text()
            if isinstance(date_raw, str):
                for month in months:
                    date_raw = date_raw.replace(month, months[month])
                date_raw = datetime.strptime(date_raw, '%d %b %Y, %H:%M')
                date = int(date_raw.timestamp())
                return date
            else:
                logger.error(error_message)
                raise ParsingException(error_message)
        else:
            logger.error(error_message)
            raise ParsingException(error_message)
