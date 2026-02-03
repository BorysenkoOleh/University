import telebot
import requests
from telebot import types

BOT_TOKEN = "8259909402:AAExHPRjNDxZiGht-Z4qbaPe_4yUjLztYSQ"
TMDB_KEY  = "74d7571526e56a878ef44722c9be2c19"

bot = telebot.TeleBot(BOT_TOKEN)

def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔎 Пошук", "⭐ Популярні фільми")
    kb.add("📺 Популярні серіали", "▶️ Мої відео")
    kb.add("❓ Допомога")
    return kb


HELP_TEXT = (
    "🎬 *Мультимедійний кіно-бот*\n\n"
    "Можливості:\n"
    "Пошук фільмів/серіалів\n"
    "Перегляд трейлерів прямо в Telegram\n"
    "Де можна легально дивитися (Netflix, Megogo, Disney+...)\n"
    "Перегляд власних завантажених відео\n"
    "Просто обери пункт меню або напиши назву!"
)
user_videos = {}

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

def tmdb_watch_providers(media_type, media_id):
    url = f"https://api.themoviedb.org/3/{media_type}/{media_id}/watch/providers"
    return requests.get(url, params={"api_key": TMDB_KEY}).json().get("results", {})

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

        text = f"*{title}* ({year})\n⭐ *Рейтинг:* {rating}\n\n{overview}"

        if poster:
            bot.send_photo(
                message.chat.id,
                poster,
                caption=text,
                parse_mode="Markdown",
                reply_markup=kb
            )
        else:
            bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=kb)


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

    bot.send_message(message.chat.id, "🎉 Відео збережено! Тепер ти можеш переглядати його в меню '▶️ Мої відео'.")

print("Бот запущено!")
bot.polling(none_stop=True)
