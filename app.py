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

app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

def fetch_csv_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # 检查是否有错误发生
        csv_data = response.text
        return csv_data
    except requests.exceptions.RequestException as e:
        print("Error fetching CSV data:", e)
        return None

def parse_csv_data(csv_content):
    try:
        csv_reader = csv.reader(csv_content.splitlines())
        message = "王道番劇列表：\n"
        count = 0
        for row in csv_reader:
            if count >= 5:
                break
            message += f"- {row[0]}\n"
            count += 1
        return message
    except csv.Error as e:
        print("Error parsing CSV:", e)
        return None

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
    elif event.message.text == "王道":
        print("王道 button clicked")
        url = "https://raw.githubusercontent.com/weichen1357/linebot_openai/master/%E7%8E%8B%E9%81%93%E7%95%AA%E6%95%B4%E5%90%88%E6%95%B8%E6%93%9A.csv"
        csv_data = fetch_csv_data(url)
        if csv_data:
            message = parse_csv_data(csv_data)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=message))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="抱歉，無法獲取王道番剧列表。"))
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
    name = profile.display_name
    message = TextSendMessage(text=f'{name} 歡迎加入')
    line_bot_api.push_message(gid, message)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
