import logging
import sqlite3
import os
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================== LOGGING ==================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ================== KONFIGURACJA ==================
ADMIN_CHANNEL_ID = -1002920830504
GROUP_LINK = "https://t.me/rozpierdool"
ADMIN_ID = 6396391785
USERS_FILE = "users.txt"
PENDING_FILE = "pending.txt"
TOKEN = "8332772493:AAGJ-D302EpgCgLzJLKCxDiaGFZGpKBnV0A"

# ================== BAZA DANYCH ==================
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance REAL DEFAULT 0,
    total_earnings REAL DEFAULT 0
)
"""
)
conn.commit()


def save_user(user_id):
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users = f.read().splitlines()
    else:
        users = []
    if str(user_id) not in users:
        users.append(str(user_id))
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(users))


def remove_user(user_id):
    cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users = f.read().splitlines()
        users = [u for u in users if u != str(user_id)]
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(users))


def add_balance(user_id, amount):
    cursor.execute(
        "UPDATE users SET balance = balance + ?, total_earnings = total_earnings + ? WHERE user_id = ?",
        (amount * 0.8, amount, user_id),
    )
    conn.commit()


def get_user(user_id):
    cursor.execute(
        "SELECT balance, total_earnings FROM users WHERE user_id = ?", (user_id,)
    )
    return cursor.fetchone()


# ================== FUNKCJE POMOCNICZE ==================
def user_exists(user_id):
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return str(user_id) in f.read().splitlines()
    return False


def save_pending(user_id, username):
    if os.path.exists(PENDING_FILE):
        with open(PENDING_FILE, "r", encoding="utf-8") as f:
            pending = f.read().splitlines()
    else:
        pending = []
    if str(user_id) not in pending:
        pending.append(str(user_id))
        with open(PENDING_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(pending))


def remove_pending(user_id):
    if os.path.exists(PENDING_FILE):
        with open(PENDING_FILE, "r", encoding="utf-8") as f:
            pending = f.read().splitlines()
        pending = [u for u in pending if u != str(user_id)]
        with open(PENDING_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(pending))


# ================== HANDLERY ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user.id)

    balance, total = get_user(user.id)

    text = (
        f"👋 Witaj {user.mention_html()}!\n\n"
        f"💰 Twój całkowity zysk: <b>{total:.2f} PLN</b>\n"
        f"💵 Twoje saldo do wypłaty: <b>{balance:.2f} PLN</b>\n\n"
        f"📄 Pobieramy 20%. Ty dostajesz 80%.\n\n"
        f"Aby dołączyć do bota, wpisz /dolacz ✅"
    )

    keyboard = [
        [InlineKeyboardButton("💸 Wypłać balans", callback_data="wyplata")],
        [InlineKeyboardButton("💳 Wpłać BLIK", callback_data="blik")],
        [InlineKeyboardButton("📢 Moja grupa", url=GROUP_LINK)],
    ]

    await update.message.reply_photo(
        photo=open("welcome.jpg", "rb"),
        caption=text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user

    parts = text.split()
    if len(parts) == 2 and parts[0].isdigit() and parts[1].replace(".", "", 1).isdigit():
        code, amount = parts
        msg = (
            f"💳 Nowy kod BLIK od {user.mention_html()}:\n\n"
            f"🔑 Kod: <b>{code}</b>\n"
            f"💵 Kwota: <b>{amount} PLN</b>"
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ Akceptuj", callback_data=f"accept_{user.id}_{amount}"
                    ),
                    InlineKeyboardButton(
                        "❌ Odrzuć", callback_data=f"reject_{user.id}"
                    ),
                ]
            ]
        )

        await update.message.reply_text("✅ Kod został zapisany i wysłany do adminów.")
        await context.bot.send_message(
            chat_id=ADMIN_CHANNEL_ID,
            text=msg,
            parse_mode="HTML",
            reply_markup=keyboard,
        )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data_parts = query.data.split("_")

    if query.data == "blik":
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="💳 Wybrałeś BLIK. Wyślij kod i kwotę, np.: 123456 200.00",
        )
        return

    elif query.data == "wyplata":
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="💸 Napisz do @yzekk lub @Imperator66",
        )
        return

    if len(data_parts) == 3 and data_parts[0] == "accept":
        _, user_id, amount = data_parts
        add_balance(int(user_id), float(amount))
        await context.bot.send_message(
            chat_id=int(user_id),
            text=f"✅ Twój kod został zaakceptowany! Dodano <b>{float(amount)*0.8:.2f} PLN</b> do salda.",
            parse_mode="HTML",
        )
        await query.edit_message_text(
            f"✅ Kod zaakceptowany. Użytkownik {user_id} dostał {float(amount)*0.8:.2f} PLN"
        )
    elif len(data_parts) == 2:
        action, user_id = data_parts
        user_id = int(user_id)
        if action == "accept":
            save_user(user_id)
            remove_pending(user_id)
            try:
                await context.bot.send_message(chat_id=user_id, text="✅ Zostałeś zaakceptowany!")
            except Exception as e:
                print(f"Nie można wysłać wiadomości do {user_id}: {e}")
            await query.edit_message_text(f"✅ Użytkownik {user_id} został zaakceptowany.")
        elif action == "reject":
            remove_pending(user_id)
            try:
                await context.bot.send_message(chat_id=user_id, text="❌ Twoja prośba została odrzucona.")
            except Exception as e:
                print(f"Nie można wysłać wiadomości do {user_id}: {e}")
            await query.edit_message_text(f"❌ Użytkownik {user_id} został odrzucony.")


# ================== KOMENDA /dolacz ==================
async def dolacz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user_exists(user.id):
        await update.message.reply_text("✅ Jesteś już zaakceptowany.")
        return

    save_pending(user.id, user.username or user.first_name)

    keyboard = [[
        InlineKeyboardButton("✅ Akceptuj", callback_data=f"accept_{user.id}"),
        InlineKeyboardButton("❌ Odrzuć", callback_data=f"reject_{user.id}")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=ADMIN_CHANNEL_ID,
        text=f"📥 Nowa prośba o dołączenie:\nUżytkownik: @{user.username or user.first_name}\nID: {user.id}",
        reply_markup=reply_markup
    )
    await update.message.reply_text("⏳ Twoje zgłoszenie zostało wysłane na kanał. Czekaj na akceptację.")


# ================== KOMENDA /kick ==================
async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Nie masz uprawnień.")
        return
    if not context.args:
        await update.message.reply_text("❌ Użycie: /kick <ID użytkownika>")
        return

    user_id = int(context.args[0])
    remove_user(user_id)
    remove_pending(user_id)
    try:
        await context.bot.send_message(chat_id=user_id, text="❌ Zostałeś usunięty z bota.")
    except Exception:
        pass
    await update.message.reply_text(f"✅ Użytkownik {user_id} został usunięty.")


# ================== KOMENDA /sendall ==================
async def send_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Nie masz uprawnień.")
        return
    if not context.args:
        await update.message.reply_text("❌ Użycie: /sendall <wiadomość>")
        return

    message = " ".join(context.args)
    if not os.path.exists(USERS_FILE):
        await update.message.reply_text("❌ Brak zaakceptowanych użytkowników.")
        return

    with open(USERS_FILE, "r", encoding="utf-8") as f:
        users = f.read().splitlines()

    sent = 0
    for user_id in users:
        try:
            await context.bot.send_message(chat_id=int(user_id), text=message)
            sent += 1
        except Exception:
            pass
    await update.message.reply_text(f"✅ Wiadomość wysłana do {sent} użytkowników.")


# ================== MAIN ==================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("dolacz", dolacz))
    app.add_handler(CommandHandler("kick", kick))
    app.add_handler(CommandHandler("sendall", send_all))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()


if __name__ == "__main__":
    main()
