import logging.config
from datetime import datetime

import schedule

from settings.settings import LOGGING_CONFIG
from site_parsers.archiveofourown.aooo_monitoring import check_aooo_updates
from site_parsers.ficbook.ficbook_monitoring import check_ficbook_updates
from site_parsers.sfsb.sf_sb_monitoring import check_sf_sb_updates
from site_parsers.sol.sol_monitoring import check_sol_updates
from site_parsers.wormstorysearch.wormstorysearch import check_wormstorysearch

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)
logging.captureWarnings(True)


def main() -> None:
    print(datetime.now().strftime("%H:%M"))
    print('Проверяем storiesonline')
    check_sol_updates()
    print('Проверяем sf_sb')
    check_sf_sb_updates()
    print('Проверяем wormstorysearch.com')
    check_wormstorysearch()
    print('проверяем ficbook_com')
    check_ficbook_updates()
    print('проверяем archiveofourown.org')
    check_aooo_updates()
    print('Конец цикла\n', '*'*30, '\n')



if __name__ == '__main__':
    main()
    schedule.every().hour.do(main)
    while True:
        schedule.run_pending()
