from selenium import webdriver
from typing import Literal
from pathlib import Path


def get_driver(mode: Literal['browser', 'no_browser'] = 'browser'):
    geckodriver_path = Path('selenium_modules/geckodriver.exe')
    log_path = Path('temp/logs/geckodriver.log')
    print(log_path)
    options = webdriver.FirefoxOptions()
    # user-agent
    user_agent = "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:84.0) Gecko/20100101 Firefox/84.0"
    options.set_preference("general.useragent.override", user_agent)
    # отключаем статус webdriver(чтобы не палиться)... почему то не работает
    options.set_preference("dom.webdriver.enabled", False)
    # headless mode
    if mode == 'browser':
        options.headless = False
    elif mode == 'no_browser':
        options.headless = True
    driver = webdriver.Firefox(options=options, executable_path=geckodriver_path, service_log_path=log_path)
    return driver
