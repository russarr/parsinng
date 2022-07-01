import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Literal

import bs4
from bs4 import BeautifulSoup
from requests import Session

from common.common import Book
from common.exceptions import ParsingException, GetPageSourseException
from common.project_types import ChapterInfo
from common.request_authorization import create_auth_session
from common.utils import create_soup
from db_modules.db_common import BookDB, check_book_link_in_db

logger = logging.getLogger(__name__)


class AoooBook(Book, BookDB):
    __slots__ = ("book_link",
                 "site_name",
                 "book_title",
                 "author_name",
                 "author_link",
                 "book_directory",
                 "book_size",
                 "book_score",
                 "chapters_info_list",
                 "book_sex_content",
                 "book_posted_date",
                 "book_updated_date",
                 "book_download_date",
                 "book_description",
                 "book_genre",
                 "book_series",
                 "book_tags",
                 "book_series_order_position",
                 "book_votes_count",
                 "book_status",
                 "book_monitoring_status")

    def __init__(self, book_link: str, site_name: Literal['https://archiveofourown.org'] = 'https://archiveofourown.org'):
        super().__init__(book_link, site_name)
        self.epub_download_link = ''

    def downoload_book(self, session: Session | None = None, redownload: bool = False) -> Session:
        """Фукнция скачивания или обновления книги."""
        if session is None:
            logger.debug('Сессия не передана, создаем сессию')
            session = self._create_auth_session()
        logger.debug(f'{check_book_link_in_db(self.book_link)=}')
        if check_book_link_in_db(self.book_link) and not redownload:
            logger.debug('Обновляем книгу')
            self._update_book(session)
        else:
            self._download_full_book(session)
        return session

    def _update_book(self, session: Session) -> None:
        """Обновление storiesonline книги"""
        logger.debug('Начинаем обновление книги')
        self.read_book_info_from_db()
        book_updated_date_in_db = self.book_updated_date
        self._get_book_info(session)
        if self.book_updated_date > book_updated_date_in_db:
            logger.debug('Дата обновления книги больше даты обновления в БД')
            self.update_book_in_db()
            self._download_epub(session)

    def _download_full_book(self, session: Session | None = None) -> None:
        if session is None:
            session = create_auth_session(site_alias='aooo')
        self._get_book_info(session)
        self._download_epub(session)
        self.add_book_to_db()

    def _download_epub(self, session: Session) -> None:
        logger.debug(f'Скачиваем epub файл книги {self.book_link}')
        response = session.get(self.epub_download_link)
        file_name = self._create_file_name()
        file_path = Path('C:\\Users\\Necros\\YandexDisk\\books').joinpath(file_name)
        if response.status_code == 200:
            logger.debug(response.headers)
            if response.headers['Content-Type'] == 'application/epub+zip':
                try:
                    with open(file_path, 'wb') as file:
                        file.write(response.content)
                    logger.info(f'C ficbook сохранена книга: "{file_name}"')
                except FileNotFoundError:
                    error_message = 'Ошибка сохранения fb2 файла книги на диск'
                    logger.error(error_message)
                    raise GetPageSourseException(error_message)
            else:
                error_message = f'Ответ на запрос при скачивании {self.book_link} не является epub-файлом'
                logger.error(error_message)
                raise ParsingException(error_message)
        else:
            error_message = f'Ошибка скачивания fb2 {self.book_link}'
            logger.error(error_message)
            raise GetPageSourseException(error_message)

    def _get_book_info(self, session: Session) -> None:
        """получения инфы о книги с stories_online"""
        logger.debug('Получаем информацию о книге')
        book_soup, chapters_list_soup = self.get_book_soup(session)
        self._get_book_details(book_soup)
        self._get_chapters_links(chapters_list_soup)
        # self.epub_download_link = self._get_epub_download_link(book_soup)
        # self._create_book_directories()
        # self._get_book_size()

    def _get_epub_download_link(self, book_soup: BeautifulSoup) -> str:
        logger.debug(f'Получаем ссылку для скачивания epub {self.book_link}')
        download_block = book_soup.find('li', class_="download")
        if isinstance(download_block, bs4.Tag):
            download_link: str = download_block.find('a', string='EPUB').get('href')  # type: ignore
            logger.debug(f'{download_link=}')
            return self.site_name + download_link
        else:
            error_message = f'Ошибка получения ссылки на epub-файл книги {self.book_link}'
            logger.error(error_message)
            raise ParsingException(error_message)

    def get_book_soup(self, session: Session) -> tuple[BeautifulSoup, BeautifulSoup]:
        """Функция получет soup для страницы с общей информацией и странцы со списком глав"""
        logger.debug('Получаем page sourse страницы с общей информацией о книге')
        response = session.get(self.site_name + self.book_link)
        if response.status_code == 200:
            general_info_soup = create_soup(response.text)
        else:
            error_message = 'Ошибка получения page sourse страницы с общей информацией о книге'
            logger.error(error_message)
            raise GetPageSourseException(error_message)

        logger.debug('Получаем page sourse страницы со списком глав')
        response = session.get(self.site_name + self.book_link + '/navigate')
        if response.status_code == 200:
            chapters_info_soup = create_soup(response.text)
        else:
            error_message = 'Ошибка получения page sourse страницы со списком глав'
            logger.error(error_message)
            raise GetPageSourseException(error_message)
        return general_info_soup, chapters_info_soup

    def _get_book_details(self, book_soup: BeautifulSoup) -> None:
        self._get_book_title(book_soup)
        self._get_author_details(book_soup)
        self._get_book_description(book_soup)
        self._get_book_dates(book_soup)
        self._get_book_status(book_soup)
        self._get_book_tags(book_soup)

    def _get_book_title(self, book_soup: BeautifulSoup) -> None:
        logger.debug('Получаем название книги')
        book_title_tag = book_soup.find(class_="title heading")
        error_message = 'Ошибка получения названия книги'
        if isinstance(book_title_tag, bs4.Tag):
            book_title = book_title_tag.get_text()
            if book_title:
                self.book_title = book_title.strip()
                logger.debug(f'{self.book_title}')
            else:
                logger.error(error_message)
                raise ParsingException(error_message)
        else:
            logger.error(error_message)
            raise ParsingException(error_message)

    def _get_author_details(self, book_soup: BeautifulSoup) -> None:
        logger.debug(f'Получаем имя и ссылку автора в книге {self.book_link}')
        author_details_tag = book_soup.find('a', rel="author")
        error_message = 'Ошибка получени имени автора'
        if isinstance(author_details_tag, bs4.Tag):
            author_name = author_details_tag.get_text()
            if author_name:
                self.author_name = author_name
            else:
                logger.error(error_message)
                raise ParsingException(error_message)
            author_link = author_details_tag.get('href')
            if isinstance(author_link, str):
                self.author_link = author_link
            else:
                logger.error(error_message)
                raise ParsingException(error_message)
            logger.debug(f'{self.author_name=}, {self.author_link=}')
        else:
            logger.error(error_message)
            raise ParsingException(error_message)

    def _get_book_description(self, book_soup: BeautifulSoup) -> None:
        logger.debug(f'Получаем описание книги {self.book_link}')
        book_description_tag = book_soup.find('div', class_="summary module")
        error_message = 'Ошибка получения описания книги'
        if isinstance(book_description_tag, bs4.Tag):
            book_description = book_description_tag.get_text()
            if book_description:
                self.book_description = book_description.strip()
                logger.debug(f'{self.book_description=}')
            else:
                logger.error(error_message)
                raise ParsingException(error_message)
        else:
            logger.error(error_message)
            raise ParsingException(error_message)

    def _get_book_dates(self, book_soup: BeautifulSoup) -> None:
        logger.debug(f'Получаем даты публикации и обновления книги {self.book_link}')
        posted_date_tag = book_soup.find('dd', class_="published")
        error_message = 'Ошибка получения даты публикации'
        if isinstance(posted_date_tag, bs4.Tag):
            book_posted_date = posted_date_tag.get_text()
            if isinstance(book_posted_date, str):
                self.book_posted_date = self._create_datetime(book_posted_date)
            else:
                logger.error(error_message)
                raise ParsingException(error_message)
        else:
            logger.error(error_message)
            raise ParsingException(error_message)

        updated_date_tag = book_soup.find('dd', class_="status")
        error_message = 'Ошибка получения даты обновления'
        if isinstance(updated_date_tag, bs4.Tag):
            book_updated_date = updated_date_tag.get_text()
            if isinstance(book_updated_date, str):
                self.book_updated_date = self._create_datetime(book_updated_date)
            else:
                logger.error(error_message)
                raise ParsingException(error_message)
        logger.debug(f'{self.book_posted_date=}, {self.book_updated_date=}')

    @staticmethod
    def _create_datetime(date_raw: str) -> int:
        date_datetime = datetime.strptime(date_raw, '%Y-%m-%d')
        date = int(date_datetime.timestamp())
        return date

    @staticmethod
    def _create_chapter_datetime(date_raw: str) -> int:
        date_datetime = datetime.strptime(date_raw, '(%Y-%m-%d)')
        date = int(date_datetime.timestamp())
        return date

    def _get_book_status(self, book_soup: BeautifulSoup) -> None:
        logger.debug(f'Получаем статус книги {self.book_link}')
        book_status_tag = book_soup.find('dd', class_="chapters")
        error_message = 'Ошибка получения статуса книги'
        if isinstance(book_status_tag, bs4.Tag):
            book_status = book_status_tag.get_text()
            if isinstance(book_status, str):
                book_status_re = re.match(r'(\d+/\?)|(\d+/\d+)', book_status)
                if book_status_re:
                    if book_status_re.group(1):
                        self.book_status = 'In progress'
                    elif book_status_re.group(2):
                        self.book_status = 'Concluded'
                    else:
                        logger.error(error_message)
                        raise ParsingException(error_message)
                else:
                    logger.error(error_message)
                    raise ParsingException(error_message)
            else:
                logger.error(error_message)
                raise ParsingException(error_message)
            logger.debug(f'{self.book_status}')
        else:
            logger.error(error_message)
            raise ParsingException(error_message)

    def _get_book_tags(self, book_soup: BeautifulSoup) -> None:
        logger.debug('Получаем тэги книги')
        book_tags_list = book_soup.find_all('a', class_="tag")
        self.book_tags = tuple(tag.get_text() for tag in book_tags_list)
        logger.debug(f'{self.book_tags}')

    def _get_chapters_links(self, chapters_soup: BeautifulSoup) -> None:
        logger.debug(f'Получаем список глав {self.book_link}')
        chapters_links_block = chapters_soup.find('ol', class_="chapter index group")
        if isinstance(chapters_links_block, bs4.Tag):
            chapters_info_list = chapters_links_block.find_all('li')
            if chapters_info_list:
                for number, chapter_info_tag in enumerate(chapters_info_list):
                    link = chapter_info_tag.find('a')
                    chapter_date_tag = chapter_info_tag.find('span', class_="datetime")
                    if isinstance(link, bs4.Tag) and isinstance(chapter_date_tag, bs4.Tag):
                        chapter_info = ChapterInfo(
                            chapter_link=link.get('href'),  # type: ignore
                            chapter_name=link.get_text(),
                            chapter_file_name=f'chapter_{str(number).zfill(4)}.html',
                            chapter_posted_date=self._get_chapter_date(chapter_date_tag),
                            book_link=self.book_link)
                        if chapter_info not in self.chapters_info_list:
                            self.chapters_info_list.append(chapter_info)
                    else:
                        error_message = f'Ошибка парсинга информации о главе {chapter_info_tag}'
                        logger.error(error_message)
                        raise ParsingException(error_message)
                logger.debug(f'{self.chapters_info_list=}')
            else:
                error_message = 'Ошибка получения списка глав'
                logger.error(error_message)
                raise ParsingException(error_message)

    def _get_chapter_date(self, chapter_date_tag: bs4.Tag) -> int:
        chapter_date = chapter_date_tag.get_text()
        if chapter_date:
            chapter_posted_date = self._create_chapter_datetime(chapter_date)
            return chapter_posted_date
        else:
            error_message = 'Ошибка получения даты главы'
            logger.error(error_message)
            raise ParsingException(error_message)
