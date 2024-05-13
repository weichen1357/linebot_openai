from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *

# 匯入你的爬蟲程式碼
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os

# 初始化 Flask 應用
app = Flask(__name__)

# 初始化 Line Bot API
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# 爬取指定季節的動畫資訊並回傳
def scrape_anime_season(url):
    # 爬蟲程式碼與函數內容請參考你原本的程式碼
    pass

# 監聽所有來自 /callback 的 Post Request
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
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
    if message_text == "/爬取動畫":
        # 呼叫爬蟲函數爬取網頁內容
        scrape_anime_season('https://myanimelist.net/anime/season/2024/spring')
        # 讀取爬取到的資料
        with open('2024-spring-combined.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
        # 建立回覆訊息的文字內容
        reply_text = ""
        for anime in data:
            reply_text += f"{anime['title']} - {anime['release_date']}\n"
        # 將爬取到的內容回傳給使用者
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )

# 主程式入口
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
