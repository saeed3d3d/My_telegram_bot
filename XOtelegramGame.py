import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    ContextTypes, ConversationHandler, MessageHandler, filters
)

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# حالت‌های گفتگو
WAITING_FOR_PLAYER, PLAYING = range(2)

class TicTacToeGame:
    def __init__(self, player1, player2):
        self.player1 = player1  # کاربر اول
        self.player2 = player2  # کاربر دوم
        self.board = ['⬜'] * 9  # صفحه بازی
        self.current_player = player1  # بازیکن فعلی
        self.symbols = {player1: '❌', player2: '⭕'}  # نمادها
        self.game_over = False
        self.winner = None

    def make_move(self, position, player_id):
        """انجام حرکت"""
        if self.game_over or player_id != self.current_player:
            return False, "نوبت تو نیست یا بازی تمام شده!"
        
        if self.board[position] != '⬜':
            return False, "این خانه قبلاً انتخاب شده!"
        
        # انجام حرکت
        self.board[position] = self.symbols[player_id]
        
        # بررسی برنده
        if self.check_winner():
            self.game_over = True
            self.winner = player_id
            return True, f"🎉 {self.symbols[player_id]} برنده شد!"
        
        # بررسی تساوی
        if '⬜' not in self.board:
            self.game_over = True
            return True, "⚡ بازی مساوی شد!"
        
        # تغییر نوبت
        self.current_player = self.player2 if self.current_player == self.player1 else self.player1
        return True, None

    def check_winner(self):
        """بررسی برنده"""
        lines = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],  # سطرها
            [0, 3, 6], [1, 4, 7], [2, 5, 8],  # ستون‌ها
            [0, 4, 8], [2, 4, 6]              # قطرها
        ]
        
        for line in lines:
            if (self.board[line[0]] == self.board[line[1]] == self.board[line[2]] != '⬜'):
                return True
        return False

    def get_board_display(self):
        """نمایش صفحه بازی"""
        board_text = ""
        for i in range(0, 9, 3):
            row = "".join(self.board[i:i+3])
            board_text += f"{row}\n"
        return board_text

    def get_keyboard(self):
        """ایجاد کیبورد بازی"""
        keyboard = []
        for i in range(0, 9, 3):
            row = []
            for j in range(3):
                pos = i + j
                row.append(InlineKeyboardButton(self.board[pos], callback_data=f"move_{pos}"))
            keyboard.append(row)
        
        # دکمه‌های کنترل
        keyboard.append([
            InlineKeyboardButton("🔄 بازی جدید", callback_data="new_game"),
            InlineKeyboardButton("❌ پایان بازی", callback_data="end_game")
        ])
        return InlineKeyboardMarkup(keyboard)

