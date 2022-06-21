import pickle
import time
from os import getenv
# from selenium_general import get_driver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, InvalidCookieDomainException
from selenium.webdriver.firefox.webdriver import WebDriver
from common.exceptions import GetPageSourseException  # type: ignore
from dotenv import load_dotenv
from pathlib import Path
import logging

logger = logging.getLogger('logger')


def sol_auth(driver: WebDriver) -> WebDriver:
    logger.debug('авторизуемся на sol через selenuim')
    driver.get('https://storiesonline.net')
    driver = _load_cookies(driver)
    driver = _fill_sol_auth_form(driver)
    _save_cookies(driver)
    return driver


def _load_cookies(driver: WebDriver) -> WebDriver:
    """функция для загрузки cookies с диска"""
    logger.debug('загружаем sol cookies')
    try:
        with open('temp/cookies.pickle', 'rb') as f:
            for cookie in pickle.load(f):
                driver.add_cookie(cookie)
            driver.refresh()
            return driver
    except (InvalidCookieDomainException, FileNotFoundError, EOFError):
        logger.exception('Проблема с загрузкой cookies')
        return driver


def _fill_sol_auth_form(driver: WebDriver) -> WebDriver:
    """функция заполняет данные авторизации и логинится на storiesonline.com"""
    logger.debug('авторизуемся на sol')
    try:
        driver.find_element(By.XPATH, '//a[@href="https://storiesonline.net/sol-secure/user/my_account.php"]')
        return driver
    except NoSuchElementException:
        login, password = _load_auth_data()
        try:
            driver.find_element(By.LINK_TEXT, "Log-in").click()
            driver.find_element(By.NAME, "email").clear()
            driver.find_element(By.NAME, "email").send_keys(login)
            driver.find_element(By.NAME, "password").clear()
            driver.find_element(By.NAME, "password").send_keys(password)
            driver.find_element(By.NAME, "password").send_keys(Keys.ENTER)
            time.sleep(3)
            driver.find_element(By.XPATH, '//a[@href="https://storiesonline.net/sol-secure/user/my_account.php"]')
            return driver

        except NoSuchElementException:
            logger.exception('Проблемы с авторизацией на sol')
            raise GetPageSourseException('Проблемы с авторизацией на storiesonline.com')


def _save_cookies(driver: WebDriver) -> None:
    """ сохраняем cookies, чтобы потом не логинится"""
    logger.debug('сохраняем cookies на диск')
    with open('temp/cookies.pickle', 'wb') as file:
        pickle.dump(driver.get_cookies(), file)


def _load_auth_data():
    """функция загружает данные из переменных окружения"""
    logger.debug('берем данные для авторизации из переменных окружения')
    dotenv_path = Path('utils/.env')
    load_dotenv(dotenv_path=dotenv_path)
    login = getenv('SOL_LOGIN')
    password = getenv('SOL_PASSWORD')
    if not any([login, password]):
        logger.error('не могу загрузить данные для авторизации из переменных окружения')
        raise GetPageSourseException('не могу загрузить данные для авторизации из переменных окружения')
    return login, password

# if __name__ == '__main__':
#     driver = get_driver('browser')
#     sol_auth(driver)
