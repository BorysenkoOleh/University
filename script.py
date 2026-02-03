import telebot
import requests
from telebot import types

BOT_TOKEN = "8259909402:AAExHPRjNDxZiGht-Z4qbaPe_4yUjLztYSQ"
TMDB_KEY  = "74d7571526e56a878ef44722c9be2c19"

bot = telebot.TeleBot(BOT_TOKEN)

# =================== МЕНЮ ===================
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔎 Пошук", "⭐ Популярні фільми")
    kb.add("📺 Популярні серіали", "▶️ Мої відео")
    kb.add("❓ Допомога")
    return kb


HELP_TEXT = (
    "🎬 *Мультимедійний кіно-бот*\n\n"
    "Можливості:\n"
    "🔹 Пошук фільмів/серіалів\n"
    "🔹 Перегляд трейлерів прямо в Telegram\n"
    "🔹 Де можна легально дивитися (Netflix, Megogo, Disney+...)\n"
    "🔹 Перегляд власних завантажених відео\n"
    "🔹 Показ відкритих (public-domain) відео\n\n"
    "Просто обери пункт меню або напиши назву!"
)

# Сховище користувацьких відео
user_videos = {}   # chat_id: [file_id1, file_id2, ...]


# =================== API TMDb ===================
def tmdb_search(query):
    url = "https://api.themoviedb.org/3/search/multi"
    return requests.get(url, params={
        "api_key": TMDB_KEY,
        "query": query,
        "language": "uk-UA"
    }).json().get("results", [])


def tmdb_trailers(media_type, media_id):
    url = f"https://api.themoviedb.org/3/{media_type}/{media_id}/videos"
    return requests.get(url, params={"api_key": TMDB_KEY}).json().get("results", [])


def tmdb_watch_providers(media_type, media_id):
    url = f"https://api.themoviedb.org/3/{media_type}/{media_id}/watch/providers"
    return requests.get(url, params={"api_key": TMDB_KEY}).json().get("results", {})


def public_domain_videos():
    # Пара прикладів абсолютно легальних відео
    return [
        {"title": "Sherlock Jr. (1924)", "url": "https://archive.org/download/SherlockJr/SherlockJr_512kb.mp4"},
        {"title": "Night of the Living Dead (1968)", "url": "https://archive.org/download/night_of_the_living_dead/night_of_the_living_dead.mp4"}
    ]


# =================== START ===================
@bot.message_handler(commands=['start', 'help'])
def start(message):
    bot.send_message(message.chat.id, HELP_TEXT, reply_markup=main_menu(), parse_mode="Markdown")


# =================== ОБРОБКА МЕНЮ ===================
@bot.message_handler(func=lambda m: True, content_types=['text'])
def handler(message):
    text = message.text.strip()

    if text == "❓ Допомога":
        bot.send_message(message.chat.id, HELP_TEXT, parse_mode="Markdown")

    elif text == "▶️ Мої відео":
        vids = user_videos.get(message.chat.id, [])
        if not vids:
            bot.send_message(message.chat.id, "У тебе ще немає завантажених відео.")
        else:
            bot.send_message(message.chat.id, "Твої відео:")
            for vid in vids:
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
        # ПОШУК
        results = tmdb_search(text)
        if not results:
            bot.send_message(message.chat.id, "Не знайдено ❌")
            return

        item = results[0]
        title = item.get("title") or item.get("name")
        year = (item.get("release_date") or item.get("first_air_date") or "—")[:4]
        overview = item.get("overview") or "Опис недоступний."
        rating = item.get("vote_average", "—")

        media_type = item["media_type"]
        media_id = item["id"]

        # кнопки ТРЕЙЛЕР + ДЕ ПОДИВИТИСЬ + PUBLIC DOMAIN
        kb = types.InlineKeyboardMarkup()

        kb.add(types.InlineKeyboardButton("▶️ Трейлер", callback_data=f"trailer:{media_type}:{media_id}"))
        kb.add(types.InlineKeyboardButton("📺 Де переглянути", callback_data=f"watch:{media_type}:{media_id}"))
        kb.add(types.InlineKeyboardButton("🎞 Відкриті фільми", callback_data="public"))

        bot.send_message(
            message.chat.id,
            f"*{title}* ({year})\n⭐ *Рейтинг:* {rating}\n\n{overview}",
            parse_mode="Markdown",
            reply_markup=kb
        )


# =================== CALLBACK (ТРЕЙЛЕР / ДЕ ПЕРЕГЛЯНУТИ / PUBLIC DOMAIN) ===================
@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    data = call.data.split(":")

    # PUBLIC DOMAIN
    if data[0] == "public":
        vids = public_domain_videos()
        for v in vids:
            bot.send_message(call.message.chat.id, f"🎞 {v['title']}")
            bot.send_video(call.message.chat.id, v['url'])
        return

    # ТРЕЙЛЕР
    if data[0] == "trailer":
        _, media_type, media_id = data
        vids = tmdb_trailers(media_type, media_id)

        yt = [v for v in vids if v["site"] == "YouTube"]
        if yt:
            video_key = yt[0]["key"]
            url = f"https://www.youtube.com/watch?v={video_key}"
            bot.send_message(call.message.chat.id, f"▶️ Трейлер:\n{url}")
        else:
            bot.send_message(call.message.chat.id, "Трейлер не знайдено.")

    # ДЕ ПЕРЕГЛЯНУТИ
    if data[0] == "watch":
        _, media_type, media_id = data
        providers = tmdb_watch_providers(media_type, media_id).get("UA", {})

        flatrate = providers.get("flatrate", [])
        rent = providers.get("rent", [])
        buy = providers.get("buy", [])

        msg = "📺 *Офіційні провайдери в Україні:*\n\n"

        if flatrate:
            msg += "🎟 Підписка:\n" + "\n".join([f"• {p['provider_name']}" for p in flatrate]) + "\n\n"
        if rent:
            msg += "💳 Оренда:\n" + "\n".join([f"• {p['provider_name']}" for p in rent]) + "\n\n"
        if buy:
            msg += "🛒 Купівля:\n" + "\n".join([f"• {p['provider_name']}" for p in buy]) + "\n\n"

        bot.send_message(call.message.chat.id, msg or "Немає даних.", parse_mode="Markdown")


# =================== КОРИСТУВАЦЬКІ ВІДЕО ===================
@bot.message_handler(content_types=['video'])
def save_user_video(message):
    file_id = message.video.file_id
    user_videos.setdefault(message.chat.id, []).append(file_id)

    bot.send_message(message.chat.id, "🎉 Відео збережено! Тепер ти можеш переглядати його в меню '▶️ Мої відео'.")


print("Бот запущено!")
bot.polling(none_stop=True)
