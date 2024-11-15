from flask import Flask, request, jsonify
from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
import os
from dotenv import load_dotenv
from api_client import ApiClient

load_dotenv()

app = Flask(__name__)
bot = Bot(token=os.getenv('TELEGRAM_TOKEN'))
api_client = ApiClient(os.getenv('DOMOPHONE_API_URL'), os.getenv('DOMOPHONE_API_TOKEN'))

@app.route('/webhook/call', methods=['POST', 'GET'])
async def handle_call():
    if request.method == 'GET':
        data = request.args
    else:
        data = request.json
        
    domophone_id = data.get('domofon_id')
    tenant_id = data.get('tenant_id')
    
    if not domophone_id or not tenant_id:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    # Получаем информацию о пользователе
    user_info = api_client.check_tenant(tenant_id)
    if not user_info or not user_info.get('telegram_chat_id'):
        return jsonify({'error': 'User not found or no telegram chat ID'}), 404
    
    # Получаем снимок с камеры
    snapshot = api_client.get_camera_snapshot(domophone_id, user_info.get('phone'))
    
    # Создаем кнопку для открытия двери
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Открыть дверь", callback_data=f"open_{domophone_id}")]
    ])
    
    try:
        if snapshot:
            await bot.send_photo(
                chat_id=user_info['telegram_chat_id'],
                photo=snapshot,
                caption="🔔 Входящий вызов в домофон!",
                reply_markup=keyboard
            )
        else:
            await bot.send_message(
                chat_id=user_info['telegram_chat_id'],
                text="🔔 Входящий вызов в домофон!",
                reply_markup=keyboard
            )
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 