from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *
import pandas as pd
import os

app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# 读取 CSV 文件
df = pd.read_csv("https://github.com/weichen1357/linebot_openai/blob/master/%E7%8E%8B%E9%81%93%E7%95%AA%E6%95%B4%E5%90%88%E6%95%B8%E6%93%9A.csv")

# 根据类别过滤动漫数据
def filter_anime_by_category(category, df):
    filtered_df = df[df['category'] == category]
    return filtered_df

# 生成动漫信息回复消息
def Category(result, msg): 
    reply_1 = f'這裡依照近期人氣為您推薦5部｢{msg}｣類別動漫：\n\n' 
    for index,value in enumerate(result): 
        reply = (f'{index + 1}. 『{value["name"]}』\n' 
                f'人氣：{value["popularity"]}\n' 
                f'上架時間：{value["date"]}\n' 
                f'以下是觀看連結：\n' 
                f'{value["url"]}\n') 
        reply_1 = reply_1 + reply 
    return reply_1

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

    # 直接回复 PostbackAction 的数据
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
