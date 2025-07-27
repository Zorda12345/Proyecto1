from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time

options = Options()
service = Service()
driver = webdriver.Chrome(service=service, options=options)
driver.get("https://www.amazon.es")
time.sleep(5)
driver.quit()
