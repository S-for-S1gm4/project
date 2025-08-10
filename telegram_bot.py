import asyncio
import logging
import hashlib
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict
from core.auth import hash_password  # Добавить этот импорт
from core.exceptions import InvalidCredentialsException  # Добавить


from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, ConversationHandler
)

# Импорты наших сервисов
from services.user_service import UserService
from services.event_service import EventService
from database.config import get_settings

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем настройки
settings = get_settings()

# Константы для диалогов
REGISTRATION_EMAIL, REGISTRATION_USERNAME, REGISTRATION_PASSWORD = range(3)
LOGIN_EMAIL, LOGIN_PASSWORD = range(2)
ADD_BALANCE_AMOUNT = range(1)
CREATE_EVENT_TITLE, CREATE_EVENT_DESCRIPTION, CREATE_EVENT_COST = range(3)

# Хранилище сессий пользователей (в продакшене использовать Redis)
user_sessions: Dict[int, Dict] = {}

class EventPlannerBot:
    """Главный класс Telegram бота"""

    def __init__(self, token: str):
        self.token = token
        self.app = Application.builder().token(token).build()
        self.setup_handlers()

    def setup_handlers(self):
        """Настройка обработчиков команд и сообщений"""

        # Регистрация
        registration_handler = ConversationHandler(
            entry_points=[CommandHandler("register", self.start_registration)],
            states={
                REGISTRATION_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.registration_email)],
                REGISTRATION_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.registration_username)],
                REGISTRATION_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.registration_password)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)]
        )

        # Авторизация
        login_handler = ConversationHandler(
            entry_points=[CommandHandler("login", self.start_login)],
            states={
                LOGIN_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.login_email)],
                LOGIN_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.login_password)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)]
        )

        # Пополнение баланса
        balance_handler = ConversationHandler(
            entry_points=[CommandHandler("addbalance", self.start_add_balance)],
            states={
                ADD_BALANCE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_balance_amount)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)]
        )

        # Создание события
        create_event_handler = ConversationHandler(
            entry_points=[CommandHandler("createevent", self.start_create_event)],
            states={
                CREATE_EVENT_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.create_event_title)],
                CREATE_EVENT_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.create_event_description)],
                CREATE_EVENT_COST: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.create_event_cost)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)]
        )

        # Регистрируем обработчики
        self.app.add_handler(registration_handler)
        self.app.add_handler(login_handler)
        self.app.add_handler(balance_handler)
        self.app.add_handler(create_event_handler)

        # Простые команды
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("profile", self.profile))
        self.app.add_handler(CommandHandler("balance", self.balance))
        self.app.add_handler(CommandHandler("events", self.events))
        self.app.add_handler(CommandHandler("myevents", self.my_events))
        self.app.add_handler(CommandHandler("transactions", self.transactions))
        self.app.add_handler(CommandHandler("logout", self.logout))

        # Callback обработчики для inline кнопок
        self.app.add_handler(CallbackQueryHandler(self.button_callback))

        # Обработчик неизвестных команд
        self.app.add_handler(MessageHandler(filters.COMMAND, self.unknown_command))

    # =============================================================================
    # ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
    # =============================================================================

    def get_user_session(self, telegram_id: int) -> Optional[Dict]:
        """Получение сессии пользователя"""
        return user_sessions.get(telegram_id)

    def create_user_session(self, telegram_id: int, user_id: int, email: str) -> None:
        """Создание сессии пользователя"""
        user_sessions[telegram_id] = {
            'user_id': user_id,
            'email': email,
            'logged_in': True,
            'login_time': datetime.utcnow()
        }

    def clear_user_session(self, telegram_id: int) -> None:
        """Очистка сессии пользователя"""
        if telegram_id in user_sessions:
            del user_sessions[telegram_id]

    def require_auth(self, func):
        """Декоратор для проверки авторизации"""
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            telegram_id = update.effective_user.id
            session = self.get_user_session(telegram_id)

            if not session or not session.get('logged_in'):
                await update.message.reply_text(
                    "Ошибка: Вы не авторизованы. Используйте /login для входа в систему."
                )
                return

            return await func(update, context)
        return wrapper

    def get_main_menu_keyboard(self, authenticated: bool = False):
        """Создание главного меню"""
        if authenticated:
            keyboard = [
                [InlineKeyboardButton("Профиль", callback_data="profile")],
                [InlineKeyboardButton("Баланс", callback_data="balance")],
                [InlineKeyboardButton("События", callback_data="events")],
                [InlineKeyboardButton("Мои события", callback_data="myevents")],
                [InlineKeyboardButton("Транзакции", callback_data="transactions")],
                [InlineKeyboardButton("Выйти", callback_data="logout")]
            ]
        else:
            keyboard = [
                [InlineKeyboardButton("Войти", callback_data="login")],
                [InlineKeyboardButton("Регистрация", callback_data="register")],
                [InlineKeyboardButton("Посмотреть события", callback_data="events")]
            ]

        return InlineKeyboardMarkup(keyboard)

    # =============================================================================
    # ОСНОВНЫЕ КОМАНДЫ
    # =============================================================================

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        telegram_id = update.effective_user.id
        session = self.get_user_session(telegram_id)

        welcome_text = f"""
**Добро пожаловать в {settings.APP_NAME}!**

Я помогу вам управлять событиями, балансом и участием в мероприятиях.

{"Статус: Вы авторизованы" if session and session.get('logged_in') else "Статус: Вы не авторизованы"}

Выберите действие:
        """

        keyboard = self.get_main_menu_keyboard(session and session.get('logged_in'))

        await update.message.reply_text(
            welcome_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        help_text = """
**Доступные команды:**

**Без авторизации:**
• /start - Главное меню
• /register - Регистрация
• /login - Вход в систему
• /events - Просмотр событий

**После авторизации:**
• /profile - Ваш профиль
• /balance - Баланс счета
• /addbalance - Пополнить баланс
• /transactions - История транзакций
• /myevents - Мои события
• /createevent - Создать событие
• /logout - Выйти из системы

**Универсальные:**
• /help - Эта справка
• /cancel - Отменить текущую операцию

Совет: Используйте кнопки в меню для удобной навигации!
        """

        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик неизвестных команд"""
        await update.message.reply_text(
            "Неизвестная команда. Используйте /help для просмотра доступных команд."
        )

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена текущей операции"""
        await update.message.reply_text(
            "Операция отменена. Используйте /start для возврата в главное меню."
        )
        return ConversationHandler.END

    # =============================================================================
    # РЕГИСТРАЦИЯ
    # =============================================================================

    async def start_registration(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало регистрации"""
        await update.message.reply_text(
            "**Регистрация нового аккаунта**\n\n"
            "Введите ваш email адрес:",
            parse_mode='Markdown'
        )
        return REGISTRATION_EMAIL

    async def registration_email(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение email при регистрации"""
        email = update.message.text.strip()

        # Простая валидация email
        if '@' not in email or '.' not in email:
            await update.message.reply_text(
                "Некорректный email адрес. Попробуйте еще раз:"
            )
            return REGISTRATION_EMAIL

        context.user_data['registration_email'] = email
        await update.message.reply_text(
            f"Email: {email}\n\n"
            "Теперь введите желаемый username:"
        )
        return REGISTRATION_USERNAME

    async def registration_username(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение username при регистрации"""
        username = update.message.text.strip()

        if len(username) < 3:
            await update.message.reply_text(
                "Username должен содержать минимум 3 символа. Попробуйте еще раз:"
            )
            return REGISTRATION_USERNAME

        context.user_data['registration_username'] = username
        await update.message.reply_text(
            f"Username: {username}\n\n"
            "Теперь введите пароль (минимум 6 символов):"
        )
        return REGISTRATION_PASSWORD

    async def registration_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение пароля и завершение регистрации"""
        password = update.message.text.strip()

        if len(password) < 6:
            await update.message.reply_text(
                "Пароль должен содержать минимум 6 символов. Попробуйте еще раз:"
            )
            return REGISTRATION_PASSWORD

        try:
            # Создаем пользователя
            user = UserService.create_user(
                email=context.user_data['registration_email'],
                username=context.user_data['registration_username'],
                password=password,
                full_name=f"Telegram User {update.effective_user.first_name}"
            )

            # Автоматически авторизуем пользователя
            self.create_user_session(
                update.effective_user.id,
                user.id,
                user.email
            )

            await update.message.reply_text(
                f"**Регистрация успешна!**\n\n"
                f"Username: {user.username}\n"
                f"Email: {user.email}\n"
                f"Начальный баланс: ${user.balance}\n\n"
                f"Вы автоматически авторизованы в системе!",
                parse_mode='Markdown'
            )

            # Показываем главное меню
            keyboard = self.get_main_menu_keyboard(True)
            await update.message.reply_text(
                "Выберите действие:",
                reply_markup=keyboard
            )

        except ValueError as e:
            await update.message.reply_text(
                f"Ошибка регистрации: {str(e)}\n\n"
                "Используйте /register для повторной попытки."
            )
        except Exception as e:
            logger.error(f"Registration error: {e}")
            await update.message.reply_text(
                "Произошла ошибка при регистрации. Попробуйте позже."
            )

        # Очищаем временные данные
        context.user_data.clear()
        return ConversationHandler.END

    # =============================================================================
    # АВТОРИЗАЦИЯ
    # =============================================================================

    async def start_login(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало авторизации"""
        telegram_id = update.effective_user.id
        session = self.get_user_session(telegram_id)

        if session and session.get('logged_in'):
            await update.message.reply_text(
                "Вы уже авторизованы в системе!"
            )
            return ConversationHandler.END

        await update.message.reply_text(
            "**Вход в систему**\n\n"
            "Введите ваш email адрес:",
            parse_mode='Markdown'
        )
        return LOGIN_EMAIL

    async def login_email(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение email при авторизации"""
        email = update.message.text.strip()
        context.user_data['login_email'] = email

        await update.message.reply_text(
            f"Email: {email}\n\n"
            "Теперь введите пароль:"
        )
        return LOGIN_PASSWORD

    async def login_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение пароля и завершение авторизации"""
        password = update.message.text.strip()

        try:
            # Проверяем учетные данные
            user = UserService.get_user_by_email(context.user_data['login_email'])

            if not user:
                await update.message.reply_text(
                    "Пользователь с таким email не найден.\n"
                    "Используйте /register для регистрации."
                )
                context.user_data.clear()
                return ConversationHandler.END

            # Проверяем пароль
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            if user.hashed_password != hashed_password:
                await update.message.reply_text(
                    "Неверный пароль. Попробуйте еще раз:\n"
                    "Или используйте /cancel для отмены."
                )
                return LOGIN_PASSWORD

            if not user.is_active:
                await update.message.reply_text(
                    "Ваш аккаунт отключен. Обратитесь к администратору."
                )
                context.user_data.clear()
                return ConversationHandler.END

            # Создаем сессию
            self.create_user_session(
                update.effective_user.id,
                user.id,
                user.email
            )

            await update.message.reply_text(
                f"**Вход выполнен успешно!**\n\n"
                f"Добро пожаловать, {user.username}!\n"
                f"Ваш баланс: ${user.balance}\n"
                f"Роль: {user.role}",
                parse_mode='Markdown'
            )

            # Показываем главное меню
            keyboard = self.get_main_menu_keyboard(True)
            await update.message.reply_text(
                "Выберите действие:",
                reply_markup=keyboard
            )

        except Exception as e:
            logger.error(f"Login error: {e}")
            await update.message.reply_text(
                "Произошла ошибка при авторизации. Попробуйте позже."
            )

        # Очищаем временные данные
        context.user_data.clear()
        return ConversationHandler.END

    async def logout(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выход из системы"""
        telegram_id = update.effective_user.id
        self.clear_user_session(telegram_id)

        await update.message.reply_text(
            "Вы вышли из системы.\n"
            "Используйте /start для возврата в главное меню."
        )

    # =============================================================================
    # ПРОФИЛЬ И БАЛАНС
    # =============================================================================

    async def profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Просмотр профиля пользователя"""
        telegram_id = update.effective_user.id
        session = self.get_user_session(telegram_id)

        if not session:
            await update.message.reply_text(
                "Вы не авторизованы. Используйте /login"
            )
            return

        try:
            user = UserService.get_user_by_id(session['user_id'])
            if not user:
                await update.message.reply_text("Пользователь не найден.")
                return

            profile_text = f"""
**Ваш профиль**

ID: {user.id}
Username: {user.username}
Email: {user.email}
Полное имя: {user.full_name or 'Не указано'}
Баланс: ${user.balance}
Роль: {user.role}
Активен: {'Да' if user.is_active else 'Нет'}
Регистрация: {user.created_at.strftime('%d.%m.%Y %H:%M')}
            """

            await update.message.reply_text(profile_text, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Profile error: {e}")
            await update.message.reply_text("Ошибка получения профиля.")

    async def balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Просмотр баланса"""
        telegram_id = update.effective_user.id
        session = self.get_user_session(telegram_id)

        if not session:
            await update.message.reply_text(
                "Вы не авторизованы. Используйте /login"
            )
            return

        try:
            user = UserService.get_user_by_id(session['user_id'])
            if not user:
                await update.message.reply_text("Пользователь не найден.")
                return

            # Получаем последние транзакции
            transactions = UserService.get_user_transactions(user.id)[:5]

            balance_text = f"""
**Ваш баланс: ${user.balance}**

**Последние операции:**
"""

            if transactions:
                for t in transactions:
                    operation = "Пополнение" if t.transaction_type == "deposit" else "Списание"
                    balance_text += f"{operation} {t.amount:+} - {t.description or t.transaction_type}\n"
            else:
                balance_text += "Операций пока нет.\n"

            balance_text += "\nИспользуйте /addbalance для пополнения"

            await update.message.reply_text(balance_text, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Balance error: {e}")
            await update.message.reply_text("Ошибка получения баланса.")

    # =============================================================================
    # ПОПОЛНЕНИЕ БАЛАНСА
    # =============================================================================

    async def start_add_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало пополнения баланса"""
        telegram_id = update.effective_user.id
        session = self.get_user_session(telegram_id)

        if not session:
            await update.message.reply_text(
                "Вы не авторизованы. Используйте /login"
            )
            return ConversationHandler.END

        await update.message.reply_text(
            "**Пополнение баланса**\n\n"
            "Введите сумму для пополнения (в долларах):",
            parse_mode='Markdown'
        )
        return ADD_BALANCE_AMOUNT

    async def add_balance_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка суммы пополнения"""
        telegram_id = update.effective_user.id
        session = self.get_user_session(telegram_id)

        try:
            amount = float(update.message.text.strip())

            if amount <= 0:
                await update.message.reply_text(
                    "Сумма должна быть положительной. Попробуйте еще раз:"
                )
                return ADD_BALANCE_AMOUNT

            if amount > 10000:
                await update.message.reply_text(
                    "Максимальная сумма пополнения: $10,000. Попробуйте еще раз:"
                )
                return ADD_BALANCE_AMOUNT

            # Пополняем баланс
            success = UserService.add_balance(
                session['user_id'],
                amount,
                f"Telegram bot top-up by {update.effective_user.first_name}"
            )

            if success:
                updated_user = UserService.get_user_by_id(session['user_id'])
                await update.message.reply_text(
                    f"**Баланс пополнен!**\n\n"
                    f"Добавлено: ${amount}\n"
                    f"Новый баланс: ${updated_user.balance}",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "Ошибка пополнения баланса. Попробуйте позже."
                )

        except ValueError:
            await update.message.reply_text(
                "Некорректная сумма. Введите число (например: 100.50):"
            )
            return ADD_BALANCE_AMOUNT
        except Exception as e:
            logger.error(f"Add balance error: {e}")
            await update.message.reply_text(
                "Произошла ошибка при пополнении баланса."
            )

        return ConversationHandler.END

    # =============================================================================
    # СОБЫТИЯ
    # =============================================================================

    async def events(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Просмотр активных событий"""
        try:
            events = EventService.get_active_events()[:10]  # Последние 10 событий

            if not events:
                await update.message.reply_text(
                    "Активных событий пока нет.\n"
                    "Используйте /createevent для создания нового события."
                )
                return

            events_text = "**Активные события:**\n\n"

            for event in events:
                events_text += f"""
**{event.title}**
Стоимость: ${event.cost}
Участников: {event.current_participants}
{f"Описание: {event.description[:50]}..." if event.description else ""}
ID: {event.id}

"""

            events_text += "\nДля участия в событии используйте команду:\n`/join <ID события>`"

            await update.message.reply_text(events_text, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Events error: {e}")
            await update.message.reply_text("Ошибка получения событий.")

    async def my_events(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Мои события"""
        telegram_id = update.effective_user.id
        session = self.get_user_session(telegram_id)

        if not session:
            await update.message.reply_text(
                "Вы не авторизованы. Используйте /login"
            )
            return

        try:
            events = EventService.get_events_by_creator(session['user_id'])

            if not events:
                await update.message.reply_text(
                    "У вас пока нет созданных событий.\n"
                    "Используйте /createevent для создания."
                )
                return

            events_text = "**Ваши события:**\n\n"

            for event in events:
                events_text += f"""
**{event.title}**
Статус: {event.status}
Стоимость: ${event.cost}
Участников: {event.current_participants}
ID: {event.id}

"""

            await update.message.reply_text(events_text, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"My events error: {e}")
            await update.message.reply_text("Ошибка получения ваших событий.")

    async def transactions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """История транзакций"""
        telegram_id = update.effective_user.id
        session = self.get_user_session(telegram_id)

        if not session:
            await update.message.reply_text(
                "Вы не авторизованы. Используйте /login"
            )
            return

        try:
            transactions = UserService.get_user_transactions(session['user_id'])[:20]

            if not transactions:
                await update.message.reply_text(
                    "У вас пока нет транзакций."
                )
                return

            trans_text = "**История транзакций:**\n\n"

            for t in transactions:
                operation = "Пополнение" if t.transaction_type == "deposit" else "Списание"
                date_str = t.created_at.strftime('%d.%m %H:%M')
                trans_text += f"{operation} ${t.amount:+.2f} - {date_str}\n"
                if t.description:
                    trans_text += f"    Описание: {t.description[:40]}...\n"
                trans_text += "\n"

            await update.message.reply_text(trans_text, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Transactions error: {e}")
            await update.message.reply_text("Ошибка получения транзакций.")

    # =============================================================================
    # СОЗДАНИЕ СОБЫТИЙ
    # =============================================================================

    async def start_create_event(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало создания события"""
        telegram_id = update.effective_user.id
        session = self.get_user_session(telegram_id)

        if not session:
            await update.message.reply_text(
                "Вы не авторизованы. Используйте /login"
            )
            return ConversationHandler.END

        await update.message.reply_text(
            "**Создание нового события**\n\n"
            "Введите название события:",
            parse_mode='Markdown'
        )
        return CREATE_EVENT_TITLE

    async def create_event_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение названия события"""
        title = update.message.text.strip()

        if len(title) < 3:
            await update.message.reply_text(
                "Название должно содержать минимум 3 символа. Попробуйте еще раз:"
            )
            return CREATE_EVENT_TITLE

        context.user_data['event_title'] = title
        await update.message.reply_text(
            f"Название: {title}\n\n"
            "Введите описание события (или 'пропустить'):"
        )
        return CREATE_EVENT_DESCRIPTION

    async def create_event_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение описания события"""
        description = update.message.text.strip()

        if description.lower() == 'пропустить':
            description = None

        context.user_data['event_description'] = description
        await update.message.reply_text(
            f"Описание: {description or 'Не указано'}\n\n"
            "Введите стоимость участия (0 для бесплатного события):"
        )
        return CREATE_EVENT_COST

    async def create_event_cost(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение стоимости и создание события"""
        telegram_id = update.effective_user.id
        session = self.get_user_session(telegram_id)

        try:
            cost = float(update.message.text.strip())

            if cost < 0:
                await update.message.reply_text(
                    "Стоимость не может быть отрицательной. Попробуйте еще раз:"
                )
                return CREATE_EVENT_COST

            # Создаем событие
            event = EventService.create_event(
                title=context.user_data['event_title'],
                description=context.user_data['event_description'],
                creator_id=session['user_id'],
                cost=cost
            )

            await update.message.reply_text(
                f"**Событие создано успешно!**\n\n"
                f"Название: {event.title}\n"
                f"Стоимость: ${event.cost}\n"
                f"Статус: {event.status}\n"
                f"ID: {event.id}\n\n"
                f"Для активации события используйте команду администрации.",
                parse_mode='Markdown'
            )

        except ValueError:
            await update.message.reply_text(
                "Некорректная стоимость. Введите число (например: 50.00):"
            )
            return CREATE_EVENT_COST
        except Exception as e:
            logger.error(f"Create event error: {e}")
            await update.message.reply_text(
                "Ошибка создания события. Попробуйте позже."
            )

        # Очищаем временные данные
        context.user_data.clear()
        return ConversationHandler.END

    # =============================================================================
    # CALLBACK ОБРАБОТЧИКИ (INLINE КНОПКИ)
    # =============================================================================

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий inline кнопок"""
        query = update.callback_query
        await query.answer()

        data = query.data
        telegram_id = query.from_user.id
        session = self.get_user_session(telegram_id)

        if data == "profile" and session:
            await self.handle_profile_button(query, session)
        elif data == "balance" and session:
            await self.handle_balance_button(query, session)
        elif data == "events":
            await self.handle_events_button(query)
        elif data == "myevents" and session:
            await self.handle_my_events_button(query, session)
        elif data == "transactions" and session:
            await self.handle_transactions_button(query, session)
        elif data == "logout":
            await self.handle_logout_button(query, telegram_id)
        elif data == "login":
            await query.edit_message_text(
                "Для входа в систему используйте команду /login"
            )
        elif data == "register":
            await query.edit_message_text(
                "Для регистрации используйте команду /register"
            )
        elif data.startswith("join_"):
            await self.handle_join_event_button(query, data, session)
        elif data.startswith("predict_"):
            await self.handle_predict_button(query, data, session)

    async def handle_profile_button(self, query, session):
        """Обработка кнопки профиля"""
        try:
            user = UserService.get_user_by_id(session['user_id'])
            if not user:
                await query.edit_message_text("Пользователь не найден.")
                return

            profile_text = f"""
**Ваш профиль**

ID: {user.id}
Username: {user.username}
Email: {user.email}
Баланс: ${user.balance}
Роль: {user.role}
Регистрация: {user.created_at.strftime('%d.%m.%Y')}
            """

            keyboard = [[InlineKeyboardButton("Назад", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                profile_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Profile button error: {e}")
            await query.edit_message_text("Ошибка получения профиля.")

    async def handle_balance_button(self, query, session):
        """Обработка кнопки баланса"""
        try:
            user = UserService.get_user_by_id(session['user_id'])
            if not user:
                await query.edit_message_text("Пользователь не найден.")
                return

            # Получаем последние транзакции
            transactions = UserService.get_user_transactions(user.id)[:3]

            balance_text = f"**Текущий баланс: ${user.balance}**\n\n"

            if transactions:
                balance_text += "**Последние операции:**\n"
                for t in transactions:
                    operation = "Пополнение" if t.transaction_type == "deposit" else "Списание"
                    balance_text += f"{operation} ${t.amount:+.2f}\n"

            keyboard = [
                [InlineKeyboardButton("Пополнить", callback_data="add_balance")],
                [InlineKeyboardButton("Назад", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                balance_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Balance button error: {e}")
            await query.edit_message_text("Ошибка получения баланса.")

    async def handle_events_button(self, query):
        """Обработка кнопки событий"""
        try:
            events = EventService.get_active_events()[:5]

            if not events:
                await query.edit_message_text(
                    "Активных событий пока нет.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Назад", callback_data="back_to_menu")]
                    ])
                )
                return

            events_text = "**Активные события:**\n\n"
            keyboard = []

            for event in events:
                events_text += f"""
**{event.title}**
${event.cost} | Участников: {event.current_participants}
ID: {event.id}

"""
                keyboard.append([
                    InlineKeyboardButton(f"Присоединиться к {event.id}", callback_data=f"join_{event.id}"),
                    InlineKeyboardButton(f"Предсказание {event.id}", callback_data=f"predict_{event.id}")
                ])

            keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_menu")])
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                events_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Events button error: {e}")
            await query.edit_message_text("Ошибка получения событий.")

    async def handle_join_event_button(self, query, data, session):
        """Обработка кнопки присоединения к событию"""
        if not session:
            await query.edit_message_text("Вы не авторизованы. Используйте /login")
            return

        try:
            event_id = int(data.split("_")[1])

            # Получаем информацию о событии
            event = EventService.get_event_by_id(event_id)
            if not event:
                await query.edit_message_text("Событие не найдено.")
                return

            # Присоединяемся к событию
            success = EventService.join_event(session['user_id'], event_id)

            if success:
                updated_user = UserService.get_user_by_id(session['user_id'])
                await query.edit_message_text(
                    f"**Успешно присоединились к событию!**\n\n"
                    f"Событие: {event.title}\n"
                    f"Потрачено: ${event.cost}\n"
                    f"Новый баланс: ${updated_user.balance}",
                    parse_mode='Markdown'
                )
            else:
                user = UserService.get_user_by_id(session['user_id'])
                reason = "недостаточно средств" if event.cost > user.balance else "событие недоступно"
                await query.edit_message_text(
                    f"Не удалось присоединиться к событию.\n"
                    f"Причина: {reason}\n\n"
                    f"Ваш баланс: ${user.balance}\n"
                    f"Нужно: ${event.cost}"
                )

        except Exception as e:
            logger.error(f"Join event error: {e}")
            await query.edit_message_text("Ошибка присоединения к событию.")

    async def handle_predict_button(self, query, data, session):
        """Обработка кнопки предсказания"""
        if not session:
            await query.edit_message_text("Вы не авторизованы. Используйте /login")
            return

        try:
            event_id = int(data.split("_")[1])

            # Получаем информацию о событии
            event = EventService.get_event_by_id(event_id)
            user = UserService.get_user_by_id(session['user_id'])

            if not event or not user:
                await query.edit_message_text("Событие или пользователь не найден.")
                return

            # Простое предсказание
            can_afford = user.balance >= event.cost
            balance_ratio = user.balance / max(event.cost, 1)

            if can_afford and balance_ratio >= 2:
                prediction = "Очень вероятно"
                confidence = 0.85
                status = "Рекомендуется"
            elif can_afford:
                prediction = "Возможно"
                confidence = 0.60
                status = "К рассмотрению"
            else:
                prediction = "Маловероятно"
                confidence = 0.25
                status = "Не рекомендуется"

            prediction_text = f"""
**ML Предсказание участия**

Событие: {event.title}
Стоимость: ${event.cost}
Ваш баланс: ${user.balance}

**Предсказание: {prediction}**
Уверенность: {confidence:.0%}

Рекомендация: {"Присоединяйтесь!" if confidence > 0.7 else "Рассмотрите внимательно" if confidence > 0.4 else "Возможно, стоит подождать"}
            """

            keyboard = [[InlineKeyboardButton("Назад к событиям", callback_data="events")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                prediction_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

            # Записываем запрос в историю
            try:
                UserService.add_balance(
                    session['user_id'],
                    0.0,
                    f"Telegram ML prediction for event: {event.title}"
                )
            except:
                pass

        except Exception as e:
            logger.error(f"Predict error: {e}")
            await query.edit_message_text("Ошибка генерации предсказания.")

    async def handle_logout_button(self, query, telegram_id):
        """Обработка кнопки выхода"""
        self.clear_user_session(telegram_id)

        keyboard = self.get_main_menu_keyboard(False)
        await query.edit_message_text(
            "Вы вышли из системы.",
            reply_markup=keyboard
        )

    # =============================================================================
    # ЗАПУСК БОТА
    # =============================================================================

    async def run(self):
        """Запуск бота"""
        logger.info("Starting Telegram bot...")
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()

        # Держим бота запущенным
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        finally:
            await self.app.stop()

# =============================================================================
# ОСНОВНАЯ ФУНКЦИЯ
# =============================================================================

async def main():
    """Главная функция запуска бота"""

    # Получаем токен бота из переменных окружения
    BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"  # Замените на реальный токен

    if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        logger.error("Please set your Telegram bot token!")
        logger.error("1. Create bot via @BotFather")
        logger.error("2. Set BOT_TOKEN in environment variables or replace in code")
        return

    # Проверяем доступность базы данных
    try:
        from database.database import test_connection, init_db
        if not test_connection():
            logger.error("Database connection failed! Make sure the main API is running.")
            return

        logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Database error: {e}")
        return

    # Создаем и запускаем бота
    bot = EventPlannerBot(BOT_TOKEN)

    logger.info(f"Bot started for {settings.APP_NAME}")
    logger.info("Available commands:")
    logger.info("  /start - Main menu")
    logger.info("  /register - Register new account")
    logger.info("  /login - Login to system")
    logger.info("  /help - Show help")

    try:
        await bot.run()
    except Exception as e:
        logger.error(f"Bot error: {e}")

if __name__ == "__main__":
    """
    Для запуска Telegram бота NB!:

    1. Мне надо создать бота через @BotFather
    2. Взять токен
    3. Замените YOUR_TELEGRAM_BOT_TOKEN_HERE на мой
    4. Убедиться, что основное API запущено
    5. Запустите: python telegram_bot.py
    """
    asyncio.run(main())
