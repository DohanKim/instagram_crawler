import time
import re
import os

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from google.cloud import language
from google.cloud.language import enums
from google.cloud.language import types

import pymongo

driver_path = "/Users/dohan/Downloads/chromedriver"
driver = webdriver.Chrome(driver_path)

client = pymongo.MongoClient('localhost', 27017)
db = client.instagram_crawler

json_key_path = "/Users/dohan/instagram crawler-a2991ea6950e.json"

driver.implicitly_wait(5)
driver.get("https://www.instagram.com/accounts/login/")
driver.find_elements_by_name("username")[0].send_keys("hodoli__")
driver.find_elements_by_name("password")[0].send_keys(os.environ['passwd'])
driver.find_element_by_xpath("//*[@id='react-root']/section/main/div/article/div/div[1]/div/form/div[4]/button").submit()
WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'KL4Bh')))

driver.get("https://www.instagram.com/foodyinkorea/")

total_count = driver.find_element_by_class_name('g47SY').text
print("total: ", total_count)

body = driver.find_element_by_tag_name("body")
alt_list = []

for i in range(2):
    body.send_keys(Keys.END)
    time.sleep(0.2)

WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div.kIKUG > a")))
first_post = driver.find_element_by_css_selector('div.kIKUG')
anchor = first_post.find_element_by_tag_name('a')
driver.execute_script("arguments[0].click();", anchor)

meta_data_pattern = re.compile("[\U0001f004-\U0001f6c5][ \t]*([^\U0001f004-\U0001f6c5\n]+)")
price_pattern = re.compile("[0-9|,]+[ \t]*원")
time_pattern = re.compile("\d+:\d+[ \t]*-[ \t]*\d+:\d+")

while True:
    print("=" * 20)
    WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.C4VMK > span')))
    text_span = driver.find_element_by_css_selector('div.C4VMK > span')

    meta_data = meta_data_pattern.findall(text_span.text)

    if len(meta_data) > 0:
        name = meta_data[0] if len(meta_data[0]) < 80 or len(meta_data) == 1 else meta_data[1]
        price = ""
        worktime = ""
        image = ""

        try:
            driver.execute_script("window.open('" + driver.current_url + "','_blank');");
            tabs = driver.window_handles
            driver.switch_to.window(tabs[1])
            time.sleep(1)
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'img.FFVAD')))
            image = driver.find_element_by_css_selector('img.FFVAD').get_attribute('src')
            driver.close()
            driver.switch_to.window(tabs[0])
        except Exception as e:
            print(name)
            print("Image extract error")
            print(e)

        for meta_datum in meta_data:
            if price_pattern.search(meta_datum) != None:
                price = meta_datum
            elif time_pattern.search(meta_datum) != None:
                worktime = meta_datum

        # Instantiates a client
        client = language.LanguageServiceClient.from_service_account_json(json_key_path)

        # The text to analyze
        document = types.Document(
            content=text_span.text,
            type=enums.Document.Type.PLAIN_TEXT)

        address = ""
        phone_number = ""
        entities = client.analyze_entities(document=document).entities
        for entity in entities:
            entity_type = enums.Entity.Type(entity.type)
            if entity_type.name == 'ADDRESS':
                address = entity.name
            elif entity_type.name == 'PHONE_NUMBER':
                phone_number = entity.name

        print("name: ", name)
        print("time: ", worktime)
        print("price: ", price)
        print("address: ", address)
        print("phone: ", phone_number)
        print("image: ", image)

        existing_restaurant = db.restaurants.find_one({'name': name})
        if existing_restaurant == None:
            db.restaurants.insert_one(
                {'name': name,
                 'image': image,
                 'time': worktime,
                 'price': price,
                 'address': address,
                 'phone': phone_number,
                 'description': text_span.text})
        else:
            db.restaurants.update_one({'_id': existing_restaurant['_id']}, {"$set": {'image': image}})
            print("updated image only")

    else:
        print(text_span.text)
        print("No meta data")

    next = driver.find_element_by_css_selector('a.coreSpriteRightPaginationArrow')
    if next:
        next.click()
    else:
        break

driver.close()
