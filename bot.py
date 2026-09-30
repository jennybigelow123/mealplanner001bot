import os
import logging
import sqlite3
import random
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ============================================================
# CONFIG
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise SystemExit("❌ BOT_TOKEN is missing. Set it in Railway → Variables.")

DB_PATH = "meals.db"
DEFAULT_TZ = "Africa/Lagos"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ============================================================
# MEAL DATABASE (No external API — built-in)
# ============================================================
BREAKFASTS = [
    {"name": "Oatmeal with banana & honey", "note": "Slow carbs + natural sweetness. Add nuts for protein."},
    {"name": "Scrambled eggs + whole wheat toast", "note": "High protein start. Add avocado for healthy fats."},
    {"name": "Greek yogurt + berries + granola", "note": "Probiotics + antioxidants. Great for gut health."},
    {"name": "Smoothie: spinach, mango, banana, milk", "note": "Drink your greens. Add peanut butter for protein."},
    {"name": "Boiled eggs + fruit + tea", "note": "Simple, quick, filling. Perfect for busy mornings."},
    {"name": "Pancakes with fruit topping", "note": "Weekend treat. Use whole wheat flour for more fiber."},
    {"name": "Akara + pap (ogi)", "note": "Classic Nigerian breakfast. Protein from beans."},
    {"name": "Bread + peanut butter + banana", "note": "Fast, affordable, and energy-boosting."},
    {"name": "Custard + milk + bread", "note": "Warm and easy. Add a boiled egg for protein."},
    {"name": "Tea + sandwich (egg or tuna)", "note": "Balanced and portable — great for commuters."},
    {"name": "Fruit bowl + yogurt", "note": "Light and refreshing. Add seeds for crunch."},
    {"name": "Moi moi + pap", "note": "Steamed bean pudding — protein-rich and filling."},
    {"name": "Porridge (oats or millet)", "note": "Warm, comforting, easy on the stomach."},
    {"name": "Toasted bread + butter + fried egg", "note": "Simple classic. Add tomato slices for freshness."},
]

LUNCHES = [
    {"name": "Rice + beans + stew + plantain", "note": "Balanced plate: carbs, protein, and potassium."},
    {"name": "Jollof rice + grilled chicken + salad", "note": "Add salad for fiber. Chicken for lean protein."},
    {"name": "Beans porridge + bread", "note": "Cheap, protein-rich, and very filling."},
    {"name": "Eba + egusi soup + vegetables", "note": "Hearty and traditional. Load up on greens."},
    {"name": "Pounded yam + vegetable soup", "note": "Energy-packed. Watch the portion size."},
    {"name": "Fried rice + beef + coleslaw", "note": "Veggies already in the rice — add coleslaw for crunch."},
    {"name": "Spaghetti + tomato sauce + chicken", "note": "Quick, kid-friendly, and satisfying."},
    {"name": "Yam + egg sauce", "note": "Simple and nutritious. Add pepper for flavor."},
    {"name": "Amala + ewedu + gbegiri", "note": "Rich in iron. Great for energy."},
    {"name": "Salad bowl + grilled fish", "note": "Light lunch. Add boiled eggs for protein."},
    {"name": "Ofada rice + ayamase + beef", "note": "Local favorite. Full of flavor."},
    {"name": "Chicken wrap + fruit", "note": "Portable and balanced. Great for workdays."},
    {"name": "Semo + ogbono soup", "note": "Warm and filling. Add fish for omega-3."},
    {"name": "Rice + stew + fish + veggies", "note": "Classic plate. Keep veggies generous."},
]

