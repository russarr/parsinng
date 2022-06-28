import requests.exceptions
from bs4 import BeautifulSoup
from db_modules.db_common import BookDB
from epub.epub import BookEpub
from requests import Session
from db_modules.db_common import check_book_link_in_db
from common.project_types import ChapterInfo
from common.utils import create_request_session, create_soup
from pathlib import Path
from common.exceptions import ParsingException
from common.utils import form_acceptable_name, request_get_image
from tqdm import tqdm
from typing import Literal

import logging
import time
import random

logger = logging.getLogger(__name__)


class Book(BookDB, BookEpub):

    def __init__(self, book_link: str, site_name: Literal['https://forums.sufficientvelocity.com', 'https://forums.spacebattles.com', 'https://storiesonline.net']):
        super().__init__(book_link)
        self.site_name = site_name
        # self.book_link = book_link

    def downoload_book(self, session: Session | None = None, redownload: bool = False) -> Session:
        """Фукнция скачивания или обновления книги."""
        if session is None:
            session = self._create_auth_session()
        if check_book_link_in_db(self.book_link) and not redownload:
            self._update_book(session)
        else:
            self._download_full_book(session)
        return session

    def _download_full_book(self, session: Session) -> None:
        """Функция скачачивания книги полностью"""
        logger.debug(f'Начинаем скачивание книги {self.book_link}')

        self._get_book_info(session)
        for chapter in tqdm(self.chapters_info_list):
            try:
                self._download_chapter(chapter, session)
            except requests.exceptions.ConnectionError:  # в случае потери соединенеия, переподключение через 30с
                logger.exception('Дисконект')
                time.sleep(30)
                session = self._create_auth_session()
                self._download_chapter(chapter, session)
            time.sleep(random.randint(1, 3))
        self.calculate_book_size()
        self.add_book_to_db()
        self.compile_epub_file()

    def _update_book(self, session: Session) -> None:
        """Обновление storiesonline книги"""
        logger.debug('Начинаем обновление книги')
        self.read_book_info_from_db()
        sorted_chapters_list_in_db = self._get_sorted_chapters()
        book_updated_date_in_db = self.book_updated_date
        self._get_book_info(session)
        if self.book_updated_date > book_updated_date_in_db:
            for chapter in tqdm(self.chapters_info_list):
                if chapter.chapter_link not in sorted_chapters_list_in_db[:-1]:
                    self._download_chapter(chapter, session)
                    time.sleep(random.randint(1, 3))
            self.calculate_book_size()
            self.update_book_in_db()
            self.compile_epub_file()

    def _get_book_info(self, session: Session) -> None:
        raise NotImplementedError('Метод не переопределен _get_book_info')

    def _download_chapter(self, chapter_info: ChapterInfo, session: Session) -> None:
        raise NotImplementedError('Метод не переопределен _download_chapter')

    @staticmethod
    def _create_auth_session() -> Session:
        session = create_request_session()
        return session

    def _create_book_directories(self) -> None:
        logger.debug('создаем директории на диске')
        author_name = form_acceptable_name(self.author_name, 20)
        book_name = form_acceptable_name(self.book_title, 30)
        book_directory = ['book_database'] + [author_name] + [book_name]
        book_path = Path(*book_directory)
        book_images_path = book_path.joinpath('Images')
        book_texts_path = book_path.joinpath('Text')
        try:
            book_images_path.mkdir(parents=True, exist_ok=True)
            book_texts_path.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            error_message = f'Ошибка создания папки на диске {book_directory}'
            logger.exception(error_message)
            raise ParsingException(error_message)

        self.book_directory = book_path
        logger.debug(f'{self.book_directory=}')

    def _save_chapter_text_on_disk(self, chapter_text: str, chapter_info: ChapterInfo) -> Path:
        logger.debug('Сохраняем текст главы на диск')
        book_directory = Path(self.book_directory)
        chapter_path = book_directory.joinpath(f'Text/{chapter_info.chapter_file_name}')
        try:
            chapter_path.write_text(chapter_text, encoding='utf-8')
        except PermissionError:
            error_message = f'Не могу сохранить на диск {chapter_path=}'
            logger.error(error_message)
            raise ParsingException(error_message)
        return chapter_path

    @staticmethod
    def _save_image(image_link: str, book_path: Path) -> str:
        image_name = 'Images/' + image_link.split('/')[-1]
        image_path = book_path.joinpath(image_name)
        if image_path.exists():
            return image_name
        else:
            image_response = request_get_image(image_link)
            if image_response.status_code == 200:
                image = image_response.content
                image_path.write_bytes(image)
                return image_name
            elif image_response.status_code == 404:
                return image_name
            else:
                error_message = f'Ошибка {image_response.status_code} загрузки изображения {image_name} в тексте главы'
                logger.error(error_message)
                raise ParsingException(error_message)

    def _get_chapter_images(self, soup: BeautifulSoup) -> BeautifulSoup:
        """функция получения картинок в главе"""
        logger.debug('сохраняем изображения из текста')
        images = soup.findAll('img')
        for image in images:
            image_link = image.get('src')
            local_image_path = self._save_image(image_link, self.book_directory)
            if local_image_path:
                image['src'] = '../' + local_image_path  # добавлил ../ вначале адреса тэга, чтобы работало в .epub книгах
        return soup

    @staticmethod
    def _get_chapter_size(chapter_text: str) -> int:
        chapter_text = create_soup(chapter_text).get_text()
        chapter_size = len(chapter_text.encode('utf-8'))
        return int(chapter_size / 1024)

    def calculate_book_size(self) -> None:
        book_size = 0
        for chapter in self.chapters_info_list:
            book_size += chapter.chapter_size
        self.book_size = book_size

    def _clear_description(self) -> None:
        """Убирает символы, из-за которых epub ломается"""
        self.book_description = self.book_description.replace('&', 'and')
