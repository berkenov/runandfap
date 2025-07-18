from config import BOT_TOKEN
from aiogram import Bot, Dispatcher, types, executor
from datetime import datetime, date
from db import init_db, ensure_user, add_run, get_user_stats, get_user_history, get_leaderboard

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

tracked_groups = set()


def is_group_chat(message: types.Message):
    return message.chat.type in ["group", "supergroup"]


import asyncio
from datetime import datetime, date
from db import (
    init_db, ensure_user, add_run, get_user_stats, 
    get_user_history, get_leaderboard, get_all_users_in_group, get_users_with_runs_today
)

# ...

async def daily_reminder():
    """Фоновая задача: каждый день в 19:00 напоминает о пробежке"""
    while True:
        now = datetime.now()
        target = now.replace(hour=19, minute=0, second=0, microsecond=0)
        if now > target:
            # если уже позже 19:00, ждём до завтра
            target = target.replace(day=now.day + 1)
        wait_seconds = (target - now).total_seconds()
        await asyncio.sleep(wait_seconds)

        # Когда настало 19:00 – проверяем все группы
        for group_id in tracked_groups:
            await send_group_reminder(group_id)

async def send_group_reminder(group_id):
    # Все юзеры группы
    all_users = get_all_users_in_group(group_id)
    # Кто уже бегал сегодня
    ran_today = get_users_with_runs_today(group_id)

    # Фильтруем кто ещё не бегал
    not_ran = [u for u in all_users if u[0] not in ran_today]

    if not not_ran:
        await bot.send_message(group_id, "🔥 Все сегодня уже бегали! Красава!")
        return

    mentions = []
    for user_id, username in not_ran:
        if username:
            mentions.append(f"@{username}")
        else:
            mentions.append(f"[пользователь](tg://user?id={user_id})")

    text = "🕖 Уже 19:00! Сегодня ещё не бегали:\n" + ", ".join(mentions) + "\n\nНе фапайте – бегите!"
    await bot.send_message(group_id, text, parse_mode="Markdown")



HELP_TEXT = (
    "🏃 *RundOrFap* — бот для учёта пробежек в группе.\n\n"
    "Он хранит результаты *только для этой группы*.\n\n"
    "Доступные команды:\n"
    "/run <км> <мин:сек> — добавить пробежку\n"
    "/stats — твоя статистика\n"
    "/history — последние 5 пробежек\n"
    "/leaderboard — рейтинг группы\n"
    "/help — показать эту подсказку\n\n"
    "_Добавляй пробежки, соревнуйся с друзьями и не фапай вместо бега!_"
)

@dp.message_handler(commands=['start', 'help'])
async def start(message: types.Message):
    if not is_group_chat(message):
        return
    await message.answer(HELP_TEXT, parse_mode="Markdown")

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    if not is_group_chat(message):
        return
    await message.answer(
        "🏃 RundOrFap активен!\n"
        "Добавляйте пробежки: /run <км> <мин:сек>\n"
        "Статистика: /stats\n"
        "История: /history\n"
        "Лидерборд: /leaderboard\n\n"
        "Все данные сохраняются **только для этой группы**."
    )

@dp.message_handler(commands=['run'])
async def cmd_run(message: types.Message):
    if not is_group_chat(message):
        return
    group_id = message.chat.id
    user_id = message.from_user.id
    username = message.from_user.full_name

    # Убираем запятые -> точки
    text = message.text.replace(",", ".").strip()
    # Ожидаем: /run 5.6 за 22.4
    parts = text.split()

    if len(parts) < 3 or parts[2] != "за":
        await message.reply("Формат: /run <км> за <минуты>\nНапример: /run 5.6 за 22.4")
        return

    try:
        distance = float(parts[1])  # километры
        time_part = parts[3]        # время (может быть 22 или 22.4 или 27:30)

        if ":" in time_part:
            # формат минут:секунд
            mm, ss = time_part.split(":")
            duration = int(mm) * 60 + int(ss)
        else:
            # формат с десятичными минутами
            minutes_float = float(time_part)
            full_seconds = int(minutes_float * 60)
            duration = full_seconds
    except Exception as e:
        await message.reply("Ошибка формата. Примеры:\n/run 5.6 за 22.4\n/run 7 за 30\n/run 5.6 за 27:30")
        return

    ensure_user(group_id, user_id, username)
    add_run(group_id, user_id, username, distance, duration)

    # человеко-читаемый вывод
    m = duration // 60
    s = duration % 60
    # темп (мин/км)
    pace_sec_per_km = duration / distance
    pace_m = int(pace_sec_per_km // 60)
    pace_s = int(pace_sec_per_km % 60)

    await message.answer(
        f"✅ {username} добавил {distance} км за {m}:{s:02d}\n"
        f"Темп: {pace_m}:{pace_s:02d} мин/км"
    )
    tracked_groups.add(message.chat.id)


@dp.message_handler(commands=['stats'])
async def cmd_stats(message: types.Message):
    if not is_group_chat(message):
        return
    group_id = message.chat.id
    user_id = message.from_user.id

    stats = get_user_stats(group_id, user_id)
    if not stats or stats[0] == 0:
        await message.answer(f"{message.from_user.full_name}, у тебя ещё нет пробежек в этой группе!")
        return

    count, total_distance, total_duration = stats
    avg_pace = total_duration / total_distance if total_distance else 0
    min_per_km = int(avg_pace // 60)
    sec_per_km = int(avg_pace % 60)

    await message.answer(
        f"🏃 {message.from_user.full_name}\n"
        f"Пробежек: {count}\n"
        f"Общая дистанция: {total_distance:.1f} км\n"
        f"Средний темп: {min_per_km}:{sec_per_km:02d} мин/км"
    )
    tracked_groups.add(message.chat.id)

@dp.message_handler(commands=['history'])
async def cmd_history(message: types.Message):
    if not is_group_chat(message):
        return
    group_id = message.chat.id
    user_id = message.from_user.id

    rows = get_user_history(group_id, user_id)
    if not rows:
        await message.answer("Нет пробежек.")
        return

    text = f"📜 Последние пробежки {message.from_user.full_name}:\n"
    for d, dur, date in rows:
        m = dur // 60
        s = dur % 60
        text += f"{date[:10]} — {d} км за {m}:{s:02d}\n"
    await message.answer(text)

@dp.message_handler(commands=['leaderboard'])
async def cmd_leaderboard(message: types.Message):
    if not is_group_chat(message):
        return
    group_id = message.chat.id

    rows = get_leaderboard(group_id)
    if not rows:
        await message.answer("Пока никто не бегал в этой группе.")
        return

    text = "🏆 Лидерборд группы:\n"
    for i, (user, km) in enumerate(rows, start=1):
        text += f"{i}. {user} — {km:.1f} км\n"
    await message.answer(text)
    tracked_groups.add(message.chat.id)


if __name__ == "__main__":
    init_db()
    loop = asyncio.get_event_loop()
    loop.create_task(daily_reminder())  # запускаем фоновый пинг
    executor.start_polling(dp, skip_updates=True)
