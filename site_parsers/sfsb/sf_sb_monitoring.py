import logging
import time

from tqdm import tqdm

from common.request_authorization import create_auth_session
from db_modules.db_common import get_monitoring_stories_list
from site_parsers.sfsb.sf_sb_book import SfSbBook

logger = logging.getLogger(__name__)


def check_sf_sb_updates() -> None:
    session = create_auth_session(site_alias='sf_sb')
    monitoring_list = get_monitoring_stories_list('sf_sb')
    logger.debug(f'{monitoring_list=}')
    for book_url_data in tqdm(monitoring_list, desc='Обход списка мониторинга sf_sb', colour='green'):
        book = SfSbBook(*book_url_data)
        book.downoload_book(session)
        time.sleep(1)
    session.close()
