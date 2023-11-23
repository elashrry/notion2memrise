import pandas as pd 
import numpy as np
import pytest
from pandas.testing import assert_frame_equal

from src import handlers as hr
from src import memrise as mem
from src.constants import MEMRISE_EMAIL, MEMRISE_PASSWORD

mem.COURSE_EDIT_URL = "https://app.memrise.com/course/6515074/testing/edit/"
mem.COURSE_DB_URL = "https://app.memrise.com/course/6515074/testing/edit/database/7570903/"  # noqa: E501


def read_data():
    df = pd.read_csv("tests/data/test.csv")
    df["date modified"] = pd.to_datetime(df["date modified"])
    return df

@pytest.fixture
def driver():
    driver = mem.create_driver()
    driver = mem.sign_in(driver, MEMRISE_EMAIL, MEMRISE_PASSWORD)
    driver = mem.agree_to_cookies(driver)
    driver, deleted_df = mem.delete_words(driver, "ALL")
    yield driver

    driver, deleted_df = mem.delete_words(driver, "ALL")
    driver.quit()

def test_handle_new_from_notion(driver):
    df = read_data()
    driver, added_res_df = hr.handle_new_from_notion(driver, df)

    driver, memrise_df = mem.get_all_words(driver)
    memrise_df = memrise_df.sort_values(by="cell id").reset_index(drop=True)
    df_valid = mem.validate_input(df)
    df_valid = df_valid.sort_values(by="cell id").reset_index(drop=True)
    assert_frame_equal(memrise_df, df_valid)

def test_handle_updated_from_notion(driver):
    df = read_data()
    # dtypes will be all Object if you use a single row
    to_update_idx = np.random.choice(df.index, size=2, replace=False)
    # add it to memrise
    to_add_df = df.loc[to_update_idx].copy()
    driver, added_res_df = hr.handle_new_from_notion(driver, to_add_df)
    # update it in df 
    df.loc[to_update_idx, "French"] = "updated-" + df.loc[
        to_update_idx, "French"]
    # add again to memrise
    updated_df = df.loc[to_update_idx].copy()
    driver, update_res_df = hr.handle_updated_from_notion(driver, updated_df)
    
    # test 
    expected_update_res_df = pd.DataFrame({
        "French": updated_df["French"].to_list(),
        "cell id": updated_df["cell id"].to_list(),
        "action": "update",
        "success": True,
        "error": np.nan
    })
    assert_frame_equal(expected_update_res_df, update_res_df)

    # check the words in the course 
    driver, memrise_df = mem.get_all_words(driver)
    memrise_df = memrise_df.sort_values(by="cell id").reset_index(drop=True)
    # make sure the input dtypes and column order are correct
    updated_df_valid = mem.validate_input(updated_df)
    columns_with_all_na = updated_df_valid.columns[updated_df_valid.isna().all()]
    updated_df_valid = updated_df_valid.astype(
        {col: np.float64 for col in columns_with_all_na})

    updated_df_valid = updated_df_valid.sort_values(by="cell id").reset_index(drop=True)
    assert_frame_equal(memrise_df, updated_df_valid)

def test_notion2memrise(driver):
    df = read_data()
    most_recent = df["date modified"].max()
    driver = mem.create_driver()
    driver = mem.sign_in(driver, MEMRISE_EMAIL, MEMRISE_PASSWORD)
    driver = mem.agree_to_cookies(driver)

    to_del_idx, to_update_idx = np.random.choice(df.index, 2, replace=False)
    # add them to memrise
    # update their modified date to something very old
    df.loc[[to_del_idx, to_update_idx], "date modified"] = pd.to_datetime(
        "2000-01-01", utc=True)

    to_add_df = df.loc[[to_del_idx, to_update_idx]].copy()
    driver, added_res_df = hr.handle_new_from_notion(driver, to_add_df)

    # delete one from df
    df = df.drop(index=[to_del_idx])
    # update one from df and its date
    df.loc[to_update_idx, "French"] = "updated-" + df.loc[
        to_update_idx, "French"]
    df.loc[to_update_idx, "date modified"] = most_recent
    driver = hr.notion2memrise(driver, df)

    driver, memrise_df = mem.get_all_words(driver)
    memrise_df = memrise_df.sort_values(by="cell id").reset_index(drop=True)

    df_valid = mem.validate_input(df)
    df_valid = df_valid.sort_values(by="cell id").reset_index(drop=True)

    assert_frame_equal(memrise_df, df_valid)