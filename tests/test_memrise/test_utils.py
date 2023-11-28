import pandas as pd
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.constants import MEMRISE_EMAIL, MEMRISE_PASSWORD
from src.memrise.constants import FIREFOX_PATH, TIMEOUT_LIMIT
from src.memrise import utils as ut
from tests.constants import COURSE_EDIT_URL, DB_NAME

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
    assert isinstance(ut.create_driver(), webdriver.Firefox)

def test_sign_in(driver):
    driver = ut.sign_in(driver, MEMRISE_EMAIL, MEMRISE_PASSWORD)
    # wait  login in. i.e. a button with title "Your account"
    WebDriverWait(driver, TIMEOUT_LIMIT).until(
        EC.presence_of_element_located(
            (By.XPATH, '//button[@title="Your account"]')))
    assert True

def test_create_new_level(driver):
    driver = ut.sign_in(driver, MEMRISE_EMAIL, MEMRISE_PASSWORD)
    driver.get(COURSE_EDIT_URL)  # Replace with the actual edit page URL
    driver = ut.create_new_level(driver, DB_NAME)
    # Verify: check that a new level was created
    new_level = WebDriverWait(driver, TIMEOUT_LIMIT).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[@class='level']")))
    assert new_level is not None
