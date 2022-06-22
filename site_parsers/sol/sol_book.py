import random
import time
import bs4
from bs4 import BeautifulSoup
from common.common import ChapterLinkName, ChapterInfo  # type: ignore
from pathlib import Path
from datetime import datetime
from common.exceptions import ParsingException, GetPageSourseException  # type: ignore
from common.utils import request_get_image  # type: ignore
import re
from common.common import BookInfo
from site_parsers.sol.sol_requests_soup import SolRequestsSoup  # type: ignore
import logging
from requests import Session
from common.utils import raise_exception, create_soup
from db_modules.db_common import BookDB
from epub.epub import BookEpub  # type: ignore

logger = logging.getLogger(__name__)


class SolBook(SolRequestsSoup, BookDB, BookEpub):
    __slots__ = ("book_link",
                 "site_name",
                 "book_title",
                 "author_name",
                 "author_link",
                 "book_directory",
                 "chapters_links",
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

    def __init__(self, book_link):
        super().__init__(book_link)
        self.site_name = 'https://storiesonline.net'

    def download_full_book(self):
        """Функция скачачивания книги полностью"""
        logger.debug('Начинаем скачивание книги')
        session = self.create_sol_requests_session()
        self._get_sol_book_info(session)
        for chapter in self.chapters_links:
            self._download_sol_chapter(chapter, session)
            time.sleep(random.randint(1, 3))
        session.close()
        self.add_book_to_db()

    def _get_sol_book_info(self, session: Session) -> None:
        logger.debug('Получаем информацию о книге')
        book_soup = self.get_book_soup(session)
        self._get_author_title(book_soup)
        self._get_chapters_links(book_soup)
        self._create_book_directories()
        self._get_book_cover(book_soup)
        self._get_book_details(session)

    def _download_sol_chapter(self, chapter_link_name: ChapterLinkName, session: Session) -> None:
        logger.debug(f'Скачиваем главу: {chapter_link_name}')
        if chapter_link_name:
            chapter_info = ChapterInfo(chapter_link=chapter_link_name.chapter_link,
                                       chapter_name=chapter_link_name.chapter_name,
                                       chapter_file_name=f'chapter_{str(chapter_link_name.chapter_order_position).zfill(4)}.html',
                                       book_link=self.book_link)
            chapter_soup = self.get_chapter_soup(chapter_info.chapter_link, session)
            chapter_info = self._get_chapter_info(chapter_soup, chapter_info)
            self.chapters_info_list.append(chapter_info)
        else:
            error_message = f'Нет ссылки и имени главы'
            logger.error(error_message)
            raise ParsingException(error_message)

    def _get_chapter_info(self, chapter_soup: BeautifulSoup, chapter_info: ChapterInfo) -> ChapterInfo:
        logger.debug('Парсим текс главы')
        chapter_soup = create_soup(str(chapter_soup.find('article')))
        if chapter_soup:
            chapter_info.chapter_posted_date, chapter_info.chapter_updated_date = self._get_chapter_dates(chapter_soup)
            chapter_soup = self._clear_chapter_soup(chapter_soup)
            chapter_soup = self._get_chapter_images(chapter_soup)
            chapter_text = self._get_chapter_text(chapter_soup)
            self._save_chapter_text_on_disk(chapter_text, chapter_file_name=chapter_info.chapter_file_name, book_directory=self.book_directory)
        else:
            raise_exception(ParsingException, 'Не могу найти тэг article')

        return chapter_info

    @staticmethod
    def _get_chapter_dates(chapter_soup) -> tuple[int, int]:
        logger.debug('Получаем даты в главе')
        chapter_dates = chapter_soup.find_all('div', class_="date")
        posted_date, updated_date = 0, 0
        for date in chapter_dates:
            posted_date_re = re.search(r'Posted:\D+(\d{13})', str(date))
            if posted_date_re:
                posted_date = int(posted_date_re.group(1)[:-3])  # type: ignore
            updated_date_re = re.search(r'Updated:\D+(\d{13})', str(date))
            if updated_date_re:
                updated_date = int(updated_date_re.group(1)[:-3])  # type: ignore
        if posted_date == 0 and updated_date == 0:
            raise_exception(ParsingException, 'Ошибка получения дат в главе')
        logger.debug(f'{posted_date=}, {updated_date=}')
        return posted_date, updated_date

    @staticmethod
    def _clear_chapter_soup(chapter_soup: BeautifulSoup) -> BeautifulSoup:
        """функция для удаления со страницы даты, ссылки на слудующую главу, формы голосования и т.д."""
        logger.debug('Удаляем лишнее из текста')
        tags_to_clear = ['div[class="date"]', 'a[accesskey="n"]', 'form[id="voteForm"]', 'div[class="end-note"]', 'div[class="vform"]']
        for tag in tags_to_clear:
            tag_to_delete = chapter_soup.select_one(tag)
            if tag_to_delete:
                tag_to_delete.decompose()
        return chapter_soup

    def _get_chapter_images(self, soup: BeautifulSoup) -> BeautifulSoup:
        """функция получения картинок в главе"""
        logger.debug('сохраняем изображения из текста')
        images = soup.findAll('img')
        for image in images:
            image_link = image.get('src')
            local_image_path = self._save_image(image_link, self.book_directory)
            if local_image_path:
                image['src'] = '../' + local_image_path  # добавлил ../ вначале адреса тэга, чтобы работатла в .epub книгах
        return soup

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

    def _get_chapter_text(self, soup: BeautifulSoup) -> str:
        logger.debug('Получаем финальный текст главы')
        chapter_text = str(soup).strip()
        chapter_text = self._replace_unreadable_symbols(chapter_text)
        return chapter_text

    @staticmethod
    def _replace_unreadable_symbols(chapter_text: str) -> str:
        logger.debug('Заменяем нечитаемые символы')
        for symbol in '‘’':
            chapter_text = chapter_text.replace(symbol, "'")
        for symbol in '“”':
            chapter_text = chapter_text.replace(symbol, '"')
        return chapter_text

    @staticmethod
    def _save_chapter_text_on_disk(chapter_text, chapter_file_name: str, book_directory: Path) -> Path:
        logger.debug('Сохраняем текст главы на диск')
        chapter_path = book_directory.joinpath(f'Text/{chapter_file_name}')
        try:
            chapter_path.write_text(chapter_text, encoding='utf-8')
        except PermissionError:
            raise_exception(ParsingException, f'Не могу сохранить на диск {chapter_path=}')
        return chapter_path

    def _get_author_title(self, book_soup: BeautifulSoup) -> None:
        logger.debug('Получаем название и имя автора')
        author_name = book_soup.find('a', rel="author")
        author_link = book_soup.find('a', rel="author")
        book_title = book_soup.find('a', rel="bookmark")
        if all([author_name, author_link, book_title]):
            self.author_name = author_name.get_text()  # type: ignore
            self.author_link = author_link.get('href')  # type: ignore
            self.book_title = book_title.get_text()  # type: ignore
            logger.debug(f'{self.author_name=}, {self.author_link=}, {self.book_title=}')
        else:
            raise_exception(ParsingException, 'Не могу получить автора или название книги из soup')

    def _get_chapters_links(self, book_soup: BeautifulSoup) -> None:
        logger.debug('получаем список ссылок на главы')
        soup = book_soup.find('div', id="index-list")
        if soup:
            assert isinstance(soup, bs4.Tag)
            self.chapters_links = tuple(ChapterLinkName(chapter_link=link[1].get('href'), chapter_name=link[1].text, chapter_order_position=link[0]) for link in enumerate(soup.findAll('a')))
            logger.debug(f'{self.chapters_links=}')
        else:
            logger.error('Не умею загружать короткие истории без списка глав')
            raise ParsingException('Не умею загружать короткие истории без списка глав')

    def _create_book_directories(self) -> None:
        logger.debug('создаем директории на диске')
        book_directory = ['book_database'] + self.author_link.split('/')[-1:] + self.book_link.split('/')[-1:]  # type: ignore
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

    def _get_book_cover(self, book_soup: BeautifulSoup) -> None:
        logger.debug('сохраянем обложку книги')
        cover_link = book_soup.find('p', class_='c').find('img')  # type: ignore
        if cover_link:
            cover_link = cover_link.get('src')  # type: ignore
            image_response = request_get_image(cover_link)  # type: ignore
            if image_response.status_code == 200:
                image = image_response.content
                book_cover_path = self.book_directory.joinpath('Images/_cover.jpg')
                try:
                    book_cover_path.write_bytes(image)
                    logger.debug(f'обложку загрузили {book_cover_path}')
                except FileNotFoundError as e:
                    logger.exception(f'Не могу сохранить обложку книги {self.book_link} на диск')
                    raise ParsingException(f'Не могу сохранить обложку на диск {e}')
            else:
                logger.error(f'Не могу загрузить обложку, {image_response.status_code=}')
        else:
            logger.debug('обложки нет')

    def _get_book_details(self, session: Session) -> None:
        logger.debug('Получаем описание и детали книги')
        book_details_soup = self._get_book_details_soup(session)
        find_result = book_details_soup.find('p')
        if book_details_soup:
            book_details = str(find_result)
            self._get_book_description(book_details)
            self._get_book_sex_content(book_details)
            self._get_book_genre(book_details)
            self._get_book_tags(book_details)
            self._get_book_size(book_details)
            self._get_book_votes_count(book_details)
            self._get_book_score(book_details)
            self._get_book_posted_date(book_details)
            self._get_book_updated_date(book_details)
            self._get_book_status(book_details)
            logger.debug(f'{self.book_description=}\n{self.book_sex_content=}\n{self.book_genre=}\n{self.book_tags=}\n{self.book_size=}\n{self.book_votes_count=}\n{self.book_score=}')
            logger.debug(f'{self.book_posted_date=}\n{self.book_updated_date=}\n{self.book_status=}')
        else:
            logger.error(f'Не могу загрузить описание книги {self.book_link}')
            raise ParsingException(f'Не могу загрузить описание книги {self.book_link}')

    def _get_book_details_soup(self, session: Session) -> BeautifulSoup:
        post_data = {
            "cmd": "showDetails",
            "data[]": self._get_sol_book_id()
        }
        response = session.post('https://storiesonline.net/res/responders/moreData.php', data=post_data)
        if response.status_code == 200:
            book_details_soup = create_soup(response.text)
            return book_details_soup
        else:
            error_message = f'Не могу получить детали {self.book_link=}'
            logger.error(error_message)
            raise GetPageSourseException(error_message)

    def _get_book_description(self, book_details: str) -> None:
        book_description_search = re.search(r'<b>Synopsis:</b>(.*)<br/>', book_details)
        book_description = str(book_description_search.group(1)).strip() if book_description_search else ''
        self.book_description = book_description

    def _get_book_sex_content(self, book_details: str) -> None:
        book_sex_content_search = re.search(r'<b>Sex Contents:</b>(.*)<br/>', book_details)
        book_sex_content = str(book_sex_content_search.group(1)).strip() if book_sex_content_search else ''
        self.book_sex_content = book_sex_content

    def _get_book_genre(self, book_details: str) -> None:
        book_genre_search = re.search(r'<b>Genre:</b>(.*)<br/>', book_details)
        book_genre = book_genre_search.group(1).strip() if book_genre_search else ''
        self.book_genre = book_genre

    def _get_book_tags(self, book_details: str) -> None:
        book_tags_search = re.search(r'<b>Codes:</b>(.*)<br/>', book_details)
        if book_tags_search:
            book_tags = book_tags_search.group(1).strip()
            book_tags = tuple(book_tags.split(', '))
        else:
            return None
        self.book_tags = book_tags

    def _get_book_size(self, book_details: str) -> None:
        book_size_search = re.search(r'<b>Size:</b>\s*(\d+)\s*KB', book_details)
        book_size = int(book_size_search.group(1).strip()) if book_size_search else 0
        self.book_size = book_size

    def _get_book_votes_count(self, book_details: str) -> None:
        book_votes_count_search = re.search(r'<b>Votes:</b>\s*(\d+)\s', book_details)
        book_votes_count = int(book_votes_count_search.group(1).strip()) if book_votes_count_search else 0
        self.book_votes_count = book_votes_count

    def _get_book_score(self, book_details: str) -> None:
        book_score_search = re.search(r'<b>Score:</b>\s*(\d*\.\d+|\d+)\\n', book_details)
        logger.debug(f'{book_score_search=}')
        book_score = float(book_score_search.group(1).strip()) if book_score_search else 0.0
        self.book_score = book_score

    def _get_book_posted_date(self, book_details: str) -> None:
        book_posted_date_search = re.search(r'<b>Posted:</b>\s*(\d{4}-\d{2}-\d{2})', book_details)
        if book_posted_date_search:
            book_posted_date = book_posted_date_search.group(1)
            book_posted_date = int(datetime.strptime(book_posted_date, '%Y-%m-%d').timestamp())
        else:
            book_posted_date = 0
        self.book_posted_date = book_posted_date

    def _get_book_updated_date(self, book_details: str) -> None:
        book_updated_date_search = re.search(r'<b>(Updat|Conclud)ed:</b>\s*(\d{4}-\d{2}-\d{2})', book_details)
        if book_updated_date_search:
            book_updated_date = book_updated_date_search.group(2)
            book_updated_date = int(datetime.strptime(book_updated_date, '%Y-%m-%d').timestamp())
        else:
            book_updated_date = 0
        self.book_updated_date = book_updated_date

    def _get_book_status(self, book_details: str) -> None:
        book_status_search = re.search(r'<b>Posted:</b>\D*\d{4}-\d{2}-\d{2}(\D*)<b>Updated:</b>', book_details)
        book_status_html = book_status_search.group(1) if book_status_search else '<p></p>'
        book_status_raw = create_soup(book_status_html).find()
        book_status_raw = book_status_raw.get_text().strip()  # type: ignore
        if 'Incomplete' in book_status_raw:  # type: ignore
            self.book_status = 'Frozen'
        if re.search('<b>Concluded:</b>', book_details):
            self.book_status = 'Concluded'
        if book_status_raw == 'in progress':
            self.book_status = 'In progress'

        if self.book_status not in ('Frozen', 'Concluded', 'In progress'):
            logger.error(f'Неизвестный статус {book_status_raw}')
            raise ParsingException(f'Неизвестный статус {book_status_raw}')

    def _get_sol_book_id(self) -> str:
        if self.book_link:
            book_id = self.book_link.split('/')[2]
            if book_id.isdecimal():
                logger.debug(f'{book_id=}')
                return book_id
            else:
                logger.error(f'Проблема с получением book_id {self.book_link}: {book_id} должно быть число')
                raise ParsingException(f'Проблема с получением book_id {self.book_link}: {book_id} должно быть число')
        else:
            logger.error(f'Проблема с получением book_id: отсутствует {self.book_link}')
            raise ParsingException(f'Проблема с получением book_id: отсутствует {self.book_link}')


def _print_book_info(book_info: BookInfo) -> None:
    for line in book_info.__dict__:
        print(line, book_info.__getattribute__(line))
