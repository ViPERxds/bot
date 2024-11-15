from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler
from telegram.ext import ContextTypes, filters
import httpx
import logging
import json
import os
from dotenv import load_dotenv
from app.core.config import settings
from fastapi import HTTPException

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
API_URL = settings.BASE_URL
TELEGRAM_TOKEN = settings.TELEGRAM_TOKEN

# Нужно добавить обработку ошибок при отсутствии TELEGRAM_TOKEN
if not TELEGRAM_TOKEN:
    raise ValueError("Не задан TELEGRAM_TOKEN в .env файле")

class DomophoneBot:
    def __init__(self):
        if not TELEGRAM_TOKEN:
            raise ValueError("Не задан TELEGRAM_TOKEN")
        self.app = Application.builder().token(TELEGRAM_TOKEN).build()
        self.setup_handlers()
        
    def setup_handlers(self):
        """Настройка обработчиков команд"""
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(MessageHandler(filters.CONTACT, self.handle_contact))
        self.app.add_handler(CommandHandler("domofons", self.show_domofons))
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /start"""
        keyboard = [[{"text": "Отправить номер телефона", "request_contact": True}]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await update.message.reply_text(
            "Добро пожаловать! Для начала работы, пожалуйста, поделитесь номером телефона.",
            reply_markup=reply_markup
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отображение справки по командам"""
        help_text = """
🤖 *Команды бота:*

/start - Начать работу с ботом
/help - Показать эту справку
/domofons - Показать список доступных домофонов

*Возможности:*
• 📱 Авторизация по номеру телефона
• 📋 Просмотр списка доступных домофонов
• 📷 Получение снимков с камер
• 🚪 Открытие дверей
• 🔔 Уведомления о входящих вызовах

*Как пользоваться:*
1. Отправьте свой номер телефона для авторизации
2. Используйте команду /domofons для просмотра списка
3. Нажимайте на кнопки для получения снимков и открытия дверей
        """
        await update.message.reply_text(
            help_text,
            parse_mode='Markdown'
        )

    async def handle_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка полученного контакта"""
        try:
            phone = update.message.contact.phone_number
            if not phone.startswith('+'):
                phone = '+' + phone
            
            # Преобразуем телефон в формат 7XXXXXXXXXX
            phone = phone.replace('+', '')
            if phone.startswith('8'):
                phone = '7' + phone[1:]
            
            logger.info(f"Получен номер телефона: {phone}")
            
            # Получаем tenant_id по номеру телефона
            headers = {
                "x-api-key": settings.API_TOKEN,
                "Content-Type": "application/json"
            }
            
            # Используем правильный эндпоинт из документации
            url = f"{settings.API_URL}/check-tenant"
            payload = {"phone": int(phone)}
            
            logger.info(f"Отправляем запрос: URL={url}, payload={payload}")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload
                )
                
                logger.info(f"Статус ответа: {response.status_code}")
                logger.info(f"Тело ответа: {response.text}")
                
                if response.status_code == 200:
                    data = response.json()
                    tenant_id = data.get('tenant_id')  # Получаем tenant_id из ответа
                    context.user_data['tenant_id'] = tenant_id
                    await update.message.reply_text(
                        "✅ Авторизация успешна! Используйте /domofons для просмотра доступных домофонов."
                    )
                else:
                    raise HTTPException(status_code=response.status_code, detail=response.text)

        except Exception as e:
            logger.error(f"Ошибка при обработке контакта: {str(e)}")
            await update.message.reply_text(
                "❌ Ошибка авторизации. Попробуйте позже или обратитесь в поддержку."
            )

    async def show_domofons(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показ списка доступных домофонов"""
        if 'tenant_id' not in context.user_data:
            await update.message.reply_text(
                "Вы не авторизованы. Используйте /start для авторизации."
            )
            return
            
        try:
            headers = {
                "x-api-key": settings.API_TOKEN,
                "Content-Type": "application/json"
            }
            
            # 1. Получаем список квартир
            apartments_url = f"{settings.API_URL}/domo.apartment"
            params = {"tenant_id": context.user_data['tenant_id']}
            
            logger.info(f"Запрос списка квартир: URL={apartments_url}, params={params}")
            
            async with httpx.AsyncClient() as client:
                apartments_response = await client.get(
                    apartments_url,
                    headers=headers,
                    params=params
                )
                
                if apartments_response.status_code != 200:
                    raise HTTPException(status_code=apartments_response.status_code, 
                                     detail=apartments_response.text)
                    
                apartments = apartments_response.json()
                keyboard = []
                
                # 2. Для каждой квартиры получаем домофоны
                for apartment in apartments:
                    domofons_url = f"{settings.API_URL}/domo.apartment/{apartment['id']}/domofon"
                    domofons_params = {"tenant_id": context.user_data['tenant_id']}
                    
                    domofons_response = await client.get(
                        domofons_url,
                        headers=headers,
                        params=domofons_params
                    )
                    
                    if domofons_response.status_code != 200:
                        continue
                        
                    domofons = domofons_response.json()
                    
                    for domofon in domofons:
                        location = domofon.get('location', {})
                        address = location.get('readable_address', 'Адрес не указан')
                        porch = location.get('porch', '')
                        address_text = f"{address} (подъезд {porch})" if porch else address
                        
                        keyboard.append([
                            InlineKeyboardButton(
                                f"📷 {address_text}",
                                callback_data=f"snapshot_{domofon['id']}"
                            ),
                            InlineKeyboardButton(
                                f"🚪 Открыть",
                                callback_data=f"open_{domofon['id']}"
                            )
                        ])
                
                if keyboard:
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await update.message.reply_text(
                        "Выберите действие:",
                        reply_markup=reply_markup
                    )
                else:
                    await update.message.reply_text("У вас нет доступных домофонов")
                    
        except Exception as e:
            logger.error(f"Ошибка получения списка домофонов: {str(e)}")
            await update.message.reply_text(
                "❌ Ошибка получения списка домофонов. Попробуйте позже."
            )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий на кнопки"""
        query = update.callback_query
        action, domofon_id = query.data.split('_')
        
        try:
            headers = {
                "x-api-key": settings.API_TOKEN,
                "Content-Type": "application/json"
            }
            
            if action == "snapshot":
                # Получаем снимок с камеры
                url = f"{settings.API_URL}/domo.domofon/urlsOnType"
                payload = {
                    "intercoms_id": [int(domofon_id)],
                    "media_type": ["JPEG"]
                }
                params = {"tenant_id": context.user_data['tenant_id']}
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        url,
                        headers=headers,
                        json=payload,
                        params=params
                    )
                    
                    if response.status_code == 200:
                        urls = response.json()
                        if urls and urls[0].get('jpeg'):
                            await query.message.reply_photo(
                                urls[0]['jpeg'],
                                caption="📷 Снимок с камеры"
                            )
                        else:
                            await query.message.reply_text("❌ Не удалось получить снимок")
                            
            elif action == "open":
                # Открываем дверь
                url = f"{settings.API_URL}/domo.domofon/{domofon_id}/open"
                payload = {"door_id": 1}
                params = {"tenant_id": context.user_data['tenant_id']}
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        url,
                        headers=headers,
                        json=payload,
                        params=params
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        await query.message.reply_text(data.get('msg', '✅ Дверь открыта'))
                    else:
                        await query.message.reply_text("❌ Не удалось открыть дверь")
                        
        except Exception as e:
            logger.error(f"Ошибка при обработке действия: {str(e)}")
            await query.message.reply_text(f"❌ Ошибка: {str(e)}")
        
        await query.answer()

    async def check_api(self):
        """Проверка доступности API"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{API_URL}/")
                response.raise_for_status()
        except Exception as e:
            logger.error(f"API недоступен: {str(e)}")
            raise

    def run(self):
        """Запуск бота"""
        self.app.run_polling()

if __name__ == '__main__':
    bot = DomophoneBot()
    bot.run() 