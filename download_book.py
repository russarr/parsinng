import clipboard
from common.utils import parse_book_url
from site_parsers.sol.sol_book import SolBook
import logging.config
import logging


from settings.settings import LOGGING_CONFIG

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger('logger')

def main() -> None:
    logger.debug('Начинаем загрузку книги')
    book_url = clipboard.paste()
    site_name, book_link = parse_book_url(book_url)
    book = SolBook(book_link)
    session = book.downoload_book()
    session.close()


if __name__ == '__main__':
    main()
