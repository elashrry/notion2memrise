"""constants for the memrise modules"""
FIREFOX_PATH = "/opt/homebrew/bin/geckodriver"
TIMEOUT_LIMIT = 10  # in seconds
WORD_SEARCH_TIME_OUT = 5  # in seconds
LOGIN_URL = "https://app.memrise.com/signin"
EMAIL_ID = "username"
PASSWORD_ID = "password"
SUBMIT_XPATH = "//button[@type='submit']"
YES_BTN_CLASS = "btn btn-primary btn-yes"
SAVE_CHANGES_CLASS = "btn btn-success"
MODAL_BACKDROP_CLASS = "modal-backdrop fade"
YES_NO_MODAL_ID = "modal-yesno"
UPDATE_CELL_JAVA_SCRIPT = """arguments[0].value = arguments[1];arguments[0].blur();"""
