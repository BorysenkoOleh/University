import asyncio
import threading
import uuid

import requests
import telebot
import websockets
from telebot import types

# ====== Налаштування ======
BOT_TOKEN = "8259909402:AAExHPRjNDxZiGht-Z4qbaPe_4yUjLztYSQ"
TMDB_KEY = "74d7571526e56a878ef44722c9be2c19"
HOST = "https://movie-bot--shu1red1eye.replit.app"  # Замініть на свій хост де лежить webapp.html
WS_PORT = 8765

bot = telebot.TeleBot(BOT_TOKEN)

# ====== Збереження даних ======
user_videos = {}
rooms = {}  # room_id: set of websocket connections

# ====== Меню ======
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔎 Пошук", "⭐ Популярні фільми")
    kb.add("📺 Популярні серіали", "▶️ Мої відео")
    kb.add("👥 Дивитись разом")
    kb.add("❓ Допомога")
    return kb

HELP_TEXT = (
    "🎬 *Мультимедійний кіно-бот*\n\n"
    "Можливості:\n"
    "- Пошук фільмів/серіалів\n"
    "- Перегляд трейлерів прямо в Telegram\n"
    "- Перегляд власних завантажених відео\n"
    "- Дивитись разом через Web App\n"
    "Просто обери пункт меню або напиши назву!"
)

# ====== TMDB API ======
def tmdb_search(query):
    url = "https://api.themoviedb.org/3/search/multi"
    raw = requests.get(url, params={
        "api_key": TMDB_KEY,
        "query": query,
        "language": "uk-UA"
    }).json().get("results", [])
    results = []
    for m in raw:
        poster = m.get("poster_path")
        poster_url = f"https://image.tmdb.org/t/p/w500{poster}" if poster else None
        results.append({
            "title": m.get("title") or m.get("name"),
            "overview": m.get("overview"),
            "rating": m.get("vote_average"),
            "year": (m.get("release_date") or m.get("first_air_date") or "")[:4],
            "poster": poster_url,
            "media_type": m.get("media_type"),
            "id": m.get("id")
        })
    return results

def tmdb_trailers(media_type, media_id):
    url = f"https://api.themoviedb.org/3/{media_type}/{media_id}/videos"
    return requests.get(url, params={"api_key": TMDB_KEY}).json().get("results", [])

# ====== Telegram обробники ======
@bot.message_handler(commands=['start', 'help'])
def start(message):
    bot.send_message(message.chat.id, HELP_TEXT, reply_markup=main_menu(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: True, content_types=['text'])
def handler(message):
    text = message.text.strip()

    if text == "❓ Допомога":
        bot.send_message(message.chat.id, HELP_TEXT, parse_mode="Markdown")

    elif text == "▶️ Мої відео":
        vidos = user_videos.get(message.chat.id, [])
        if not vidos:
            bot.send_message(message.chat.id, "У тебе ще немає завантажених відео.")
        else:
            bot.send_message(message.chat.id, "Твої відео:")
            for vid in vidos:
                bot.send_video(message.chat.id, vid)

    elif text == "⭐ Популярні фільми":
        url = "https://api.themoviedb.org/3/movie/popular"
        data = requests.get(url, params={"api_key": TMDB_KEY, "language": "uk-UA"}).json()["results"][:5]
        msg = "⭐ Популярні фільми:\n\n" + "\n".join([f"{m['title']} — ⭐{m['vote_average']}" for m in data])
        bot.send_message(message.chat.id, msg)

    elif text == "📺 Популярні серіали":
        url = "https://api.themoviedb.org/3/tv/popular"
        data = requests.get(url, params={"api_key": TMDB_KEY, "language": "uk-UA"}).json()["results"][:5]
        msg = "📺 Популярні серіали:\n\n" + "\n".join([f"{m['name']} — ⭐{m['vote_average']}" for m in data])
        bot.send_message(message.chat.id, msg)

    elif text == "🔎 Пошук":
        bot.send_message(message.chat.id, "Введи назву фільму або серіалу ✍️")

    elif text == "👥 Дивитись разом":
        room_id = str(uuid.uuid4())[:8]
        kb = types.InlineKeyboardMarkup()
        url = f"{HOST}/webapp.html?room={room_id}"
        kb.add(types.InlineKeyboardButton("▶️ Відкрити кімнату", web_app=types.WebAppInfo(url=url)))
        bot.send_message(message.chat.id, f"👥 Кімната створена! ID: `{room_id}`", reply_markup=kb, parse_mode="Markdown")
        rooms[room_id] = set()  # створюємо порожню кімнату для WebSocket

    else:
        results = tmdb_search(text)
        if not results:
            bot.send_message(message.chat.id, "Не знайдено ❌")
            return
        item = results[0]
        title = item["title"]
        year = item["year"]
        overview = item["overview"] or "Опис недоступний."
        rating = item["rating"]
        poster = item["poster"]
        media_type = item["media_type"]
        media_id = item["id"]
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("▶️ Трейлер", callback_data=f"trailer:{media_type}:{media_id}"))
        text_msg = f"*{title}* ({year})\n⭐ *Рейтинг:* {rating}\n\n{overview}"
        if poster:
            bot.send_photo(message.chat.id, poster, caption=text_msg[:1000], parse_mode="Markdown", reply_markup=kb)
        else:
            bot.send_message(message.chat.id, text_msg[:1000], parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    data = call.data.split(":")
    if data[0] == "trailer":
        _, media_type, media_id = data
        vidos = tmdb_trailers(media_type, media_id)
        yt = [v for v in vidos if v["site"] == "YouTube"]
        if yt:
            video_key = yt[0]["key"]
            url = f"https://www.youtube.com/watch?v={video_key}"
            bot.send_message(call.message.chat.id, f"▶️ Трейлер:\n{url}")
        else:
            bot.send_message(call.message.chat.id, "Трейлер не знайдено.")

@bot.message_handler(content_types=['video'])
def save_user_video(message):
    file_id = message.video.file_id
    user_videos.setdefault(message.chat.id, []).append(file_id)
    bot.send_message(message.chat.id, "🎉 Відео збережено!")

# ====== WebSocket сервер ======
async def ws_handler(ws):
    query = ws.path.split("?room=")
    if len(query) < 2:
        await ws.close()
        return
    room_id = query[1]
    if room_id not in rooms:
        rooms[room_id] = set()
    rooms[room_id].add(ws)
    try:
        async for msg in ws:
            for client in rooms[room_id]:
                if client != ws:
                    await client.send(msg)
    finally:
        rooms[room_id].remove(ws)


# noinspection PyTypeChecker
def start_ws_server():
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    server = websockets.serve(ws_handler, "0.0.0.0", WS_PORT)
    loop.run_until_complete(server)
    print(f"WebSocket сервер запущено на порту {WS_PORT}")
    loop.run_forever()

# ====== Запуск ======
if __name__ == "__main__":
    ws_thread = threading.Thread(target=start_ws_server)
    ws_thread.start()
    print("Бот запущено!")
    bot.polling(none_stop=True)
