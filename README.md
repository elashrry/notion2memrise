# About

I am using [Notion](https://www.notion.so/) to create a database of words I want to learn in a foreign language, and I am using [Memrise](https://www.memrise.com/) to learn them through their scientific time-spaced memorization algorithm.
This project is a way to automate the process of creating a course on Memrise from a database on Notion.

# How does it work
### Notion
The database on Notion would look like:

![Notion database](images/database_example.png)

We use their API to query the database. An extra piece of information we get from the API is a unique ID for each cell/page in the database. We will use this ID to link words in the notion database to words on the memrise course.


### TODO:
- [x] get the database via API
- [x] create a pandas dataframe from the database
- [x] clean the dataframe
- [ ] testing modules for the above

### Memrise
Memrise does not offer an API, so I went to the old goody Selenium to control the course. Therefore, this solution won't scale well, but it does the job for me.
### TODO:
Do I work with the levels page or the database page
- [ ] function to create a course on memrise with complex view.
- 

# Requirements
- Python libraries are defined in `environment.yaml`. 
- You will need to define your own variable:
`NOTION_SECRET`, `MEMRISE_EMAIL`, `MEMRISE_PASSWORD` in in the `environment.yaml` file.
- You can create a conda environment with 
```
conda env create -f environment.yaml
``` 
and activate it with 
```
conda activate notion2memrise
``` 

- You will also need a driver for Selenium (e.g. [`geckodriver`](https://firefox-source-docs.mozilla.org/testing/geckodriver/Support.html) for Firefox or [`ChromeDriver`](https://chromedriver.chromium.org/getting-started) for Chrome ). I am using FireFox in this project.

# Testing 
- [ ] write a function to create a testing course on memrise
- [ ] create testing modules to test the code
- [ ] (?) ability to run the testing modules before each edit to the course (because of dependency on selenium and page structure of memrise)

# Limitations
- If you deleted an entry in the notion database, I don't have a way to delete it in the memrise course. You have to do it manually. I could do that by checking cell id from memrise against the ids from notion.

# improvements
- Is it possible to convert these scripts to a Notion integration?