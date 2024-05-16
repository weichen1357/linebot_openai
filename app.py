from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
import time
import os

app = Flask(__name__)
static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# 设置 Chrome Driver 路径
CHROME_DRIVER_PATH = "/path/to/chromedriver"

# 创建 Chrome Webdriver
def crawl_exhibition_data(category):
    options = ChromeOptions()
    options.add_argument('--headless')  # 使用 Chrome Headless 模式
    service = ChromeService(executable_path=CHROME_DRIVER_PATH)
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
    finally:
        driver.quit()  # 關閉瀏覽器

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("請求內容: " + body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_profile = line_bot_api.get_profile(event.source.user_id)
    user_name = user_profile.display_name
    print("Received message:", event.message.text)
    if event.message.text == "ACG展覽資訊":
        print("ACG展覽資訊 button clicked")
        reply_message = TextSendMessage(
            text="@{} 您好，想了解ACG（A：動漫、C：漫畫、G：電玩）的展覽資訊嗎？請選擇你想了解的相關資訊吧！".format(user_name),
            quick_reply=QuickReply(
                items=[
                    QuickReplyButton(action=PostbackAction(label="A：動漫", data="ANIME_EXHIBITION")),
                    QuickReplyButton(action=PostbackAction(label="C：漫畫", data="COMIC_EXHIBITION")),
                    QuickReplyButton(action=PostbackAction(label="G：電玩", data="GAME_EXHIBITION"))
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, reply_message)
    elif event.message.text == "本季度新番":
        print("本季度新番 button clicked")
        reply_message = TextSendMessage(
            text="@{} 您好，請選擇年份".format(user_name),
            quick_reply=QuickReply(
                items=[
                    QuickReplyButton(action=PostbackAction(label="2023", data="SEASON_SELECTION_2023")),
                    QuickReplyButton(action=PostbackAction(label="2024", data="SEASON_SELECTION_2024"))
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, reply_message)
    else:
        print("Other message received")

@handler.add(PostbackEvent)
def handle_postback(event):
    user_profile = line_bot_api.get_profile(event.source.user_id)
    user_name = user_profile.display_name
    print("Received postback event:", event.postback.data)
    if event.postback.data == "ANIME_EXHIBITION":
        print("ANIME_EXHIBITION button clicked")
        category = "A:動漫"
        exhibition_data = crawl_exhibition_data(category)
        if exhibition_data:
            message = "\n".join(exhibition_data)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=message))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="抱歉，沒有找到相關展覽資料。"))
    elif event.postback.data.startswith("SEASON_SELECTION"):
        print("SEASON_SELECTION button clicked")
        # 這是一個新的 Postback 事件，詢問季度
        year = event.postback.data.split("_")[1]
        reply_message = TextSendMessage(
            text="@{} 您好，您選擇了 {} 年，請選擇季度項目".format(user_name, year),
            quick_reply=QuickReply(
                items=[
                    QuickReplyButton(action=MessageAction(label="冬", text=year + "冬")),
                    QuickReplyButton(action=MessageAction(label="春", text=year + "春")),
                    QuickReplyButton(action=MessageAction(label="夏", text=year + "夏")),
                    QuickReplyButton(action=MessageAction(label="秋", text=year + "秋")),
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, reply_message)
    elif event.postback.data.startswith("2023") or event.postback.data.startswith("2024"):
        print("Season selected:", event.postback.data)
        # Here you can handle the selection of the season
        pass
    else:
        print("Other postback event received")

@handler.add(MemberJoinedEvent)
def welcome(event):
    gid = event.source.group_id
    profile = line_bot_api.get_group_member_profile(gid, event.joined.members[0].user_id)
    name = profile.display_name
    message = TextSendMessage(text=f'{name} 歡迎加入')
    line_bot_api.push_message(gid, message)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
