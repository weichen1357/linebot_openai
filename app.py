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

app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

user_data = {}

def fetch_csv_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        csv_data = response.text
        return csv_data
    except requests.exceptions.RequestException as e:
        print("Error fetching CSV data:", e)
        return None

def parse_csv_data(csv_content, category, exclude_list=None, start_index=1):
    try:
        csv_reader = csv.reader(csv_content.splitlines())
        next(csv_reader)
        rows = [row for row in csv_reader if len(row) == 5]

        if exclude_list:
            rows = [row for row in rows if row[0] not in exclude_list]

        sampled_rows = rows[:5]  # 取前五个或剩下的
        message = "\n".join([f"『{row[1]}』\n人氣: {row[0]}\n上架時間: {row[2]}\n以下是觀看連結:\n{row[3]}" for row in sampled_rows])
        return message, sampled_rows
    except csv.Error as e:
        print("Error parsing CSV:", e)
        return None, []

def parse_csv_data_for_random_pick(csv_content):
    try:
        csv_reader = csv.reader(csv_content.splitlines())
        next(csv_reader)
        rows = [row for row in csv_reader if len(row) == 5]
        random_row = random.choice(rows)
        name, popularity, date, url, img = random_row
        message = f"這裡為您推薦一部人氣動漫:\n\n『{popularity}』\n人氣: {name}\n上架时间: {date}\n以下是觀看連結:\n{url}\n"
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
    user_id = event.source.user_id
    print(f"Received message from {user_name}: {event.message.text}")

    if user_id not in user_data:
        user_data[user_id] = {'category': None, 'seen': [], 'count': 0}

    if event.message.text == "ACG展覽資訊":
        print("ACG展覽資訊 button clicked")
        reply_message = TextSendMessage(
            text=f"@{user_name} 您好，想了解ACG（A：动漫、C：漫画、G：电玩）的展览资讯吗？请选择您想了解的相关资讯吧！",
            quick_reply=QuickReply(
                items=[
                    QuickReplyButton(action=MessageAction(label="A：动漫", text="A：动漫")),
                    QuickReplyButton(action=MessageAction(label="C：漫画", text="C：漫画")),
                    QuickReplyButton(action=MessageAction(label="G：电玩", text="G：电玩"))
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, reply_message)
    elif event.message.text == "愛看啥類別":
        print("愛看啥類別 button clicked")
        reply_message = TextSendMessage(
            text=f"@{user_name} 您好，想觀看什麼類型的動漫呢？請選取您想觀看的類型吧！",
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
    elif event.message.text in ["王道", "校園", "戀愛", "運動", "喜劇", "異世界"]:
        print(f"{event.message.text} button clicked")
        url = f"https://raw.githubusercontent.com/weichen1357/linebot_openai/master/{event.message.text}.csv"
        csv_data = fetch_csv_data(url)
        if csv_data:
            user_data[user_id]['category'] = event.message.text
            user_data[user_id]['count'] = 0
            message, sampled_rows = parse_csv_data(csv_data, event.message.text)
            user_data[user_id]['seen'] = [row[0] for row in sampled_rows]
            user_data[user_id]['count'] += len(sampled_rows)

            buttons_template = TemplateSendMessage(
                alt_text="是否要再追加五部動漫？",
                template=ButtonsTemplate(
                    text=f"@{user_name} 是否要再追加五部動漫呢？",
                    actions=[
                        MessageAction(label="是", text="是"),
                        MessageAction(label="否", text="否")
                    ]
                )
            )

            line_bot_api.reply_message(event.reply_token, [
                TextSendMessage(text=f"這裡為您推薦一部人氣動漫:\n\n{message}"),
                buttons_template
            ])
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"抱歉，无法获取{event.message.text}番剧列表。"))
    elif event.message.text == "是" and user_data[user_id]['category']:
        category = user_data[user_id]['category']
        url = f"https://raw.githubusercontent.com/weichen1357/linebot_openai/master/{category}.csv"
        csv_data = fetch_csv_data(url)
        if csv_data:
            start_index = user_data[user_id]['count'] + 1
            message, sampled_rows = parse_csv_data(csv_data, category, exclude_list=user_data[user_id]['seen'], start_index=start_index)
            user_data[user_id]['seen'].extend([row[0] for row in sampled_rows])
            user_data[user_id]['count'] += len(sampled_rows)

            buttons_template = TemplateSendMessage(
                alt_text="是否要再追加五部動漫？",
                template=ButtonsTemplate(
                    text=f"@{user_name} 是否要再追加五部動漫呢？",
                    actions=[
                        MessageAction(label="是", text="是"),
                        MessageAction(label="否", text="否")
                    ]
                )
            )

            line_bot_api.reply_message(event.reply_token, [
                TextSendMessage(text=f"這裡為您推薦一部人氣動漫:\n\n{message}"),
                buttons_template
            ])
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"抱歉，无法获取更多{category}番剧列表。"))
    elif event.message.text == "否":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"歐虧，那祝你影片欣賞愉快!"))
    elif event.message.text == "今天來看啥":
        categories = ["王道", "校園", "戀愛", "運動", "喜劇", "異世界"]
        random_category = random.choice(categories)
        url = f"https://raw.githubusercontent.com/weichen1357/linebot_openai/master/{random_category}.csv"
        csv_data = fetch_csv_data(url)
        if csv_data:
            message = parse_csv_data_for_random_pick(csv_data)
            reply_message = f"@{user_name} 您好，想消磨時間卻不知道看哪一部動漫嗎?\n隨機為您推薦一部人氣動漫:\n\n{message}"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_message))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="抱歉，无法获取推薦的番剧列表。"))
    else:
        print("Other message received: " + event.message.text)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="我不明白你的意思，可以再说一遍吗？"))

@handler.add(PostbackEvent)
def handle_postback(event):
    user_profile = line_bot_api.get_profile(event.source.user_id)
    user_name = user_profile.display_name
    print(f"Received postback event from {user_name}: {event.postback.data}")
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=event.postback.data))

@handler.add(MemberJoinedEvent)
def welcome(event):
    gid = event.source.group_id
    profile = line_bot_api.get_group_member_profile(gid, event.joined.members[0].user_id)
    name = profile.display_name
    message = TextSendMessage(text=f'{name} 欢迎加入')
    line_bot_api.push_message(gid, message)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
