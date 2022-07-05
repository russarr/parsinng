import logging.config
from datetime import datetime

import schedule

from common.exceptions import *
from settings.settings import LOGGING_CONFIG
from site_parsers.archiveofourown.aooo_monitoring import check_aooo_updates
from site_parsers.ficbook.ficbook_monitoring import check_ficbook_updates
from site_parsers.sfsb.sf_sb_monitoring import check_sf_sb_updates
from site_parsers.sol.sol_monitoring import check_sol_updates
from site_parsers.wormstorysearch.wormstorysearch import check_wormstorysearch
from site_parsers.youtube.youtube import check_youtube_rss

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)
logging.captureWarnings(True)


def main() -> None:
    try:
        print(datetime.now().strftime("%H:%M"))
        print('Проверяем storiesonline')
        check_sol_updates()
        print('-' * 20)
        print('Проверяем sf_sb')
        check_sf_sb_updates()
        print('-' * 20)
        print('Проверяем wormstorysearch.com')
        check_wormstorysearch()
        print('-' * 20)
        print('проверяем ficbook_com')
        check_ficbook_updates()
        print('-' * 20)
        print('проверяем archiveofourown.org')
        check_aooo_updates()
        print('-' * 20)
        print('Проверяем youtube')
        check_youtube_rss()
        print('Конец цикла\n', '*' * 30, '\n')
    except (GetPageSourseException, DataBaseExceptions, ParsingException, CompileException):
        logger.exception('Ошибка запланированная')
    except:
        logger.exception('Незапланированная ошибка')


if __name__ == '__main__':
    main()
    schedule.every().hour.do(main)
    while True:
        schedule.run_pending()