DINNERS = [
    {"name": "Vegetable soup + wheat", "note": "Light dinner. Easy on digestion before sleep."},
    {"name": "Grilled fish + roasted potatoes + greens", "note": "Omega-3 + fiber. Light and satisfying."},
    {"name": "Pepper soup + rice", "note": "Warming and light. Great when you feel tired."},
    {"name": "Chicken stew + boiled yam", "note": "Comforting and filling. Portion wisely at night."},
    {"name": "Beans + plantain (dodo)", "note": "Protein + potassium. A classic evening combo."},
    {"name": "Cabbage stew + rice", "note": "Low-calorie and filling. Add fish or chicken."},
    {"name": "Okra soup + eba", "note": "Rich in fiber. Good for digestion."},
    {"name": "Noodles + egg + vegetables", "note": "Quick dinner. Add carrots and peas for balance."},
    {"name": "Fish pepper soup + bread", "note": "Light and warming. Great for cold evenings."},
    {"name": "Chicken salad + boiled egg", "note": "Low-carb, high-protein. Perfect light dinner."},
    {"name": "Beans + corn + plantain", "note": "Balanced and filling. Great vegetarian option."},
    {"name": "Steamed veggies + grilled chicken", "note": "Clean and light. Best dinner for weight goals."},
    {"name": "Soup + semo (light portion)", "note": "Warm comfort. Keep the portion moderate at night."},
    {"name": "Egg sauce + boiled potatoes", "note": "Simple, light, and ready in 15 minutes."},
]

# ============================================================
# TIPS — DAILY NUTRITION & PLANNING ADVICE
# ============================================================
MORNING_TIPS = [
    "🌅 *Start with water.* A glass before breakfast wakes up your metabolism.",
    "🍳 *Eat protein at breakfast.* Eggs, beans, or yogurt keep you full till lunch.",
    "🥣 *Don't skip breakfast.* Even a small one prevents overeating later.",
    "🍌 *Add fruit* to breakfast — natural sugar beats processed sugar.",
    "☕ *Coffee is fine* — just drink water alongside it.",
    "🥜 *Nuts & seeds* are great morning toppings. Small handful = big nutrition.",
    "🍞 *Choose whole grains* over white bread when you can.",
    "🍵 *Green tea* is a gentle morning boost — try it once this week.",
    "🧘 *Eat slowly.* Your brain needs 20 minutes to feel full.",
    "📝 *Check today's plan* before you start cooking — avoid last-minute takeout.",
]

MIDDAY_TIPS = [
    "🍽️ *Balanced plate rule:* ½ veggies, ¼ protein, ¼ carbs.",
    "💧 *Drink water before lunch.* It reduces overeating.",
    "🥗 *Add color* to your plate — the more colors, the more nutrients.",
    "🚶 *Walk 5 minutes* after eating to help digestion.",
    "🍎 *Fruit is a perfect snack* — better than biscuits or chips.",
    "🐟 *Eat fish 2–3 times a week* for omega-3 and brain health.",
    "🧂 *Go easy on salt.* Use herbs, pepper, and garlic for flavor.",
    "🥤 *Skip sugary drinks.* Water, zobo (no sugar), or fresh juice is better.",
    "🍛 *Watch portions,* not just foods. Half a plate is often enough.",
    "🥕 *Snack smart:* carrots, groundnuts, or yogurt beat pastries.",
]

EVENING_TIPS = [
    "🌙 *Eat dinner 2–3 hours before bed* — easier digestion and better sleep.",
    "🥗 *Keep dinner light.* Soup, veggies, or grilled protein works best.",
    "🍵 *Herbal tea* after dinner helps relaxation — try chamomile or ginger.",
    "🚫 *Avoid heavy fried food* at night — it disrupts sleep.",
    "🍽️ *Plan tomorrow's meals tonight.* 5 minutes now saves you tomorrow.",
    "🛒 *Write your grocery list* before bed — shop with purpose, not impulse.",
    "💧 *Sip water* in the evening, but don't gulp right before sleep.",
    "🥜 *If you must snack,* choose nuts, yogurt, or fruit — not chips.",
    "🧊 *Prep ahead:* soak beans, chop veggies, or marinate meat tonight.",
    "📊 *Review your day:* did you eat balanced? Adjust tomorrow.",
]

# ============================================================
# DATABASE
# ============================================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            timezone TEXT DEFAULT 'Africa/Lagos',
            daily_time TEXT DEFAULT '07:00',
            meals_per_day INTEGER DEFAULT 3,
            joined_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            week_of TEXT,
            plan_json TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def register_user(user):
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE user_id=?", (user.id,))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (user_id, username, first_name, joined_at) VALUES (?,?,?,?)",
            (user.id, user.username or "", user.first_name or "", datetime.utcnow().isoformat()),
        )
        conn.commit()
    conn.close()

