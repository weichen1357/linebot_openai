from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
import os
import requests
import random
from bs4 import BeautifulSoup

app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

user_data = {}

def get_headers():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'
    ]
    headers = {'User-Agent': random.choice(user_agents)}
    return headers

def scrape_anime_info():
    anime_list = []
    url = 'https://ani.gamer.com.tw/'
    try:
        response = requests.get(url, headers=get_headers(), timeout=10)
        response.encoding = 'utf-8'

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            newanime_item = soup.select_one('.timeline-ver > .newanime-block')
            if not newanime_item:
                print("No newanime_item found")
                return anime_list

            anime_items = newanime_item.select('.newanime-date-area:not(.premium-block)')
            print(f"Found {len(anime_items)} anime items")

            for anime_item in anime_items:
                anime_info = {}
                name_tag = anime_item.select_one('.anime-name > p')
                watch_number_tag = anime_item.select_one('.anime-watch-number > p')
                episode_tag = anime_item.select_one('.anime-episode')
                link_tag = anime_item.select_one('a.anime-card-block')

                if name_tag and watch_number_tag and episode_tag and link_tag:
                    anime_info['name'] = name_tag.text.strip()
                    anime_info['watch_number'] = watch_number_tag.text.strip()
                    anime_info['episode'] = episode_tag.text.strip()
                    anime_info['link'] = "https://ani.gamer.com.tw/" + link_tag.get('href')
                    anime_list.append(anime_info)
                    print(f"Added anime: {anime_info}")

        else:
            print(f'請求失敗: {response.status_code}')
    except requests.RequestException as e:
        print(f"請求錯誤: {e}")
    except Exception as e:
        print(f"未知錯誤: {e}")
    finally:
        return anime_list

def convert_watch_number(anime_list):
    for anime in anime_list:
        if '萬' in anime['watch_number']:
            anime['watch_number'] = float(anime['watch_number'].replace('萬', '')) * 10000
        else:
            anime['watch_number'] = int(anime['watch_number'])
        print(f"Converted watch number for {anime['name']}: {anime['watch_number']}")
    return anime_list

def aggregate_anime_info(anime_list):
    anime_dict = {}
    for anime in anime_list:
        if anime['name'] in anime_dict:
            anime_dict[anime['name']]['watch_number'] += anime['watch_number']
        else:
            anime_dict[anime['name']] = anime
    print("Aggregated anime info:", anime_dict)
    return list(anime_dict.values())

def format_anime_info(anime_list, user_name):
    if not anime_list:
        return f"@{user_name} 您好(你好)\n今天沒有找到任何動畫信息。"

    formatted_text = f"@{user_name} 您好(你好)\n揭曉今天播放次數最高的動畫排行榜 !\n\n"
    for i, anime in enumerate(anime_list, start=1):
        formatted_text += f"({i}) {anime['name']}\n"
        formatted_text += f"集數: {anime['episode']}\n"
        formatted_text += f"觀看次數: {int(anime['watch_number'])}\n"
        formatted_text += f"點我馬上看: {anime['link']}\n\n"
    return formatted_text.strip()

def get_anime_ranking(user_name):
    print("Start getting anime ranking")
    anime_list = scrape_anime_info()
    print("Scraped anime info:", anime_list)
    if not anime_list:
        return f"@{user_name} 您好(你好)\n今天沒有找到任何動畫信息。"

    anime_list = convert_watch_number(anime_list)
    print("Converted watch numbers:", anime_list)
    anime_list = aggregate_anime_info(anime_list)
    print("Aggregated anime info:", anime_list)
    anime_list = sorted(anime_list, key=lambda x: x['watch_number'], reverse=True)
    print("Sorted anime info:", anime_list)
    formatted_text = format_anime_info(anime_list, user_name)
    return formatted_text

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
        user_data[user_id] = {'category': None, 'seen': [], 'count': 0, 'year': None}  # 在 user_data 中添加 year 字段

    if event.message.text == "播放排行榜":
        print("播放排行榜 button clicked")
        ranking_text = get_anime_ranking(user_name)
        print("Ranking text:", ranking_text)
        reply_message = TextSendMessage(text=ranking_text)
        line_bot_api.reply_message(event.reply_token, reply_message)
    else:
        print("Other message received: " + event.message.text)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="我不明白你的意思，可以再說一遍嗎？🤔"))

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
