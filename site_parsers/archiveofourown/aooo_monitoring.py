import logging
import time

from tqdm import tqdm

from common.request_authorization import create_auth_session
from db_modules.db_common import get_monitoring_stories_list
from site_parsers.archiveofourown.aooo import AoooBook

logger = logging.getLogger(__name__)


def check_aooo_updates() -> None:
    session = create_auth_session(site_alias='aooo')
    monitoring_list = get_monitoring_stories_list('aooo')
    logger.debug(f'{monitoring_list=}')
    for book_url_data in tqdm(monitoring_list, desc='Обход списка монитринга aooo', colour='green'):
        book = AoooBook(*book_url_data)
        book.downoload_book(session)
        time.sleep(1)
    session.close()
