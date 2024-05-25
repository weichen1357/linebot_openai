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

app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

user_data = {}

def fetch_csv_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # 檢查是否有錯誤發生
        csv_data = response.text
        return csv_data
    except requests.exceptions.RequestException as e:
        print("Error fetching CSV data:", e)
        return None

def parse_csv_data(csv_content, category, exclude_list=None, start_index=1):
    try:
        csv_reader = csv.reader(csv_content.splitlines())
        next(csv_reader)  # 跳過標題行
        rows = [row for row in csv_reader if len(row) == 5 and row[0] not in (exclude_list or [])]  # 避免空數據行
        # 隨機挑選五個
        sampled_rows = random.sample(rows, min(5, len(rows)))
        message = f"這裡依照近期人氣為您推薦五部「{category}」類別動漫📺:\n\n"
        for count, row in enumerate(sampled_rows, start=start_index):
            name, popularity, date, url, img = row
            message += f"{count}. 『{popularity}』\n✨ 人氣: {name}\n🗓 上架時間: {date}\n🔗 以下是觀看連結:\n{url}\n\n"
        return  message,sampled_rows
    except csv.Error as e:
        print("Error parsing CSV:", e)
        return None, []

def parse_single_csv_data(csv_content, category, user_name):
    try:
        csv_reader = csv.reader(csv_content.splitlines())
        next(csv_reader)  # 跳過標題行
        rows = [row for row in csv_reader if len(row) == 5]  # 避免空數據行
        sampled_row = random.choice(rows)
        name, popularity, date, url, img = sampled_row
        message = (f"@{user_name} 您好👋，想消磨時間卻不知道看哪一部動漫嗎?\n\n隨機為您推薦一部人氣動漫📺:\n"
                   f"👇👇👇👇👇\n"
                   f"🎥 {popularity}\n"
                   f"🔥 人氣: {name}\n"
                   f"🗓 上架時間: {date}\n"
                   f"🔗 以下是觀看連結：\n{url}")
        return message
    except csv.Error as e:
        print("Error parsing CSV:", e)
        return None

def scrape_anime_season(url):
    headers = {"User-Agent": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}
    anime_list = []
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    anime_entries = soup.find_all('div', class_='seasonal-anime')

    for entry in anime_entries:
        anime_dict = {}
        title_div = entry.find('div', class_='title')
        if title_div:
            a_tag = title_div.find('a', class_='link-title')
            if a_tag:
                anime_dict['link'] = urljoin(url, a_tag['href'])
                anime_dict['title'] = a_tag.text.strip()

        synopsis_div = entry.find('div', class_='synopsis')
        if synopsis_div:
            synopsis_p = synopsis_div.find('p')
            if synopsis_p:
                anime_dict['synopsis'] = synopsis_p.text.strip()

        date_span = entry.find('span', class_='item')
        if date_span:
            anime_dict['release_date'] = date_span.text.strip()

        score_div = entry.find('div', class_='score score-label')
        if score_div:
            score_span = score_div.find('span', class_='text')
            if score_span:
                anime_dict['score'] = score_span.text.strip()
        else:
            print("Score not found!")

        img_div = entry.find('div', class_='image')  # 這裡修正了 class_='image'
        if img_div and img_div.find('img'):
            img_tag = img_div.find('img')
            img_url = img_tag.get('data-src') or img_tag.get('src')
            if img_url:
                anime_dict['image_url'] = urljoin(url, img_url)

        anime_list.append(anime_dict)
    return anime_list
def scrape_anime_events_with_images():
    url = "https://www.e-muse.com.tw/zh/news/latest-news/events/"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            news_items = soup.find_all(class_="item article_item sr_bottom")
            events_info = []
            for item in news_items:
                title_element = item.find(class_="title")
                title_text = title_element.get_text(strip=True)
                time_element = item.find(class_="date")
                time_text = time_element.find(class_="txt-semibold").get_text(strip=True)
                learn_more_link = item['href']
                figure_element = item.find('figure')
                image_url = None
                if figure_element:
                    style_attr = figure_element.get('style')
                    if style_attr:
                        image_url = style_attr.split('url(')[1].split(')')[0]
                event_info = {
                    'title': title_text,
                    'time': time_text,
                    'learn_more_link': learn_more_link,
                    'image_url': image_url
                }
                events_info.append(event_info)
            return events_info
        else:
            return None
    except Exception as e:
        print("Error scraping anime events:", e)
        return None

