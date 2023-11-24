from src import notion
from src import memrise as mem
from src import handlers as h
from src.constants import NOTION_DATABASE_ID, MEMRISE_EMAIL, MEMRISE_PASSWORD

if __name__ == "__main__":
    print("Notion2Memrise started")
    notion_df = notion.get_data_from_notion(NOTION_DATABASE_ID)
    driver = mem.create_driver()
    driver = mem.sign_in(driver, MEMRISE_EMAIL, MEMRISE_PASSWORD)
    driver = mem.agree_to_cookies(driver)
    driver = h.notion2memrise(driver, notion_df)
