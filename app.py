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
from google.cloud import vision
import io
import sqlite3




app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

user_data = {}

service_account_key = "your-service-account-file(1).json"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = service_account_key

# Google Vision API client
client = vision.ImageAnnotatorClient()

def test_vision_api(image_path):
    with io.open(image_path, 'rb') as image_file:
        content = image_file.read()
    image = vision.Image(content=content)

    # 設置 LanguageHints 參數為中文
    image_context = vision.ImageContext(language_hints=['zh'])

    response = client.label_detection(image=image, image_context=image_context)
    labels = response.label_annotations

    label_descriptions = [label.description for label in labels]
    return label_descriptions

def search_database(label_descriptions):
    conn = sqlite3.connect('anime_characters.db')
    cursor = conn.cursor()

    query = "SELECT name, anime, url, about FROM characters"
    cursor.execute(query)
    results = cursor.fetchall()

    matching_results = []
    for row in results:
        name, anime, url, about = row
        if any(keyword in about for keyword in label_descriptions):
            matching_results.append((name, anime, url))

    conn.close()
    return matching_results

def setup_database():
    conn = sqlite3.connect('anime_characters.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            anime TEXT NOT NULL,
            url TEXT NOT NULL,
            about TEXT
        )
    ''')

    cursor.executemany('''
        INSERT INTO characters (name, anime, url, about)
        VALUES (?, ?, ?, ?)
    ''', [
       ('五條悟', '咒術迴戰', 'https://m.manhuagui.com/comic/28004/', 'Long hair'),
        ('多啦A夢', '多啦A夢', 'https://www.ofiii.com/section/114', 'Graphics'),
        ('桐谷和人', '刀劍神域', 'https://ani.gamer.com.tw/animeVideo.php?sn=926', 'Cg artwork'),
        ('工藤新一', '名偵探柯南', 'https://ani.gamer.com.tw/animeVideo.php?sn=30234', 'Chin'),
        ('魯夫', '航海王', 'https://gimy.ai/eps/252248-4-1020.html', 'Mammal'),
        ('鳴人', '火影忍者', 'https://ani.gamer.com.tw/animeVideo.php?sn=16844', 'Font'),
    ])

    conn.commit()
    conn.close()

# 設置資料庫
setup_database()



def fetch_top_watched_anime():
    csv_url = "https://raw.githubusercontent.com/weichen1357/linebot_openai/master/2024-05-28_anime_rankings.csv"
    try:
        response = requests.get(csv_url)
        response.raise_for_status()  # 檢查是否有錯誤發生
        csv_content = response.text
        # 解析 CSV 檔案
        csv_reader = csv.reader(csv_content.splitlines())
        next(csv_reader)  # 跳過標題行
        rows = [row for row in csv_reader if len(row) == 4]  # 避免空數據行
        # 按照 "Watch Number" 排序，取前五高的動畫資訊
        sorted_rows = sorted(rows, key=lambda x: float(x[1]), reverse=True)[:5]
        message = "以下是本日播放次數前五名的動畫排行榜📊:\n\n"
        for index, row in enumerate(sorted_rows, start=1):
            name, watch_number, episode, link = row
            message += f"{index}. 『{name}』\n👀 觀看人數: {watch_number}\n🎬 集數: {episode}\n🔗 連結:\n{link}\n\n"
        return message
    except requests.exceptions.RequestException as e:
        print("Error fetching top watched anime:", e)
        return None




def fetch_game_expo_info():
    url = 'https://tgs.tca.org.tw/news_list.php?a=2&b=c'
    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        news_spans = soup.find_all('span', class_='news_txt')

        message = "以下是近期Games電玩展覽的資訊🎮:\n\n"
        for index, news_span in enumerate(news_spans[:5], start=1):
            news_link = news_span.find('a')
            news_title = news_link.text.strip()
            news_url = "https://tgs.tca.org.tw/" + news_link['href']
            date_text = news_span.find_next_sibling('span').text.strip()

            message += f"{index}.📰 {news_title}\n📅 日期: {date_text}\n🔗 了解更多:\nhttps://tgs.tca.org.tw/{news_url}\n\n"

        return message
    else:
        return f'无法访问网页。状态码: {response.status_code}'


def fetch_comic_info():
    url = 'https://www.ccpa.org.tw/comic/index.php?tpl=12'
    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        target_divs = soup.find_all('div', class_='col-12 col-sm-6 col-md-6', style='padding:0 0 50px 0')

        message = "以下是近期的Comics漫畫展的資訊📚:\n\n"
        for index, div in enumerate(target_divs[:5]):
            title_tag = div.find('span', class_='rwd_font_navi_type3_2')
            title = title_tag.text if title_tag else 'N/A'

            info_spans = div.find_all('span', class_='rwd_font_navi_type3_1')
            date = info_spans[0].text if len(info_spans) > 0 else 'N/A'
            publisher = info_spans[1].text if len(info_spans) > 1 else 'N/A'

            link_tag = div.find('a')
            link = urljoin(url, link_tag['href']) if link_tag else 'N/A'
            message += f"{index + 1}.📝 {title}\n📅 日期: {date}\n🏢 出版社: {publisher}\n🔗 了解更多:\n{link}\n\n"
        
        return message
    else:
        return f'無法獲取網頁內容。狀態碼: {response.status_code}'


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
def crawl_anime_events():
    url = "https://www.e-muse.com.tw/zh/news/latest-news/events/"

    try:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            news_items = soup.find_all(class_="item article_item sr_bottom")

            message = "以下是近期Anime動漫展的資訊🎉:\n\n"
            for index, item in enumerate(news_items, start=1):
                # 提取title txt-bold
                title_element = item.find(class_="title")
                title_text = title_element.get_text(strip=True)

                # 提取時間:date
                time_element = item.find(class_="date")
                time_text = time_element.find(class_="txt-semibold").get_text(strip=True)

                # 提取了解更多:href
                learn_more_link = item['href']

                # 格式化输出信息
                message += f"{index}. 『{title_text}』\n🗓時間: {time_text}\n🔗點我了解更多:\n{learn_more_link}\n"

            return message
        else:
            return "無法獲取資料"
    except Exception as e:
        return "發生錯誤: " + str(e)



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
        print("A：動漫 button clicked")
        anime_events_info = crawl_anime_events()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"@{user_name} 您好，{anime_events_info}")
        )
    elif event.message.text == "C：漫畫":
        message = fetch_comic_info()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=message))

    elif event.message.text == "G：電玩":
        game_expo_info = fetch_game_expo_info()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=game_expo_info)
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
                    text=f"上架時間: {anime.get('release_date', 'N/A')}",
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
        top_watched_anime = fetch_top_watched_anime()
        if top_watched_anime:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=top_watched_anime))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="抓取動畫排行榜時出錯。請稍後再試。"))
    elif event.message.text == "拍照搜一下":
        profile = line_bot_api.get_profile(event.source.user_id)
        user_name = profile.display_name
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="＠{user_name}您好,想看卻不知道是什麼動漫名稱嗎？上傳圖片由我們來替你解答吧！"
            )
        )
    else:
        print("Other message received: " + event.message.text)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="我不明白你的意思，可以再說一遍嗎？🤔"))
        
@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    message_content = line_bot_api.get_message_content(event.message.id)
    image_path = f"/tmp/{event.message.id}.jpg"

    with open(image_path, 'wb') as fd:
        for chunk in message_content.iter_content():
            fd.write(chunk)

    label_descriptions = test_vision_api(image_path)
    if label_descriptions:
        results = search_database(label_descriptions)
        if results:
            response_text = "\n".join([f"此動漫人物是『{name}』，出自『{anime}』\n以下是觀賞連結🔗：{url}" for name, anime, url in results])
        else:
            response_text = "未找到該角色的相關資訊。"
    else:
        response_text = "未能識別該圖像中的角色。"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=response_text)
    )

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
