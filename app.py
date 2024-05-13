from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
import time
import os

app = Flask(__name__)
static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# 創建 Chrome Webdriver

def crawl_exhibition_data(category):
    options = webdriver.ChromeOptions()
    service = ChromeService(executable_path="chromedriver.exe")
    driver = webdriver.Chrome(service=service, options=options)
    try:
        driver.get("https://www.ccpa.org.tw/tica/data_more.php?pid=334574&tpl=")
        time.sleep(3)

        container_elements = driver.find_elements(By.CLASS_NAME, "container")
        exhibition_data = []
        for container_element in container_elements:
            w_black_elements = container_element.find_elements(By.CLASS_NAME, "w_black")
            for w_black_element in w_black_elements:
                link_text = w_black_element.text
                link_url = w_black_element.get_attribute("href")
                exhibition_data.append(f"<a href='{link_url}'>{link_text}</a>")
        return exhibition_data
    except Exception as e:
        print("發生錯誤:", str(e))
        return []

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

@handler.add(PostbackEvent)
def handle_postback(event):
    user_id = event.source.user_id
    if event.postback.data == "ACG_EXHIBITION":
        buttons_template_message = TemplateSendMessage(
            alt_text='ACG展覽選單',
            template=ButtonsTemplate(
                title='ACG展覽資訊',
                text='請選擇類別',
                actions=[
                    PostbackAction(label='A動漫', data='ANIME_EXHIBITION'),
                    PostbackAction(label='C漫畫', data='COMIC_EXHIBITION'),
                    PostbackAction(label='G電玩', data='GAME_EXHIBITION'),
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons_template_message)
    elif event.postback.data == "ANIME_EXHIBITION":  # 添加對"A動漫"按鈕的處理
        category = "A"  # 假設爬蟲程式碼中用"A"表示動漫
        exhibition_data = crawl_exhibition_data(category)
        if exhibition_data:
            message = "\n".join(exhibition_data)
            line_bot_api.push_message(user_id, TextSendMessage(text=message))
        else:
            line_bot_api.push_message(user_id, TextSendMessage(text="抱歉，沒有找到相關展覽資料。"))

@handler.add(MemberJoinedEvent)
def welcome(event):
    uid = event.joined.members[0].user_id
    gid = event.source.group_id
    profile = line_bot_api.get_group_member_profile(gid, uid)
    name = profile.display_name
    message = TextSendMessage(text=f'{name}歡迎加入')
    line_bot_api.reply_message(event.reply_token, message)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
