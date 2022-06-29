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
from common.project_types import ChapterInfo, BookInfo

logger = logging.getLogger(__name__)


class SfSbBook(Book, BookDB, BookInfo):
    __slots__ = ("book_link",
                 "site_name",
                 "book_title",
                 "author_name",
                 "author_link",
                 "book_directory",
                 "book_size",
                 "chapters_info_list",
                 "book_posted_date",
                 "book_updated_date",
                 "book_download_date",
                 "book_description",
                 "book_status",
                 "book_monitoring_status")

    def __init__(self, book_link: str, site_name: Literal['https://forums.sufficientvelocity.com', 'https://forums.spacebattles.com']):
        if not book_link.endswith('/threadmarks'):
            book_link += '/threadmarks'
        super().__init__(book_link, site_name)

    def _get_book_info(self, session: Session) -> None:
        book_soup = self._get_sf_sb_soup(session)
        self._get_book_details(book_soup)
        self._create_book_directories()

    def _download_chapter(self, chapter_link: ChapterInfo, session: Session) -> None:
        chapter_soup = self._get_chapter_soup(chapter_link, session)
        chapter_text = self._get_chapter_text(chapter_soup)
        chapter_link.chapter_size = self._get_chapter_size(chapter_text)
        self._save_chapter_text_on_disk(chapter_text, chapter_link)
        # загрузку картинок отключил, ресурс заблокирован, нужно либо прокси, либо vpn
        # self._get_chapter_images(chapter_soup)

    def _get_sf_sb_soup(self, session: Session) -> BeautifulSoup:
        logger.debug('Получаем page sourse основной страницы книги')
        response = session.get(self.site_name + self.book_link)
        page_soup = create_soup(response.text)
        page_soup = self._open_hidden_chapters(page_soup, session)
        try:
            self._get_chapters_info(page_soup)
        except ParsingException:
            # повторное выполнение в случае ошибки
            print('ПОВТОРНАЯ ПОПЫТКА')
            time.sleep(5)
            self._get_chapters_info(page_soup)
        return page_soup

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
                chapter_info = self._parse_chapter_info(number, chapter)
                if chapter_info not in self.chapters_info_list:
                    self.chapters_info_list.append(chapter_info)

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

    def _parse_chapter_info(self, number: int, chapter_info_block: bs4.Tag) -> ChapterInfo:
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
        return chapter_info

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

    def _get_book_details(self, book_soup: BeautifulSoup) -> None:
        self._get_book_title(book_soup)
        self._get_author_info(book_soup)
        self._get_book_description(book_soup)
        self._clear_description()
        self._get_book_dates(book_soup)
        self._get_book_status(book_soup)

    def _get_book_title(self, book_soup: BeautifulSoup) -> None:
        book_title_raw = book_soup.find(class_="threadmarkListingHeader-name")
        if book_title_raw and isinstance(book_title_raw, bs4.Tag):
            rss_child = book_title_raw.findChild()
            if rss_child and isinstance(rss_child, bs4.Tag):
                rss_child.decompose()
            self.book_title = book_title_raw.get_text().strip()
            logger.debug(f'{self.book_title}')
        else:
            error_message = f'Не могу получить название книги {self.book_link}'
            logger.error(error_message)
            raise ParsingException(error_message)

    def _get_author_info(self, book_soup: BeautifulSoup) -> None:
        author_name_raw = book_soup.find('a', class_="username")
        if author_name_raw:
            self.author_name = author_name_raw.get_text()
            assert isinstance(author_name_raw, bs4.Tag)
            self.author_link = str(author_name_raw.get('href'))
            logger.debug(f'{self.author_name=}, {self.author_link=}')
        else:
            error_message = f'Не могу получить имя автора, и его ссылку в книге {self.book_link}'
            logger.error(error_message)
            raise ParsingException(error_message)

    def _get_book_description(self, book_soup: BeautifulSoup) -> None:
        description_raw = book_soup.find('div', class_="threadmarkListingHeader-extraInfo")
        if description_raw:
            self.book_description = description_raw.get_text().strip()
        else:
            error_message = f'Не могу получить описание книги {self.book_link}'
            logger.error(error_message)
            raise ParsingException(error_message)

    def _get_book_dates(self, book_soup: BeautifulSoup) -> None:
        self._get_book_posted_date(book_soup)
        self._get_book_updated_date()

    def _get_book_posted_date(self, book_soup: BeautifulSoup) -> None:
        posted_date_raw = book_soup.find('div', class_="threadmarkListingHeader-stats")
        error_message = f'Не могу получить дату публикации книги {self.book_link}'
        if posted_date_raw and isinstance(posted_date_raw, bs4.Tag):
            posted_date_raw = posted_date_raw.find('time')
            if posted_date_raw and isinstance(posted_date_raw, bs4.Tag):
                posted_date = posted_date_raw.get('data-time')
                if isinstance(posted_date, str) and posted_date.isdecimal():
                    self.book_posted_date = int(posted_date)
                    logger.debug(f'{self.book_posted_date}')
                else:
                    logger.error(error_message)
                    raise ParsingException(error_message)
            else:
                logger.error(error_message)
                raise ParsingException(error_message)
        else:
            logger.error(error_message)
            raise ParsingException(error_message)

    def _get_book_updated_date(self) -> None:
        try:
            self.book_updated_date = self.chapters_info_list[-1].chapter_posted_date
        except IndexError:
            error_message = f'Не могу получить дату обновления книги {self.book_link}. Нет данных в списке глав'
            logger.exception(error_message)
            raise ParsingException(error_message)

    def _get_book_status(self, book_soup: BeautifulSoup) -> None:
        book_status_raw = book_soup.find('div', class_="threadmarkListingHeader-stats")
        error_message = f'Ошибка получения статуса {self.book_link}'
        if isinstance(book_status_raw, bs4.Tag) and book_status_raw:
            book_status_items = book_status_raw.find_all('dl', class_="pairs pairs--rows")
            if book_status_items:
                try:
                    book_status_raw_block = book_status_items[1]
                    book_status_raw = book_status_raw_block.find('dd')
                    if book_status_raw and isinstance(book_status_raw, bs4.Tag):
                        book_status = book_status_raw.get_text()
                        self._parse_book_status(book_status)
                    else:
                        logger.error(error_message)
                        raise ParsingException(error_message)
                except IndexError:
                    logger.exception(error_message)
                    raise ParsingException(error_message)
            else:
                logger.error(error_message)
                raise ParsingException(error_message)
        else:
            logger.error(error_message)
            raise ParsingException(error_message)

    def _parse_book_status(self, book_status: str) -> None:
        if book_status == 'Ongoing':
            self.book_status = 'In progress'
        elif book_status == 'Complete':
            self.book_status = 'Concluded'
        else:
            error_message = f'Не могу распарсить статус книги {book_status} {self.book_link}'
            logger.error(error_message)
            raise ParsingException(error_message)

    def _get_chapter_soup(self, chapter_link: ChapterInfo, session: Session) -> BeautifulSoup:
        post_id = self._get_post_id(chapter_link)
        chapter_url = self.site_name + chapter_link.chapter_link
        response = session.get(chapter_url)
        if response.status_code == 200:
            chapter_soup_raw = create_soup(response.text)
            chapter_soup = chapter_soup_raw.find('article', {'data-content': post_id})
            if chapter_soup and isinstance(chapter_soup, bs4.Tag):
                chapter_soup = self._clean_soup(chapter_soup)
            else:
                error_message = f'Не могу выделить пост с текстом из общей страницы {chapter_link.chapter_link}'
                logger.error(error_message)
                raise ParsingException(error_message)
            return chapter_soup
        else:
            error_message = f'Не могу получить page sourse главы {chapter_link.chapter_link} в книге {self.book_link}'
            logger.error(error_message)
            raise GetPageSourseException(error_message)

    @staticmethod
    def _get_chapter_text(chapter_soup: BeautifulSoup) -> str:
        chapter_text_raw = chapter_soup.find('div', class_="message-cell message-cell--main")
        if chapter_text_raw and isinstance(chapter_text_raw, bs4.Tag):
            chapter_text = str(chapter_text_raw).strip()
            return chapter_text
        else:
            error_message = f'Ошибка получения текста главы'
            logger.error(error_message)
            raise ParsingException(error_message)

    @staticmethod
    def _clean_soup(chapter_soup: bs4.Tag) -> BeautifulSoup:
        last_edit_block = chapter_soup.find('div', class_="message-lastEdit")
        if last_edit_block and isinstance(last_edit_block, bs4.Tag):
            last_edit_block.decompose()

        message_header = chapter_soup.find('header', class_="message-attribution message-attribution--split")
        if message_header and isinstance(message_header, bs4.Tag):
            message_header.decompose()

        message_footer = chapter_soup.find('footer', class_="message-footer")
        if message_footer and isinstance(message_footer, bs4.Tag):
            message_footer.decompose()

        chapter_soup = create_soup(str(chapter_soup))
        return chapter_soup

    @staticmethod
    def _get_post_id(chapter_link: ChapterInfo) -> str:
        post_id_raw = chapter_link.chapter_link.split('#')
        error_message = f'Не могу получить post id главы {chapter_link.chapter_link}'
        if len(post_id_raw) >= 2:
            post_id = post_id_raw[-1]
            if 'post-' not in post_id:
                logger.error(error_message)
                raise ParsingException(error_message)
            return post_id
        else:
            logger.error(error_message)
            raise GetPageSourseException(error_message)
