import random
import time

from site_parsers.sol.sol_request_authorization import SolBookRequests  # type: ignore
from common.common import BookInfo  # type: ignore
from bs4 import BeautifulSoup, Tag, NavigableString
from requests import Session
import logging
from common.utils import create_soup  # type: ignore
from common.exceptions import ParsingException  # type: ignore

logger = logging.getLogger(__name__)


class SolRequestsSoup(SolBookRequests, BookInfo):
    def get_book_soup(self, session: Session) -> BeautifulSoup:
        logger.debug('Получаем book_soup')
        book_url = self.site_name + self.book_link
        reponse = session.get(book_url)
        book_soup = create_soup(reponse.text)
        return book_soup

    def get_chapter_soup(self, chapter_link: str, session: Session) -> BeautifulSoup:
        chapter_url = self.site_name + chapter_link
        response = session.get(chapter_url)
        chapter_soup_1 = create_soup(response.text.strip())
        chapter_soup_full = self._get_chapter_content_2(session, chapter_soup_1)
        return chapter_soup_full

    def _get_chapter_content_2(self, session: Session, chapter_soup_1: BeautifulSoup) -> BeautifulSoup:
        bot_protection_block = chapter_soup_1.find('div', id="sr")
        if bot_protection_block:
            logger.debug('Есть защита от ботов')
            chapter_soup_full = self._bypass_bot_protection(session, chapter_soup_1)
            return chapter_soup_full
        else:
            logger.info('Глава короткая, без защиты')
            return chapter_soup_1

    def _bypass_bot_protection(self, session: Session, chapter_soup_1: BeautifulSoup) -> BeautifulSoup:
        data_1 = self._get_requests_data_1(chapter_soup_1)
        response = session.post('https://storiesonline.net' + '/res/responders/tl.php', data=data_1)
        if response.status_code == 200 and len(response.text) > 10:
            data_2 = self._get_requests_data_2(response.text)
            time.sleep(random.randint(1, 3))
            response = session.post('https://storiesonline.net' + '/res/responders/tl.php', data=data_2)
            logger.debug('Обошли первый шаг защиты')
            if response.status_code == 200 and len(response.text) > 100:
                logger.debug('Обошли второй шаг защиты')
                chapter_soup_2 = create_soup('\n' + response.text.strip()).find()
                tag = chapter_soup_1.find('div', id="sr")
                if tag:
                    tag.replace_with(chapter_soup_2)
                logger.debug('добавили скрытую часть текста')
                return chapter_soup_1
            else:
                error_message = f'Ошибка получения второй части токена {response.status_code=}, {len(response.text)}'
                logger.error(error_message)
                raise ParsingException(error_message)
        else:
            error_message = f'Ошибка получения второй части токена {response.status_code=}, {len(response.text)}'
            logger.error(error_message)
            raise ParsingException(error_message)

    def _get_requests_data_1(self, chapter_soup: BeautifulSoup) -> list[tuple[str, str]]:
        logger.debug('Получаем блок данных с токеном')
        temp_data = chapter_soup.find('script')
        if temp_data:
            raw_data = self._extract_data_1(temp_data)
            data = [('cmd', "gt")] + [('data[]', i) for i in raw_data]
            logger.debug(f'Токен {data=}')
            return data
        else:
            error_message = f'Ошибка получения блока данных с токеном главы книги'
            logger.error(error_message)
            raise ParsingException(error_message)

    @staticmethod
    def _get_requests_data_2(response_text: str) -> list[tuple[str, str]]:
        token_2 = response_text
        return [('cmd', "gr"), ('data[]', token_2)]

    @staticmethod
    def _extract_data_1(temp_data: Tag | NavigableString) -> tuple[str, str, str, str, str]:
        logger.debug('извлекаем токен')
        split_data = str(temp_data).split(';')
        tto, story_id, pid, ci = '', '', '', ''
        if len(split_data) > 1:
            for line in split_data:
                clean_line: str = line.strip()
                if clean_line.startswith('var tto='):
                    tto = clean_line.strip().replace('var tto=', '').strip("'")
                elif clean_line.startswith('var story_id='):
                    story_id = clean_line.strip().replace('var story_id=', '').strip()
                elif clean_line.startswith('var pid='):
                    pid = clean_line.strip().replace('var pid=', '').strip()
                elif clean_line.startswith('var ci='):
                    ci = clean_line.strip().replace('var ci=', '').strip("'")
            if all([tto, story_id, pid, ci]):
                return story_id, pid, ci, "undefined", tto
            else:
                error_message = f'Ошибка получения токена главы книги'
                logger.error(error_message)
                raise ParsingException(error_message)
        else:
            error_message = f'Ошибка получения токена главы книги'
            logger.error(error_message)
            raise ParsingException(error_message)
