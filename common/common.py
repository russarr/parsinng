from db_modules.db_common import BookDB
from epub.epub import BookEpub
from requests import Session
from db_modules.db_common import check_book_link_in_db
from common.project_types import ChapterLinkName
from common.utils import create_request_session
from pathlib import Path
from common.exceptions import ParsingException
from common.utils import form_acceptable_name

import logging
import time
import random

logger = logging.getLogger(__name__)

class Book(BookDB, BookEpub):
    def downoload_book(self, session: Session | None = None, redownload: bool = False) -> Session:
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
        for chapter in self.chapters_links:
            self._download_chapter(chapter, session)
            time.sleep(random.randint(1, 3))
        self.add_book_to_db()
        self.compile_epub_file()

    def _update_book(self, session: Session) -> None:
        """Обновление storiesonline книги"""
        logger.debug('Начинаем обновление книги')
        self.read_book_info_from_db()
        sorted_chapters_list_in_db = self._get_sorted_chapters()
        self._get_book_info(session)
        for chapter in self.chapters_links:
            if chapter.chapter_link not in sorted_chapters_list_in_db[:-1]:
                self._download_chapter(chapter, session)
                time.sleep(random.randint(1, 3))
        self.update_book_in_db()
        self.compile_epub_file()

    def _get_book_info(self, session: Session) -> None:
        raise NotImplementedError('Метод не переопределен _get_book_info')

    def _download_chapter(self, chapter_link_name: ChapterLinkName, session: Session) -> None:
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
        except PermissionError as e:
            logger.exception(f'Ошибка создания папки на диске')
            raise ParsingException(f'Ошибка создания папки на диске {e}')
        self.book_directory = book_path
        logger.debug(f'{self.book_directory=}')
