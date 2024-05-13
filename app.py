from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *

# 匯入你的爬蟲程式碼
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
import time

# 初始化 Flask 應用
app = Flask(__name__)

# 初始化 Line Bot API
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# 爬取指定網頁的函數
def scrape_website():
    options = webdriver.ChromeOptions()
    service = ChromeService(executable_path="chromedriver.exe")
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get("https://www.ccpa.org.tw/tica/data_more.php?pid=334574&tpl=")
        time.sleep(3)

        container_elements = driver.find_elements(By.CLASS_NAME, "container")
        scraped_content = "最新消息:\n"
        for container_element in container_elements:
            w_black_elements = container_element.find_elements(By.CLASS_NAME, "w_black")
            for w_black_element in w_black_elements:
                link_text = w_black_element.text
                link_url = w_black_element.get_attribute("href")
                hyperlink = f"<a href='{link_url}'>{link_text}</a>"
                scraped_content += hyperlink + "\n"
        return scraped_content
    except Exception as e:
        return "爬蟲出現錯誤: " + str(e)
    finally:
        driver.close()

# 監聽所有來自 /callback 的 Post Request
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

# 收到訊息事件時的處理
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    message_text = event.message.text
    if message_text == "/爬取":
        # 呼叫爬蟲函數爬取網頁內容
        scraped_content = scrape_website()
        # 將爬取到的內容回傳給使用者
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=scraped_content)
        )

# 主程式入口
import os
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
