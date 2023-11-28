from src import notion
from src import memrise as mem
from src import handlers as h
from src import constants as const

if __name__ == "__main__":
    print("Notion2Memrise started")
    notion_df = notion.get_data_from_notion(const.NOTION_DATABASE_ID)
    driver = mem.create_driver()
    driver = mem.sign_in(driver, const.MEMRISE_EMAIL, const.MEMRISE_PASSWORD)
    driver = mem.agree_to_cookies(driver)
    driver = h.notion2memrise(
        driver,
        notion_df,
        const.COURSE_EDIT_URL,
        const.COURSE_DB_URL,
        const.DB_NAME,
        const.LEVEL_WORD_LIMIT,
        )
