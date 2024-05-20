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
        response.raise_for_status()  # 检查是否有错误发生
        csv_data = response.text
        return csv_data
    except requests.exceptions.RequestException as e:
        print("Error fetching CSV data:", e)
        return None

def parse_csv_data(csv_content, category, exclude_list=None, start_index=1):
    try:
        csv_reader = csv.reader(csv_content.splitlines())
        next(csv_reader)  # 跳过标题行
        rows = [row for row in csv_reader if len(row) == 5 and row[0] not in (exclude_list or [])]  # 避免空数据行
        # 随机挑选五个
        sampled_rows = random.sample(rows, min(5, len(rows)))
        message = f"這裡依照近期人氣為您推薦五部「{category}」類別動漫:\n\n"
        for count, row in enumerate(sampled_rows, start=start_index):
            name, popularity, date, url, img = row
            message += f"{count}. 『{popularity}』\n人氣: {name}\n上架时间: {date}\n以下是觀看連結:\n{url}\n\n"
        return message, sampled_rows
    except csv.Error as e:
        print("Error parsing CSV:", e)
        return None, []

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
                TextSendMessage(text=message),
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
                TextSendMessage(text=message),
                buttons_template
            ])
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"抱歉，无法获取更多{category}番剧列表。"))
    elif event.message.text == "否":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"歐虧，那祝你影片欣賞愉快!"))
    else:
        print("Other message received: " + event.message.text)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="我不明白你的意思，可以再说一遍吗？"))

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
    message = TextSendMessage(text=f'{name} 欢迎加入')
    line_bot_api.push_message(gid, message)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
