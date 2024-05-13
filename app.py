from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
import json
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
import time

# Initialize Flask app
app = Flask(__name__)

# Initialize Line Bot API
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# Define function to scrape data and save it to a JSON file
def scrape_and_save_data():
    options = webdriver.ChromeOptions()
    service = ChromeService(executable_path="chromedriver.exe")
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get("https://www.ccpa.org.tw/tica/data_more.php?pid=334574&tpl=")
        time.sleep(3)

        container_elements = driver.find_elements(By.CLASS_NAME, "container")
        anime_data = []
        for container_element in container_elements:
            w_black_elements = container_element.find_elements(By.CLASS_NAME, "w_black")
            for w_black_element in w_black_elements:
                title = w_black_element.text
                link_url = w_black_element.get_attribute("href")
                anime_data.append({"title": title, "link": link_url})

        with open('anime_data.json', 'w') as file:
            json.dump(anime_data, file)

    except Exception as e:
        print("Error:", str(e))
    finally:
        driver.quit()

# Listen for POST requests from /callback
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# Handle message events
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    message_text = event.message.text
    if message_text == "/爬取動畫":
        # Call the scraping function to scrape anime data and save it
        scrape_and_save_data()
        # Read the scraped data from the JSON file
        with open('anime_data.json', 'r') as file:
            anime_data = json.load(file)
        # Build reply message text
        reply_text = ""
        for anime in anime_data:
            reply_text += f"{anime['title']} - {anime['link']}\n"
        # Reply to the user with scraped anime data
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )

# Main program entry point
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
