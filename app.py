from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *
import os
import csv
import random
import requests

app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# 在 Flask 應用程式之外讀取 CSV 檔案，並解析數據
anime_data = []

# 讀取 CSV 檔案
csv_url = "https://raw.githubusercontent.com/weichen1357/linebot_openai/master/王道番整合數據.csv"
response = requests.get(csv_url)

if response.status_code == 200:
    lines = response.text.split("\n")
    reader = csv.DictReader(lines)
    for row in reader:
        anime_data.append(row)
else:
    print("Failed to fetch CSV file")

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

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_profile = line_bot_api.get_profile(event.source.user_id)
    user_name = user_profile.display_name
    print(f"Received message from {user_name}: {event.message.text}")

    if event.message.text == "ACG展覽資訊":
        print("ACG展覽資訊 button clicked")
        reply_message = TextSendMessage(
            text=f"@{user_name} 您好，想了解ACG（A：動漫、C：漫畫、G：電玩）的展覽資訊嗎？請選擇你想了解的相關資訊吧！",
            quick_reply=QuickReply(
                items=[
                    QuickReplyButton(action=MessageAction(label="A：動漫", text="A：動漫")),
                    QuickReplyButton(action=MessageAction(label="C：漫畫", text="C：漫畫")),
                    QuickReplyButton(action=MessageAction(label="G：電玩", text="G：電玩"))
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, reply_message)
    elif event.message.text == "王道":
        # 從動漫數據中隨機選取五條記錄
        random_anime = random.sample(anime_data, 5)

        # 構建回覆訊息
        reply_message = "以下是王道動漫的資訊：\n"
        for index, value in enumerate(random_anime):
            reply_message += (
                f'{index + 1}. 『{value["name"]}』\n'
                f'人氣：{value["popularity"]}\n'
                f'上架時間：{value["date"]}\n'
                f'以下是觀看連結：\n'
                f'{value["url"]}\n\n'
            )

        # 回覆訊息給使用者
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_message))
    elif event.message.text == "本季度新番":
        print("本季度新番 button clicked")
        reply_message = TextSendMessage(
            text=f"@{user_name} 您好，請選擇年份",
            quick_reply=QuickReply(
                items=[
                    QuickReplyButton(action=MessageAction(label="2023", text="2023")),
                    QuickReplyButton(action=MessageAction(label="2024", text="2024"))
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, reply_message)
    elif event.message.text in ["2023", "2024"]:
        print(f"Year selected: {event.message.text}")
        if event.message.text == "2023":
            seasons = ["冬", "春", "夏", "秋"]
        else:
            seasons = ["冬", "春"]

        quick_reply_items = [QuickReplyButton(action=MessageAction(label=season, text=season)) for season in seasons]
        reply_message = TextSendMessage(
            text=f"@{user_name} 您好，接著請選擇季度項目",
            quick_reply=QuickReply(items=quick_reply_items)
        )
        line_bot_api.reply_message(event.reply_token, reply_message)
    elif event.message.text == "愛看啥類別":
        print("愛看啥類別 button clicked")
        reply_message = TextSendMessage(
            text=f"@{user_name} 您好，想觀看甚麼類型的動漫呢?請選擇想觀看的類型吧!",
            quick_reply=QuickReply(
                items=[
                    QuickReplyButton(action=MessageAction(label="王道", text="王道")),
                    QuickReplyButton(action=MessageAction(label="校園", text="校園")),
                    QuickReplyButton(action=MessageAction(label="戀愛", text="戀愛")),
                    QuickReplyButton(action=MessageAction(label="運動", text="運動")),
                    QuickReplyButton(action=MessageAction(label="喜劇", text="喜劇")),
                    QuickReplyButton(action=MessageAction(label="異世界", text="異世界"))
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, reply_message)
    else:
        print("Other message received: " + event.message.text)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="我不明白你的意思，可以再說一遍嗎？"))

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
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"Welcome {profile.display_name}!")
    )

if __name__ == "__main__":
    app.run()