def get_user(user_id):
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT timezone, daily_time, meals_per_day FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row

def update_user(user_id, field, value):
    if field not in ("timezone", "daily_time", "meals_per_day"):
        return
    conn = db()
    cur = conn.cursor()
    cur.execute(f"UPDATE users SET {field}=? WHERE user_id=?", (value, user_id))
    conn.commit()
    conn.close()

def save_plan(user_id, plan, week_of):
    import json
    conn = db()
    cur = conn.cursor()
    cur.execute("DELETE FROM plans WHERE user_id=? AND week_of=?", (user_id, week_of))
    cur.execute(
        "INSERT INTO plans (user_id, week_of, plan_json, created_at) VALUES (?,?,?,?)",
        (user_id, week_of, json.dumps(plan), datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()

def all_users():
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT user_id, timezone, daily_time FROM users")
    rows = cur.fetchall()
    conn.close()
    return rows

# ============================================================
# MEAL PLAN GENERATION
# ============================================================
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def generate_weekly_plan(meals_per_day: int = 3):
    """Build a 7-day plan with no repeated meal within the week."""
    breakfast_pool = random.sample(BREAKFASTS, 7)
    lunch_pool = random.sample(LUNCHES, 7)
    dinner_pool = random.sample(DINNERS, 7)

    plan = {}
    for i, day in enumerate(DAYS):
        day_plan = {"breakfast": breakfast_pool[i]}
        if meals_per_day >= 2:
            day_plan["lunch"] = lunch_pool[i]
        if meals_per_day >= 3:
            day_plan["dinner"] = dinner_pool[i]
        plan[day] = day_plan
    return plan

def format_daily_plan(day: str, day_plan: dict) -> str:
    msg = f"🍽️ *{day}'s Meal Plan*\n\n"
    if "breakfast" in day_plan:
        b = day_plan["breakfast"]
        msg += f"🌅 *Breakfast:* {b['name']}\n_{b['note']}_\n\n"
    if "lunch" in day_plan:
        l = day_plan["lunch"]
        msg += f"🍛 *Lunch:* {l['name']}\n_{l['note']}_\n\n"
    if "dinner" in day_plan:
        d = day_plan["dinner"]
        msg += f"🌙 *Dinner:* {d['name']}\n_{d['note']}_\n\n"
    return msg

def format_full_week(plan: dict) -> str:
    msg = "📅 *Your Week's Meal Plan*\n\n"
    for day in DAYS:
        msg += f"*{day}*\n"
        dp = plan[day]
        if "breakfast" in dp:
            msg += f"  🌅 {dp['breakfast']['name']}\n"
        if "lunch" in dp:
            msg += f"  🍛 {dp['lunch']['name']}\n"
        if "dinner" in dp:
            msg += f"  🌙 {dp['dinner']['name']}\n"
        msg += "\n"
    return msg

def get_tip(period: str) -> str:
    if period == "morning":
        return random.choice(MORNING_TIPS)
    if period == "midday":
        return random.choice(MIDDAY_TIPS)
    return random.choice(EVENING_TIPS)

# ============================================================
# COMMANDS
# ============================================================
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user)

    welcome = (
        f"👋 *Welcome, {user.first_name}!*\n\n"
        "I'm *MealPlannerBot* — your weekly meal planning assistant.\n\n"
        "*What I do:*\n"
        "• 📅 Build a balanced 7-day meal plan\n"
        "• 🍽️ Suggest breakfast, lunch, and dinner daily\n"
        "• 💡 Send nutrition tips 3x a day\n"
        "• 🛒 Help you plan and shop smarter\n\n"
        "*Commands:*\n"
        "/plan — Generate a new weekly plan\n"
        "/today — See today's meals\n"
        "/tomorrow — Preview tomorrow\n"
        "/week — Show the full 7-day plan\n"
        "/resend — Send today's meals again\n"
        "/tip — Get a nutrition tip now\n"
        "/settings — Timezone, daily time, meals/day\n"
        "/help — Show this menu\n\n"
        "Let's make eating well simple! 🥗"
    )
    await update.message.reply_text(welcome, parse_mode=ParseMode.MARKDOWN)

    # Generate a plan immediately
    plan = generate_weekly_plan(3)
    week_of = datetime.utcnow().date().isoformat()
    save_plan(user.id, plan, week_of)
    await update.message.reply_text(
        "🎉 I've created your first weekly plan!\n\n" + format_full_week(plan),
        parse_mode=ParseMode.MARKDOWN,
    )


async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start(update, ctx)


async def plan_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    row = get_user(update.effective_user.id)
    mpd = row[2] if row else 3
    plan = generate_weekly_plan(mpd)
    week_of = datetime.utcnow().date().isoformat()
    save_plan(update.effective_user.id, plan, week_of)
    await update.message.reply_text(
        "🆕 *Fresh weekly plan created!*\n\n" + format_full_week(plan),
        parse_mode=ParseMode.MARKDOWN,
    )


async def week_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    week_of = datetime.utcnow().date().isoformat()
    # regenerate if missing
    row = get_user(update.effective_user.id)
    mpd = row[2] if row else 3
    plan = generate_weekly_plan(mpd)
    save_plan(update.effective_user.id, plan, week_of)
    await update.message.reply_text(
        format_full_week(plan), parse_mode=ParseMode.MARKDOWN
    )


async def today_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await send_today_meals(update.effective_user.id, ctx.application)


async def tomorrow_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tomorrow_index = (datetime.utcnow().weekday() + 1) % 7
    day = DAYS[tomorrow_index]
    plan = generate_weekly_plan(3)
    await update.message.reply_text(
        format_daily_plan(day, plan[day]), parse_mode=ParseMode.MARKDOWN
    )


async def resend_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await send_today_meals(update.effective_user.id, ctx.application)


async def tip_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    hour = datetime.now().hour
    if hour < 12:
        period = "morning"
    elif hour < 18:
        period = "midday"
    else:
        period = "evening"
    await update.message.reply_text(get_tip(period), parse_mode=ParseMode.MARKDOWN)


async def settings_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🌍 Timezone", callback_data="set_tz")],
        [InlineKeyboardButton("⏰ Daily plan time", callback_data="set_time")],
        [InlineKeyboardButton("🍽️ Meals per day", callback_data="set_mpd")],
    ]
    await update.message.reply_text(
        "⚙️ *Settings*\n\nChoose what to update:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN,
    )


