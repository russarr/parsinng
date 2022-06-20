from bs4 import BeautifulSoup
from common.common import ChapterLinkName  # type: ignore
from pathlib import Path
from datetime import datetime
from utils.exceptions import ParsingException, GetPageSourseException  # type: ignore
from common.common import request_get_image
import re
from common.common import BookInfo
from site_parsers.sol.sol_requests_soup import SolRequestsSoup
import logging
from requests import Session

logger = logging.getLogger(__name__)


class SolBook(SolRequestsSoup):
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

    def get_storiesonline_book_info(self) -> None:
        logger.debug('Получаем информацию о книге')
        book_soup = self.get_book_soup()
        self._get_author_title(book_soup)
        self._get_chapters_links(book_soup)
        self._create_book_directories()
        self._get_book_cover(book_soup)
        self._get_book_details()

    def download_chapter(self, chapter_link_name: ChapterLinkName, session: Session) -> None:
        logger.debug(f'Скачиваем главу: {chapter_link_name}')
        if chapter_link_name:
            chapter_link = chapter_link_name.chapter_link
            chapter_name = chapter_link_name.chapter_name
            chapter_order_position = chapter_link_name.chapter_order_position
            session = self.create_sol_requests_session()
            chapter_soup = self.get_chapter_soup(chapter_link, session)
            chapter_info = self._get_chapter_info(chapter_soup)
        else:
            error_message = f'Нет ссылки и имени главы'
            logger.error(error_message)
            raise ParsingException(error_message)

    def _get_chapter_info(self, chapter_soup: BeautifulSoup): pass



    def _get_author_title(self, book_soup: BeautifulSoup) -> None:
        logger.debug('Получаем название и имя автора')
        author_name = book_soup.find('a', rel="author")
        author_link = book_soup.find('a', rel="author")
        book_title = book_soup.find('a', rel="bookmark")
        if all([author_name, author_link, book_title]):
            self.author_name = author_name.get_text()
            self.author_link = author_link.get('href')
            self.book_title = book_title.get_text()
            logger.debug(f'{self.author_name=}, {self.author_link=}, {self.book_title=}')
        else:
            logger.error('Не могу получить автора или название книги из soup')
            raise ParsingException('Не могу получить автора или название книги')

    def _get_chapters_links(self, book_soup: BeautifulSoup) -> None:
        logger.debug('получаем список ссылок на главы')
        soup = book_soup.find('div', id="index-list")
        if soup:
            self.chapters_links = tuple(ChapterLinkName(chapter_link=link[1].get('href'), chapter_name=link[1].text, chapter_order_position=link[0]) for link in enumerate(soup.findAll('a')))
            logger.debug(f'{self.chapters_links=}')
        else:
            logger.error('Не умею загружать короткие истории без списка глав')
            raise ParsingException('Не умею загружать короткие истории без списка глав')

    def _create_book_directories(self) -> None:
        logger.debug('создаем директории на диске')
        book_directory = ['book_database'] + self.author_link.split('/')[-1:] + self.book_link.split('/')[-1:]
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
        cover_link = book_soup.find('p', class_='c').find('img')
        if cover_link:
            cover_link = cover_link.get('src')
            image_response = request_get_image(cover_link)
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

    def _get_book_details(self) -> None:
        logger.debug('Получаем описание и детали книги')
        book_details_soup = self._get_book_details_soup()
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

    def _get_book_details_soup(self) -> BeautifulSoup:
        session = self.create_sol_requests_session()
        post_data = {
            "cmd": "showDetails",
            "data[]": self._get_sol_book_id()
        }
        response = session.post('https://storiesonline.net/res/responders/moreData.php', data=post_data)
        if response.status_code == 200:
            book_details_soup = self.create_soup(response.text)
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
        book_size_search = re.search(r'<b>Size:</b>\D*(\d+)\D*KB', book_details)
        book_size = int(book_size_search.group(1).strip()) if book_size_search else 0
        self.book_size = book_size

    def _get_book_votes_count(self, book_details: str) -> None:
        book_votes_count_search = re.search(r'<b>Votes:</b>\D*(\d+)', book_details)
        book_votes_count = int(book_votes_count_search.group(1).strip()) if book_votes_count_search else 0
        self.book_votes_count = book_votes_count

    def _get_book_score(self, book_details: str) -> None:
        book_score_search = re.search(r'<b>Score:</b>\D*(\d*\.\d+|\d+)', book_details)
        book_score = float(book_score_search.group(1).strip()) if book_score_search else 0.0
        self.book_score = book_score

    def _get_book_posted_date(self, book_details: str) -> None:
        book_posted_date_search = re.search(r'<b>Posted:</b>\D*(\d{4}-\d{2}-\d{2})', book_details)
        if book_posted_date_search:
            book_posted_date = book_posted_date_search.group(1)
            book_posted_date = int(datetime.strptime(book_posted_date, '%Y-%m-%d').timestamp())
        else:
            book_posted_date = 0
        self.book_posted_date = book_posted_date

    def _get_book_updated_date(self, book_details: str) -> None:
        book_updated_date_search = re.search(r'<b>(Updat|Conclud)ed:</b>\D*(\d{4}-\d{2}-\d{2})', book_details)
        if book_updated_date_search:
            book_updated_date = book_updated_date_search.group(2)
            book_updated_date = int(datetime.strptime(book_updated_date, '%Y-%m-%d').timestamp())
        else:
            book_updated_date = 0
        self.book_updated_date = book_updated_date

    def _get_book_status(self, book_details: str) -> None:
        book_status_search = re.search(r'<b>Posted:</b>\D*\d{4}-\d{2}-\d{2}(\D*)<b>Updated:</b>', book_details)
        book_status_html = book_status_search.group(1) if book_status_search else '<p></p>'
        book_status_raw = BeautifulSoup(book_status_html, 'html5lib').find()
        book_status_raw = book_status_raw.get_text().strip()
        if 'Incomplete' in book_status_raw:
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
