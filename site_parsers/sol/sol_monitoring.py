import time

from site_parsers.sol.sol_request_authorization import create_sol_requests_session
from requests import Session
from bs4 import BeautifulSoup
from common.exceptions import GetPageSourseException, ParsingException
from site_parsers.sol.sol_book import SolBook
from common.utils import create_soup
import pickle
import logging
from typing import Literal
from pathlib import Path
from db_modules.db_common import get_monitoring_authors_list, get_monitoring_stories_list

logger = logging.getLogger(__name__)


def check_sol_updates() -> None:
    logger.debug('Проверяемя страницу обновлений и страницу новых историй')
    session = create_sol_requests_session()
    _check_sol_updates_page(session)
    _check_sol_new_story_page(session)


def _check_sol_updates_page(session: Session) -> None:
    page_soup = _get_upd_new_page_soup(session, 'upd')
    upd_stories_list = _get_upd_stories_download_list(page_soup)
    for book_link in upd_stories_list:
        book = SolBook(book_link)
        book.downoload_sol_book(session)
        time.sleep(3)


def _check_sol_new_story_page(session: Session) -> None:
    page_soup = _get_upd_new_page_soup(session, 'new')
    new_stories_list = get_new_stories_download_list(page_soup)
    for book_link in new_stories_list:
        book = SolBook(book_link)
        book.downoload_sol_book(session)
        time.sleep(3)


def get_new_stories_download_list(page_soup: BeautifulSoup) -> list[str]:
    link_list = _get_new_stories_link_list(page_soup)
    monitoring_list = get_monitoring_authors_list()
    list_to_download = [link[1] for link in link_list if link[0] in monitoring_list]
    return list_to_download


def _get_new_stories_link_list(soup: BeautifulSoup) -> list[tuple[str, str]]:
    new_stories_list = _get_new_links_from_soup(soup)
    old_link_list = _load_old_stories_link_list('new')
    new_link_list = []
    for link in new_stories_list:
        if link not in old_link_list:
            new_link_list.append(link)
        else:
            break
    _save_old_stories_link_list(new_stories_list, 'new')
    return new_link_list


def _get_new_links_from_soup(soup: BeautifulSoup) -> list[tuple[str, str]]:
    all_links = [link.get('href') for link in soup.find_all('a')]
    stories_links = [link for link in all_links if type(link) == str and '/s/' in link]
    author_links = [link for link in all_links if type(link) == str and '/a/' in link]
    if len(author_links) == len(stories_links):
        new_stories_links = zip(author_links, stories_links, strict=True)
    else:
        error_message = 'В списке новых произведений, количество авторов не совпадает с количеством произведений'
        logger.error(error_message)
        raise ParsingException(error_message)
    return list(new_stories_links)


def _get_upd_new_page_soup(session: Session, page_type: Literal['new', 'upd']) -> BeautifulSoup:
    logger.debug('Получаем page_sourse страницы обновлений')
    if page_type == 'new':
        page_address = 'https://storiesonline.net/library/updated_stories.php'
    elif page_type == 'upd':
        page_address = 'https://storiesonline.net/library/updated_stories.php'
    else:
        error_message = f'Неверный тип страницы. Должно new или upd'
        logger.error(error_message)
        raise GetPageSourseException(error_message)
    response = session.get(page_address)
    if response.status_code == 200:
        page_soup = create_soup(response.text)
        return page_soup
    else:
        error_message = f'Ошибка получения page sourse страницы с обновлениями книг'
        logger.error(error_message)
        raise GetPageSourseException(error_message)


def _get_upd_stories_download_list(page_soup: BeautifulSoup) -> tuple[str, ...]:
    link_list = _get_updates_stories_link_list(page_soup)
    monitoring_list = get_monitoring_stories_list()
    list_to_download = tuple(link for link in link_list if link in monitoring_list)
    return list_to_download


def _get_updates_stories_link_list(page_soup: BeautifulSoup) -> list[str]:
    updated_stories_list = _get_upd_links_from_soup(page_soup)
    old_link_list = _load_old_stories_link_list('upd')
    updated_link_list = []
    for link in updated_stories_list:
        if link not in old_link_list:
            updated_link_list.append(link)
        else:
            break
    _save_old_stories_link_list(updated_stories_list, 'upd')
    return updated_link_list


def _get_upd_links_from_soup(page_soup: BeautifulSoup) -> list[str]:
    all_links = [link.get('href') for link in page_soup.find_all('a')]
    updated_stories_list = [link for link in all_links if type(link) == str and '/s/' in link]
    return updated_stories_list


def _load_old_stories_link_list(stories_list_type: Literal['upd', 'new']) -> list[str]:
    logger.debug('Читаем список ссылок с диска')
    if stories_list_type == 'upd':
        file_path = Path('temp/updated_stories_link_list.pickle')
    elif stories_list_type == 'new':
        file_path = Path('temp/new_stories_link_list.pickle')
    else:
        error_message = 'Неверно указан тип: new или upd'
        logger.error(error_message)
        raise GetPageSourseException(error_message)

    if file_path.exists():
        with open(file_path, 'rb') as file:
            link_list = pickle.load(file)
    else:
        link_list = []
    return link_list


def _save_old_stories_link_list(link_list: list[str] | list[tuple[str, str]], stories_list_type: Literal['upd', 'new']) -> None:
    logger.debug('сохраняем список ссылкок на диск')
    if stories_list_type == 'upd':
        file_path = Path('temp/updated_stories_link_list.pickle')
    elif stories_list_type == 'new':
        file_path = Path('temp/new_stories_link_list.pickle')
    else:
        error_message = 'Неверно указан тип: new или upd'
        logger.error(error_message)
        raise GetPageSourseException(error_message)

    if Path('temp').exists():
        with open(file_path, 'wb') as file:
            pickle.dump(link_list, file)
    else:
        error_message = 'Отсутсвует папка temp'
        logger.error(error_message)
        raise GetPageSourseException(error_message)
