from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *
import os

app = Flask(__name__)
static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

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

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    print("Received message:", event.message.text)
    if event.message.text == "本季度新番":
        print("本季度新番 button clicked")
        reply_message = TextSendMessage(
            text="請選擇年份",
            quick_reply=QuickReply(
                items=[
                    QuickReplyButton(action=MessageAction(label="2023", text="2023")),
                    QuickReplyButton(action=MessageAction(label="2024", text="2024"))
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, reply_message)
    else:
        print("Other message received")

@handler.add(PostbackEvent)
def handle_postback(event):
    user_id = event.source.user_id
    print("Received postback event:", event.postback.data)
    if event.postback.data == "2023" or event.postback.data == "2024":
        print("Year selected:", event.postback.data)
        reply_messages = [
            TextSendMessage(text=f"@{user_id} 您選擇的年份是 {event.postback.data}"),
            TextSendMessage(text="請選擇季度"),
            QuickReply(
                items=[
                    QuickReplyButton(action=PostbackAction(label="冬", data=event.postback.data + "冬")),
                    QuickReplyButton(action=PostbackAction(label="春", data=event.postback.data + "春")),
                    QuickReplyButton(action=PostbackAction(label="夏", data=event.postback.data + "夏")),
                    QuickReplyButton(action=PostbackAction(label="秋", data=event.postback.data + "秋"))
                ]
            )
        ]
        line_bot_api.reply_message(event.reply_token, reply_messages)
    elif event.postback.data.endswith("冬") or event.postback.data.endswith("春") or event.postback.data.endswith("夏") or event.postback.data.endswith("秋"):
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