def generate_anime_event_carousel(events_info):
    bubbles = []
    for event_info in events_info:
        bubble = BubbleContainer(
            direction='ltr',
            hero=ImageComponent(
                url=event_info['image_url'] if event_info['image_url'] else 'https://example.com/default_image.jpg',
                size='full',
                aspect_ratio='20:13',
                aspect_mode='cover'
            ),
            body=BoxComponent(
                layout='vertical',
                contents=[
                    TextComponent(text=event_info['title'], weight='bold', size='xl'),
                    BoxComponent(
                        layout='vertical',
                        margin='lg',
                        contents=[
                            TextComponent(text=f'活動日期: {event_info["time"]}', size='md'),
                            TextComponent(text='點我了解更多喲!', size='md', color='#0084B6', align='center' ,action=URIAction(uri=event_info['learn_more_link'], label='了解更多'))
                        ]
                    )
                ]
            )
        )
        bubbles.append(bubble)
    
    carousel = CarouselContainer(contents=bubbles)
    return carousel


# anime_ranking.py
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
                return anime_list

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
    finally:
        return anime_list

def convert_watch_number(anime_list):
    for anime in anime_list:
        if '萬' in anime['watch_number']:
            anime['watch_number'] = float(anime['watch_number'].replace('萬', '')) * 10000
        else:
            anime['watch_number'] = int(anime['watch_number'])
    return anime_list

def aggregate_anime_info(anime_list):
    anime_dict = {}
    for anime in anime_list:
        if anime['name'] in anime_dict:
            anime_dict[anime['name']]['watch_number'] += anime['watch_number']
        else:
            anime_dict[anime['name']] = anime
    return list(anime_dict.values())

def format_anime_info(anime_list, user_name):
    formatted_text = f"@{user_name} 您好(你好)\n揭曉今天播放次數最高的動畫排行榜 !\n\n"
    for i, anime in enumerate(anime_list, start=1):
        formatted_text += f"({i}) {anime['name']}\n"
        formatted_text += f"集數: {anime['episode']}\n"
        formatted_text += f"觀看次數: {int(anime['watch_number'])}\n"
        formatted_text += f"點我馬上看: {anime['link']}\n\n"
    return formatted_text.strip()

def get_anime_ranking(user_name):
    anime_list = scrape_anime_info()
    anime_list = convert_watch_number(anime_list)
    anime_list = aggregate_anime_info(anime_list)
    anime_list = sorted(anime_list, key=lambda x: x['watch_number'], reverse=True)
    formatted_text = format_anime_info(anime_list, user_name)
    return formatted_text
# 在 main 函数中调用 scrape_anime_info 函数
def main():
    anime_list = scrape_anime_info()
    anime_list = convert_watch_number(anime_list)
    anime_list = aggregate_anime_info(anime_list)
    anime_list = sorted(anime_list, key=lambda x: x['watch_number'], reverse=True)

    formatted_text = format_anime_info(anime_list)
    print(formatted_text)

