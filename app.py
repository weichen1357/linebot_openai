from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *
import os
import requests
import csv
import random
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from googletrans import Translator
from linebot.models import TextSendMessage
from google.cloud import vision
import io
import sqlite3
from google.colab import files
app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

user_data = {}

# 设置 Google Cloud Vision API 客户端
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "your-service-account-file(1).json"
client = vision.ImageAnnotatorClient()

def test_vision_api(image_path):
    with io.open(image_path, 'rb') as image_file:
        content = image_file.read()

    image = vision.Image(content=content)
    image_context = vision.ImageContext(language_hints=['zh'])
    response = client.label_detection(image=image, image_context=image_context)
    labels = response.label_annotations

    label_descriptions = [label.description for label in labels]
    for description in label_descriptions:
        print(description)

    return label_descriptions

def search_database(label_descriptions):
    conn = sqlite3.connect('anime_characters.db')
    cursor = conn.cursor()

    query = "SELECT name, anime, url, about FROM characters"
    cursor.execute(query)
    results = cursor.fetchall()

    matching_results = []
    for row in results:
        name, anime, url, about = row
        if any(keyword in about for keyword in label_descriptions):
            matching_results.append((name, anime, url))

    conn.close()
    return matching_results

def setup_database():
    conn = sqlite3.connect('anime_characters.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            anime TEXT NOT NULL,
            url TEXT NOT NULL,
            about TEXT
        )
    ''')

    cursor.executemany('''
        INSERT INTO characters (name, anime, url, about)
        VALUES (?, ?, ?, ?)
    ''', [
        ('五條悟', '咒術迴戰', 'https://m.manhuagui.com/comic/28004/', 'Long hair'),
        ('多啦A夢', '多啦A夢', 'https://www.ofiii.com/section/114', 'Graphics'),
        ('桐谷和人', '刀劍神域', 'https://ani.gamer.com.tw/animeVideo.php?sn=926', 'Cg artwork'),
        ('工藤新一', '名偵探柯南', 'https://ani.gamer.com.tw/animeVideo.php?sn=30234', 'Chin'),
        ('魯夫', '航海王', 'https://gimy.ai/eps/252248-4-1020.html', 'Mammal'),
        ('鳴人', '火影忍者', 'https://ani.gamer.com.tw/animeVideo.php?sn=16844', 'Font'),
    ])

    conn.commit()
    conn.close()

# 设置数据库
setup_database()





@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    app.logger.info("Signature: " + signature)
    app.logger.info("Request body: " + body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("Invalid signature. Check your channel access token/channel secret.")
        abort(400)
    return 'OK'

def translate_title(title, translator):
    try:
        translation = translator.translate(title, src='en', dest='zh-tw')
        return translation.text
    except Exception as e:
        print(f"Error translating title '{title}':", e)
        return title

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_profile = line_bot_api.get_profile(event.source.user_id)
    user_name = user_profile.display_name
    user_id = event.source.user_id
    print(f"Received message from {user_name}: {event.message.text}")

    if user_id not in user_data:
        user_data[user_id] = {'category': None, 'seen': [], 'count': 0, 'year': None}  # 在 user_data 中添加 year 字段

    if event.message.text == "播放排行榜":
        top_watched_anime = fetch_top_watched_anime()
        if top_watched_anime:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=top_watched_anime))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="抓取動畫排行榜時出錯。請稍後再試。"))
    elif event.message.text == "拍照搜一下":
        print("拍照搜一下 button clicked")
        buttons_template = TemplateSendMessage(
            alt_text='拍照搜一下',
            template=ButtonsTemplate(
                title='拍照搜一下',
                text=f'@{user_name} 请上传一张动漫图片，我会帮您识别出人物并提供相关信息和视频链接。',
                actions=[
                    MessageAction(
                        label='上传图片',
                        text='上传图片'
                    )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons_template)
    elif event.message.text == "上传图片":
        # 上传图片时应从 Line 服务器获取图片
        message_content = line_bot_api.get_message_content(event.message.id)
        image_path = f"{event.message.id}.jpg"
        with open(image_path, 'wb') as fd:
            for chunk in message_content.iter_content():
                fd.write(chunk)

        label_descriptions = test_vision_api(image_path)
        if label_descriptions:
            results = search_database(label_descriptions)
            if results:
                messages = [TextSendMessage(text=f"此动漫人物是{name}，出自{anime}，以下是观赏链接🔗：{url}") for name, anime, url in results]
                line_bot_api.reply_message(event.reply_token, messages)
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="未找到该角色的相关信息。"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="未能识别该图像中的角色。"))
    else:
        print("Other message received: " + event.message.text)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="我不明白你的意思，可以再说一遍吗？🤔"))


@handler.add(PostbackEvent)
def handle_postback(event):
    user_profile = line_bot_api.get_profile(event.source.user_id)
    user_name = user_profile.display_name
    print(f"Received postback event from {user_name}: {event.postback.data}")
    # Directly reply with the data from the PostbackAction
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=event.postback.data))

@handler.add(MemberJoinedEvent)
def welcome(event):
    gid = event.source.group_id
    profile = line_bot_api.get_group_member_profile(gid, event.joined.members[0].user_id)
    name = profile.display_name
    message = TextSendMessage(text=f'{name} 歡迎加入🎉')
    line_bot_api.push_message(gid, message)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)  
