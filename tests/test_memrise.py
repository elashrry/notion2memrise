import pandas as pd

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src import memrise as mem
from src.constants import MEMRISE_EMAIL, MEMRISE_PASSWORD

mem.COURSE_EDIT_URL = "https://app.memrise.com/course/6515074/testing/edit/"
mem.COURSE_DB_URL = "https://app.memrise.com/course/6515074/testing/edit/database/7570903/"  # noqa: E501

FIREFOX_PATH = "/opt/homebrew/bin/geckodriver"
TIMEOUT_LIMIT = 5  # in seconds
WORD_SEARCH_TIME_OUT = 0.01  # in seconds



@pytest.fixture
def driver():
    options = Options()
    options.headless = True
    driver = webdriver.Firefox(executable_path=FIREFOX_PATH, options=options)
    yield driver
    driver.quit()

def read_data():
    df = pd.read_csv("tests/data/test.csv")
    df["date modified"] = pd.to_datetime(df["date modified"])
    return df

def test_create_driver():
    assert isinstance(mem.create_driver(), webdriver.Firefox)

def test_sign_in(driver):
    driver = mem.sign_in(driver, MEMRISE_EMAIL, MEMRISE_PASSWORD)
    # wait  login in. i.e. a button with title "Your account"
    WebDriverWait(driver, TIMEOUT_LIMIT).until(
        EC.presence_of_element_located(
            (By.XPATH, '//button[@title="Your account"]')))
    assert True

def test_create_new_level(driver):
    driver = mem.sign_in(driver, MEMRISE_EMAIL, MEMRISE_PASSWORD)
    driver.get(mem.COURSE_EDIT_URL)  # Replace with the actual edit page URL
    driver = mem.create_new_level(driver)
    # Verify: check that a new level was created
    new_level = WebDriverWait(driver, TIMEOUT_LIMIT).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[@class='level']")))
    assert new_level is not None