async def settings_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "set_tz":
        ctx.user_data["awaiting"] = "set_tz"
        await query.message.reply_text(
            "Send your timezone like:\n`Africa/Lagos`\n`Europe/London`\n`America/New_York`",
            parse_mode=ParseMode.MARKDOWN,
        )
    elif data == "set_time":
        ctx.user_data["awaiting"] = "set_time"
        await query.message.reply_text(
            "Send daily plan time in 24h format like `07:00` or `18:30`.",
            parse_mode=ParseMode.MARKDOWN,
        )
    elif data == "set_mpd":
        ctx.user_data["awaiting"] = "set_mpd"
        await query.message.reply_text(
            "How many meals per day do you want planned?\nReply with `1`, `2`, or `3`.",
            parse_mode=ParseMode.MARKDOWN,
        )


async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    awaiting = ctx.user_data.get("awaiting")
    if not awaiting:
        return
    text = update.message.text.strip()
    uid = update.effective_user.id

    if awaiting == "set_tz":
        try:
            ZoneInfo(text)
        except Exception:
            await update.message.reply_text("❌ Invalid timezone. Try `Africa/Lagos`.", parse_mode=ParseMode.MARKDOWN)
            return
        update_user(uid, "timezone", text)
        await update.message.reply_text(f"✅ Timezone set to *{text}*", parse_mode=ParseMode.MARKDOWN)

    elif awaiting == "set_time":
        try:
            datetime.strptime(text, "%H:%M")
        except ValueError:
            await update.message.reply_text("❌ Use 24h format like `07:00`.", parse_mode=ParseMode.MARKDOWN)
            return
        update_user(uid, "daily_time", text)
        await update.message.reply_text(f"✅ Daily plan time set to *{text}*", parse_mode=ParseMode.MARKDOWN)

    elif awaiting == "set_mpd":
        if text not in ("1", "2", "3"):
            await update.message.reply_text("❌ Reply with 1, 2, or 3.", parse_mode=ParseMode.MARKDOWN)
            return
        update_user(uid, "meals_per_day", int(text))
        await update.message.reply_text(f"✅ Meals per day set to *{text}*", parse_mode=ParseMode.MARKDOWN)

    ctx.user_data["awaiting"] = None
    schedule_user_jobs(ctx.application, uid)