if __name__ == "__main__":
    main()

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

    if event.message.text == "ACG展覽資訊":
        print("ACG展覽資訊 button clicked")
        reply_message = TextSendMessage(
            text=f"@{user_name} 您好📣，想了解ACG（A：動漫、C：漫畫、G：電玩）的展覽資訊嗎？請選擇您想了解的相關資訊吧！",
            quick_reply=QuickReply(
                items=[
                    QuickReplyButton(action=MessageAction(label="A：動漫", text="A：動漫")),
                    QuickReplyButton(action=MessageAction(label="C：漫畫", text="C：漫畫")),
                    QuickReplyButton(action=MessageAction(label="G：電玩", text="G：電玩"))
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, reply_message)
    elif event.message.text == "A：動漫":
        print("A:動漫 button clicked")
        anime_events_info = scrape_anime_events_with_images()
        if anime_events_info:
            carousel = generate_anime_event_carousel(anime_events_info)
            line_bot_api.reply_message(
                event.reply_token,
                FlexSendMessage(alt_text="Anime展覽資訊", contents=carousel)
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="抱歉，無法獲取Anime動漫展的資訊。😢")
            )

    elif event.message.text == "愛看啥類別":
        print("愛看啥類別 button clicked")
        reply_message = TextSendMessage(
            text=f"@{user_name} 您好😄，想觀看什麼類型的動漫呢？請選取您想觀看的類型吧！",
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
            _, sampled_rows = parse_csv_data(csv_data, event.message.text)
            user_data[user_id]['seen'] = [row[0] for row in sampled_rows]
            user_data[user_id]['count'] += len(sampled_rows)

            columns = []
            for row in sampled_rows:
                name, popularity, date, url, img = row
                column = CarouselColumn(
                    thumbnail_image_url=img,
                    title=popularity[:40],  # 標題最多40個字元
                    text=f"人氣: {name}\n上架時間: {date}",
                    actions=[URIAction(label='觀看連結', uri=url)]
                )
                columns.append(column)

            carousel_template = CarouselTemplate(columns=columns)
            template_message = TemplateSendMessage(
                alt_text='推薦動漫',
                template=carousel_template
            )
            line_bot_api.reply_message(event.reply_token, template_message)
            # 追加詢問是否想再看更多動漫
            confirm_template = ConfirmTemplate(
                text="還要再看五部動漫嗎？",
                actions=[
                    MessageAction(label="是", text="是"),
                    MessageAction(label="否", text="否")
                ]
            )
            confirm_message = TemplateSendMessage(
                alt_text='還要再看五部動漫嗎？',
                template=confirm_template
            )
            line_bot_api.push_message(user_id, confirm_message)
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="抱歉，無法獲取動漫資料。😢"))
    elif event.message.text == "是":
        category = user_data[user_id].get('category')
        seen = user_data[user_id].get('seen', [])
        count = user_data[user_id].get('count', 0)
        if category:
            url = f"https://raw.githubusercontent.com/weichen1357/linebot_openai/master/{category}.csv"
            csv_data = fetch_csv_data(url)
            if csv_data:
                message, sampled_rows = parse_csv_data(csv_data, category, exclude_list=seen, start_index=count + 1)
                user_data[user_id]['seen'].extend([row[0] for row in sampled_rows])
                user_data[user_id]['count'] += len(sampled_rows)
                
                columns = []
                for row in sampled_rows:
                    name, popularity, date, url, img = row
                    column = CarouselColumn(
                        thumbnail_image_url=img,
                        title=popularity[:40],  # 標題最多40個字元
                        text=f"人氣: {name}\n上架時間: {date}",
                        actions=[URIAction(label='觀看連結', uri=url)]
                    )
                    columns.append(column)

                carousel_template = CarouselTemplate(columns=columns)
                template_message = TemplateSendMessage(
                    alt_text='推薦動漫',
                    template=carousel_template
                )
                # 追加詢問是否想再看更多動漫
                confirm_template = ConfirmTemplate(
                    text="還要再看五部動漫嗎？",
                    actions=[
                        MessageAction(label="是", text="是"),
                        MessageAction(label="否", text="否")
                    ]
                )
                confirm_message = TemplateSendMessage(
                    alt_text='還要再看五部動漫嗎？',
                    template=confirm_template
                )
                # 不需要傳 message，只傳多頁訊息
                line_bot_api.reply_message(event.reply_token, [
                    template_message,
                    confirm_message
                ])
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="抱歉，無法獲取動漫資料。😢"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請先選擇一個類別。"))

    elif event.message.text == "否":
        category = user_data[user_id].get('category')
        if category:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"感謝您的使用😊。如果想再看其他類型的動漫，請點擊「愛看啥類別」來選擇其他類別吧！"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請先選擇一個類別。"))
    elif event.message.text == "今天來看啥":
        print("今天來看啥 button clicked")
        categories = ["王道", "校園", "戀愛", "運動", "喜劇", "異世界"]
        random_category = random.choice(categories)
        url = f"https://raw.githubusercontent.com/weichen1357/linebot_openai/master/{random_category}.csv"
        csv_data = fetch_csv_data(url)
        if csv_data:
            message = parse_single_csv_data(csv_data, random_category, user_name)
            reply_message = TextSendMessage(text=message + " 🎬")
            line_bot_api.reply_message(event.reply_token, reply_message)
            return  # 在這裡加上 return，確保在推薦完動漫後立即返回，避免執行下面的程式碼段
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"抱歉，無法獲取隨機推薦的番剧列表。😢"))

    elif event.message.text == "本季度新番":
        print("本季度新番 button clicked")
        reply_message = TextSendMessage(
            text="@{} 您好，請選擇年份".format(user_name),
            quick_reply=QuickReply(
                items=[
                    QuickReplyButton(action=MessageAction(label="2023", text="2023")),
                    QuickReplyButton(action=MessageAction(label="2024", text="2024"))
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, reply_message)
    elif event.message.text == "2023" or event.message.text == "2024":
        print("Year selected:", event.message.text)
        user_data[user_id]['year'] = event.message.text  # 將選擇的年份存儲到 user_data 中
        if event.message.text == "2023":
            seasons = ["冬", "春", "夏", "秋"]
        else:
            seasons = ["冬", "春"]

        quick_reply_items = [QuickReplyButton(action=MessageAction(label=season, text=season)) for season in seasons]
        reply_message = TextSendMessage(
            text="@{} 您好，接著請選擇季度項目".format(user_name),
            quick_reply=QuickReply(items=quick_reply_items)
        )
        line_bot_api.reply_message(event.reply_token, reply_message)

    elif event.message.text in ["冬", "春", "夏", "秋"]:
        print("Season selected:", event.message.text)
        year = user_data[user_id].get('year')  # 獲取用戶選擇的年份
        season_dict = {"冬": "winter", "春": "spring", "夏": "summer", "秋": "fall"}
        season = season_dict[event.message.text]
        url = f"https://myanimelist.net/anime/season/{year}/{season}"
        anime_list = scrape_anime_season(url)

        if anime_list:
            # 從提供的動漫列表中隨機選擇五部動漫
            sampled_anime = random.sample(anime_list, min(5, len(anime_list)))

            columns = []
            for anime in sampled_anime:
                column = CarouselColumn(
                    thumbnail_image_url=anime['image_url'],
                    title=anime['title'][:40],  # 標題最多40個字元
                    text=f"評分: {anime.get('score', 'N/A')}\n上架時間: {anime.get('release_date', 'N/A')}",
                    actions=[URIAction(label='觀看連結', uri=anime['link'])]
                )
                columns.append(column)

            carousel_template = CarouselTemplate(columns=columns)
            template_message = TemplateSendMessage(
                alt_text=f'{year}年{event.message.text}季度新番',
                template=carousel_template
            )
            line_bot_api.reply_message(event.reply_token, template_message)
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"抱歉，無法獲取{year}年{season_dict[event.message.text]}季度的番劇列表。😢"))
    elif event.message.text == "播放排行榜":
        print("播放排行榜 button clicked")
        anime_list = scrape_anime_info()
        anime_list = convert_watch_number(anime_list)
        anime_list = aggregate_anime_info(anime_list)
        anime_list = sorted(anime_list, key=lambda x: x['watch_number'], reverse=True)
        formatted_text = format_anime_info(anime_list, user_name)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text = formatted_text))
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