# دیکشنری برای ذخیره بازی‌های فعال
active_games = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور شروع"""
    user = update.effective_user
    await update.message.reply_text(
        f"سلام {user.first_name}! 👋\n"
        "برای شروع بازی XO از دستور /newgame استفاده کن\n\n"
        "📖 دستورات:\n"
        "/newgame - شروع بازی جدید\n"
        "/help - راهنما"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور راهنما"""
    help_text = """
🎮 **راهنمای بازی XO**

📝 **نحوه بازی:**
- بازی بین دو بازیکن انجام میشه
- بازیکن اول: ❌
- بازیکن دوم: ⭕
- به نوبت روی خانه‌ها کلیک کنید

⚡ **دستورات:**
/newgame - شروع بازی جدید
/help - نمایش این راهنما

🏆 **قوانین:**
اولین کسی که ۳ نماد خودش رو در یک ردیف بچینه برنده میشه
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def new_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع بازی جدید"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # اگر بازی فعال وجود دارد
    if chat_id in active_games:
        await update.message.reply_text(
            "⚠️ یک بازی در حال انجام وجود داره!\n"
            "لطفا صبر کنید تا بازی تمام شود یا از /cancel استفاده کنید."
        )
        return
    
    # ایجاد بازی جدید
    game = {
        'creator': user.id,
        'player1': user.id,
        'player2': None,
        'message_id': None
    }
    active_games[chat_id] = game
    
    keyboard = [
        [InlineKeyboardButton("🎮 من بازی میکنم!", callback_data="join_game")],
        [InlineKeyboardButton("❌ لغو", callback_data="cancel_game")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = await update.message.reply_text(
        f"🎮 بازی جدید XO\n"
        f"سازنده: {user.first_name}\n\n"
        f"⏳ منتظر بازیکن دوم...\n"
        f"برای پیوستن به بازی روی دکمه زیر کلیک کن:",
        reply_markup=reply_markup
    )
    
    game['message_id'] = message.message_id

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت کلیک روی دکمه‌ها"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    
    # پیوستن به بازی
    if query.data == "join_game":
        await join_game(query, chat_id, user, message_id)
    
    # لغو بازی
    elif query.data == "cancel_game":
        await cancel_game(query, chat_id)
    
    # حرکت در بازی
    elif query.data.startswith("move_"):
        await make_move(query, chat_id, user, message_id)
    
    # بازی جدید
    elif query.data == "new_game":
        await new_game_after_finish(query, chat_id)
    
    # پایان بازی
    elif query.data == "end_game":
        await end_game(query, chat_id)

async def join_game(query, chat_id, user, message_id):
    """پیوستن بازیکن دوم به بازی"""
    if chat_id not in active_games:
        await query.edit_message_text("⏰ زمان بازی تمام شده!")
        return
    
    game = active_games[chat_id]
    
    # بررسی اگر کاربر سازنده بازی است
    if user.id == game['creator']:
        await query.answer("شما سازنده بازی هستید!", show_alert=True)
        return
    
    # بررسی اگر بازی قبلاً شروع شده
    if game['player2'] is not None:
        await query.answer("بازی قبلاً شروع شده!", show_alert=True)
        return
    
    # اضافه کردن بازیکن دوم
    game['player2'] = user.id
    
    # شروع بازی واقعی
    tic_tac_toe = TicTacToeGame(game['player1'], game['player2'])
    active_games[chat_id]['game'] = tic_tac_toe
    
    # نمایش صفحه بازی
    player1_name = (await query.bot.get_chat(game['player1'])).first_name
    player2_name = user.first_name
    
    board_text = tic_tac_toe.get_board_display()
    message_text = (
        f"🎮 بازی XO شروع شد!\n\n"
        f"❌ {player1_name}\n"
        f"⭕ {player2_name}\n\n"
        f"نوبت: {player1_name} (❌)\n\n"
        f"{board_text}"
    )
    
    await query.edit_message_text(
        message_text,
        reply_markup=tic_tac_toe.get_keyboard()
    )

async def cancel_game(query, chat_id):
    """لغو بازی"""
    if chat_id in active_games:
        creator_id = active_games[chat_id]['creator']
        if query.from_user.id == creator_id:
            del active_games[chat_id]
            await query.edit_message_text("❌ بازی لغو شد!")
        else:
            await query.answer("فقط سازنده بازی می‌تواند لغو کند!", show_alert=True)

async def make_move(query, chat_id, user, message_id):
    """انجام حرکت در بازی"""
    if chat_id not in active_games or 'game' not in active_games[chat_id]:
        await query.edit_message_text("⏰ بازی پیدا نشد!")
        return
    
    game = active_games[chat_id]['game']
    position = int(query.data.split('_')[1])
    
    success, message = game.make_move(position, user.id)
    
    if not success:
        await query.answer(message, show_alert=True)
        return
    
    # به روزرسانی صفحه بازی
    player1_name = (await query.bot.get_chat(game.player1)).first_name
    player2_name = (await query.bot.get_chat(game.player2)).first_name
    
    board_text = game.get_board_display()
    
    if game.game_over:
        # بازی تمام شده
        if game.winner:
            winner_name = player1_name if game.winner == game.player1 else player2_name
            message_text = (
                f"🏆 بازی تمام شد!\n\n"
                f"🎉 برنده: {winner_name} {game.symbols[game.winner]}\n\n"
                f"{board_text}\n\n"
                f"برای بازی جدید کلیک کن:"
            )
        else:
            message_text = (
                f"⚡ بازی مساوی شد!\n\n"
                f"{board_text}\n\n"
                f"برای بازی جدید کلیک کن:"
            )
        
        # حذف بازی از لیست فعال
        del active_games[chat_id]
        
        keyboard = [[InlineKeyboardButton("🔄 بازی جدید", callback_data="new_game")]]
        await query.edit_message_text(
            message_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        # بازی ادامه دارد
        current_player_name = player1_name if game.current_player == game.player1 else player2_name
        current_symbol = game.symbols[game.current_player]
        
        message_text = (
            f"🎮 بازی XO\n\n"
            f"❌ {player1_name}\n"
            f"⭕ {player2_name}\n\n"
            f"نوبت: {current_player_name} ({current_symbol})\n\n"
            f"{board_text}"
        )
        
        await query.edit_message_text(
            message_text,
            reply_markup=game.get_keyboard()
        )

async def new_game_after_finish(query, chat_id):
    """شروع بازی جدید پس از اتمام"""
    await query.edit_message_text("برای شروع بازی جدید از دستور /newgame استفاده کن!")

async def end_game(query, chat_id):
    """پایان دادن به بازی"""
    if chat_id in active_games:
        # بررسی اگر کاربر در بازی است
        game = active_games[chat_id]['game']
        if query.from_user.id in [game.player1, game.player2]:
            del active_games[chat_id]
            await query.edit_message_text("❌ بازی به پایان رسید!")
        else:
            await query.answer("شما در این بازی نیستید!", show_alert=True)

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور لغو"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    if chat_id in active_games:
        game = active_games[chat_id]
        if user.id == game['creator']:
            del active_games[chat_id]
            await update.message.reply_text("❌ بازی لغو شد!")
        else:
            await update.message.reply_text("فقط سازنده بازی می‌تواند لغو کند!")
    else:
        await update.message.reply_text("هیچ بازی فعالی وجود ندارد!")

def main():
    """تابع اصلی"""
    # توکن ربات خودت رو اینجا قرار بده
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
    
    # ساخت اپلیکیشن
    application = Application.builder().token(BOT_TOKEN).build()
    
    # اضافه کردن هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("newgame", new_game))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # شروع ربات
    print("🤖 ربات XO فعال شد...")
    application.run_polling()

if __name__ == '__main__':
    main()