import logging
from common.exceptions import GetPageSourseException  # type: ignore
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

logger = logging.getLogger('logger')


@dataclass
class ChapterInfo:
    chapter_file_name: str = ''
    chapter_link: str = ''
    chapter_name: str = ''
    book_link: str = ''
    chapter_updated_date: int = field(default=0, compare=False)
    chapter_posted_date: int = field(default=0, compare=False)
    chapter_size: int = field(default=0, compare=False)


@dataclass()
class BookInfo:
    book_link: str
    site_name: Literal['https://forums.sufficientvelocity.com', 'https://forums.spacebattles.com', 'https://storiesonline.net'] = field(init=False)
    book_title: str = ''
    author_name: str = ''
    author_link: str = ''
    book_directory: Path = field(repr=False, init=False)
    book_size: int = field(default=0)
    book_score: float = 0.0
    chapters_info_list: list[ChapterInfo] = field(default_factory=list)
    book_sex_content: str = ''
    book_posted_date: int = 0
    book_updated_date: int = 0
    book_download_date: int = 0
    book_description: str = ''
    book_genre: str = ''
    book_series: str = field(default='')
    book_tags: tuple[str, ...] = field(default_factory=tuple)
    book_series_order_position: int = 0
    book_votes_count: int = 0
    book_status: Literal['In progress', 'Concluded', 'Frozen', 'Unknown'] = field(repr=False, default='Unknown')
    book_monitoring_status: bool = False
