"""Constants to be used throughout the project."""

import os

NOTION_DATABASE_ID = "7c83b2ef86e941b986e8c8461fb5134d"
# order of the columns to be inserted into Memrise in case I changed them on Notion
# first column to be prompt on, and second column to be tested on
COL_LIST = [
    "French",  # used in the code, I will try to avoid it
    "English",
    "Définition",
    "Example",
    "Example Translation",
    "cell id",  # don't change, used in the code
    "Part of Speech",
    "Gender",
    "Tags",
    "Model",
    "date modified",  # don't change, used in the code
]
# columns that should not have nas
NOT_NULL_COL_LIST = ["French", "English", "date modified", "cell id"]
COURSE_EDIT_URL = "https://app.memrise.com/course/6512551/my-french-2/edit/"
COURSE_DB_URL = "https://app.memrise.com/course/6512551/my-french-2/edit/database/7568262/"  # noqa: E501
LEVEL_WORD_LIMIT = 20
DB_NAME = "French"
MEMRISE_EMAIL = os.environ.get("MEMRISE_EMAIL")
MEMRISE_PASSWORD = os.environ.get("MEMRISE_PASSWORD")
# ? can I get the ID using Notion integration?