# ============================================================
# DAILY SENDER
# ============================================================
async def send_today_meals(user_id: int, app: Application):
    row = get_user(user_id)
    mpd = row[2] if row else 3
    day = DAYS[datetime.utcnow().weekday()]
    plan = generate_weekly_plan(mpd)
    week_of = datetime.utcnow().date().isoformat()
    save_plan(user_id, plan, week_of)

    msg = format_daily_plan(day, plan[day])
    msg += "\n" + get_tip("morning")

    try:
        await app.bot.send_message(user_id, msg, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.warning(f"Send failed for {user_id}: {e}")


async def midday_job(app: Application, user_id: int):
    try:
        await app.bot.send_message(
            user_id,
            "🍽️ *Midday Nutrition Tip*\n\n" + get_tip("midday"),
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        logger.warning(f"Midday failed for {user_id}: {e}")


async def evening_job(app: Application, user_id: int):
    try:
        tomorrow_index = (datetime.utcnow().weekday() + 1) % 7
        day = DAYS[tomorrow_index]
        plan = generate_weekly_plan(3)
        msg = (
            "🌙 *Evening Tip*\n\n"
            + get_tip("evening")
            + "\n\n🔮 *Tomorrow's Meals Preview*\n\n"
            + format_daily_plan(day, plan[day])
        )
        await app.bot.send_message(user_id, msg, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.warning(f"Evening failed for {user_id}: {e}")


def schedule_user_jobs(app: Application, user_id: int):
    row = get_user(user_id)
    if not row:
        return
    tz_name, daily_time, _ = row
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo(DEFAULT_TZ)

    scheduler: AsyncIOScheduler = app.bot_data["scheduler"]

    for suffix in ("daily", "midday", "evening"):
        jid = f"{user_id}_{suffix}"
        if scheduler.get_job(jid):
            scheduler.remove_job(jid)

    h, m = map(int, daily_time.split(":"))

    scheduler.add_job(
        send_today_meals, "cron", hour=h, minute=m,
        args=[app, user_id], id=f"{user_id}_daily",
        replace_existing=True, timezone=tz,
    )
    scheduler.add_job(
        midday_job, "cron", hour=13, minute=0,
        args=[app, user_id], id=f"{user_id}_midday",
        replace_existing=True, timezone=tz,
    )
    scheduler.add_job(
        evening_job, "cron", hour=20, minute=30,
        args=[app, user_id], id=f"{user_id}_evening",
        replace_existing=True, timezone=tz,
    )


async def post_init(app: Application):
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.start()
    app.bot_data["scheduler"] = scheduler
    for (uid, *_rest) in all_users():
        schedule_user_jobs(app, uid)
    logger.info("Scheduler started.")


# ============================================================
# MAIN
# ============================================================
def main():
    init_db()
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("plan", plan_cmd))
    app.add_handler(CommandHandler("week", week_cmd))
    app.add_handler(CommandHandler("today", today_cmd))
    app.add_handler(CommandHandler("tomorrow", tomorrow_cmd))
    app.add_handler(CommandHandler("resend", resend_cmd))
    app.add_handler(CommandHandler("tip", tip_cmd))
    app.add_handler(CommandHandler("settings", settings_cmd))

    app.add_handler(CallbackQueryHandler(settings_callback, pattern="^set_"))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("MealPlannerBot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
