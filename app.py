@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    message = event.message.text
    print("Received message:", message)

    if message == "ACG展覽資訊":
        reply_message = TextSendMessage(
            text="@{} 您好，想了解ACG（A：動漫、C：漫畫、G：電玩）的展覽資訊嗎？請選擇你想了解的相關資訊吧！".format(user_id),
            quick_reply=QuickReply(
                items=[
                    QuickReplyButton(action=PostbackAction(label="A：動漫", data="ANIME_EXHIBITION")),
                    QuickReplyButton(action=PostbackAction(label="C：漫畫", data="COMIC_EXHIBITION")),
                    QuickReplyButton(action=PostbackAction(label="G：電玩", data="GAME_EXHIBITION"))
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, reply_message)
    elif message == "本季度新番":
        print("本季度新番 button clicked")
        reply_message = TextSendMessage(
            text="@{} 您好，請選擇年份".format(user_id),
            quick_reply=QuickReply(
                items=[
                    QuickReplyButton(action=PostbackAction(label="2023", data="2023")),
                    QuickReplyButton(action=PostbackAction(label="2024", data="2024"))
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, reply_message)
    else:
        print("Other message received")

@handler.add(PostbackEvent)
def handle_postback(event):
    user_id = event.source.user_id
    postback_data = event.postback.data
    print("Received postback event:", postback_data)
    
    if postback_data == "ANIME_EXHIBITION":
        category = "A:動漫"
        exhibition_data = crawl_exhibition_data(category)
        if exhibition_data:
            message = "\n".join(exhibition_data)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=message))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="抱歉，沒有找到相關展覽資料。"))
    elif postback_data in ["2023", "2024"]:
        print("Selected year:", postback_data)  # Print the selected year
        if postback_data == "2023":
            seasons = ["冬", "春", "夏", "秋"]
        else:
            seasons = ["冬", "春"]

        quick_reply_items = [QuickReplyButton(action=MessageAction(label=season, text=postback_data + season)) for season in seasons]
        reply_message = TextSendMessage(
            text="@{} 您好，請選擇季度項目".format(user_id),
            quick_reply=QuickReply(items=quick_reply_items)
        )
        line_bot_api.reply_message(event.reply_token, reply_message)
    elif postback_data.startswith("2023") or postback_data.startswith("2024"):
        print("Season selected:", postback_data)
        # Here you can handle the selection of the season
        pass
    else:
        print("Other postback event received")


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
