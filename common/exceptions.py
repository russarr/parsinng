class GetPageSourseException(Exception):
    """Ошибка получения исходного кода страницы"""


class DataBaseExceptions(Exception):
    """Ошибки базы данных"""


class ParsingException(Exception):
    """Ошибка парсинга книги"""


class CompileException(Exception):
    """Ошибка компиляции книги в файл"""
