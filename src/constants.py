"""Constants to be used throughout the project."""

import os

# order of the columns to be inserted into Memrise in case I changed them on Notion
# first column to be prompt on, and second column to be tested on
COL_LIST = [
    "French",
    "English",
    "Définition",
    "Example",
    "Example Translation",
    "Part of Speech",
    "Gender",
    "Tags",
    "Model",
    "date modified",
    "cell id",
]
MEMRISE_EMAIL = os.environ.get("MEMRISE_EMAIL")
MEMRISE_PASSWORD = os.environ.get("MEMRISE_PASSWORD")
# ? can I get the ID using Notion integration?
NOTION_DATABASE_ID = "7c83b2ef86e941b986e8c8461fb5134d"