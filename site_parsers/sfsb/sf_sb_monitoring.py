from db_modules.db_common import get_sf_sb_monitoring_stories_list
from site_parsers.sfsb.sf_sb_book import SfSbBook
import logging
from common.request_authorization import create_request_session
from tqdm import tqdm
import time

logger = logging.getLogger(__name__)


def check_sf_sb_updates() -> None:
    session = create_request_session()
    monitoring_list = get_sf_sb_monitoring_stories_list()
    logger.debug(f'{monitoring_list=}')
    for book_url_data in tqdm(monitoring_list):
        book = SfSbBook(*book_url_data)
        book.downoload_book(session)
        time.sleep(1)
    session.close()
