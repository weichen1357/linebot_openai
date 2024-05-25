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

def scrape_and_send_ranking():
    # 获取头信息
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'
    ]
    headers = {'User-Agent': random.choice(user_agents)}
    
    # 抓取动画信息
    anime_list = []
    url = 'https://ani.gamer.com.tw/'
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'

        if response.status_code == 200:
            print(f'請求成功: {response.status_code}')

            soup = BeautifulSoup(response.text, 'html.parser')
            newanime_item = soup.select_one('.timeline-ver > .newanime-block')
            if not newanime_item:
                print('未找到動畫區塊')
            else:
                anime_items = newanime_item.select('.newanime-date-area:not(.premium-block)')

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

        else:
            print(f'請求失敗: {response.status_code}')
    except requests.RequestException as e:
        print(f"請求錯誤: {e}")
    except Exception as e:
        print(f"未知錯誤: {e}")

    # 转换观看次数
    for anime in anime_list:
        if '萬' in anime['watch_number']:
            anime['watch_number'] = float(anime['watch_number'].replace('萬', '')) * 10000
        else:
            anime['watch_number'] = int(anime['watch_number'])

    # 聚合动画信息
    anime_dict = {}
    for anime in anime_list:
        if anime['name'] in anime_dict:
            anime_dict[anime['name']]['watch_number'] += anime['watch_number']
        else:
            anime_dict[anime['name']] = anime
    anime_list = list(anime_dict.values())

    # 按观看次数排序
    anime_list = sorted(anime_list, key=lambda x: x['watch_number'], reverse=True)

    # 格式化输出
    formatted_text = "@使用者 您好(你好)\n揭曉今天播放次數最高的動畫排行榜 !\n\n"
    for i, anime in enumerate(anime_list, start=1):
        formatted_text += f"({i}) {anime['name']}\n"
        formatted_text += f"集數: {anime['episode']}\n"
        formatted_text += f"觀看次數: {int(anime['watch_number'])}\n"
        formatted_text += f"點我馬上看: {anime['link']}\n\n"
    return formatted_text.strip()

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_profile = line_bot_api.get_profile(event.source.user_id)
    user_name = user_profile.display_name
    user_id = event.source.user_id
    print(f"Received message from {user_name}: {event.message.text}")

    if user_id not in user_data:
        user_data[user_id] = {'category': None, 'seen': [], 'count': 0, 'year': None}

    if event.message.text == "播放排行榜":
        ranking_message = scrape_and_send_ranking()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=ranking_message))

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
    message = TextSendMessage(text=f'{name} 歡迎加入🎉')
    line_bot_api.push_message(gid, message)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
