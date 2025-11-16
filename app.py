from flask import Flask, request, jsonify
import requests
import logging
import os
from database import db
from config import Config

app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CryptoBotAPI:
    def __init__(self, token):
        self.token = token
        self.base_url = "https://pay.crypt.bot/api"
    
    def create_invoice(self, amount, asset='TON', user_id=None):
        try:
            response = requests.post(
                f"{self.base_url}/createInvoice",
                headers={'Crypto-Pay-API-Token': self.token},
                json={
                    'asset': asset,
                    'amount': str(amount),
                    'description': f'Пополнение баланса на {amount} {asset}',
                    'payload': str(user_id)
                }
            )
            data = response.json()
            if data.get('ok'):
                return data['result']
            return None
        except Exception as e:
            logger.error(f"CryptoBot API error: {e}")
            return None

crypto_bot = CryptoBotAPI(Config.CRYPTO_BOT_TOKEN)

@app.route('/')
def home():
    return "🚀 Crypto Payment Bot is running!"

@app.route('/api/deposit', methods=['POST'])
def create_deposit():
    try:
        data = request.get_json()
        telegram_id = data.get('telegram_id')
        amount = data.get('amount')
        asset = data.get('asset', 'TON')
        
        if not telegram_id or not amount:
            return jsonify({'error': 'Missing parameters'}), 400
        
        user = db.get_user(telegram_id)
        if not user:
            db.create_user(telegram_id)
        
        invoice = crypto_bot.create_invoice(amount, asset, telegram_id)
        if not invoice:
            return jsonify({'error': 'Failed to create invoice'}), 500
        
        db.create_transaction(telegram_id, amount, 'deposit', 'pending', asset)
        
        return jsonify({
            'success': True,
            'pay_url': invoice['pay_url'],
            'invoice_id': invoice['invoice_id']
        })
    except Exception as e:
        logger.error(f"Deposit error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/withdraw', methods=['POST'])
def create_withdraw():
    try:
        data = request.get_json()
        telegram_id = data.get('telegram_id')
        amount = float(data.get('amount'))
        address = data.get('address')
        asset = data.get('asset', 'TON')
        
        if not all([telegram_id, amount, address]):
            return jsonify({'error': 'Missing parameters'}), 400
        
        user = db.get_user(telegram_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        user_balance = float(user[2])
        if user_balance < amount:
            return jsonify({'error': f'Insufficient balance. Available: {user_balance}'}), 400
        
        transaction = db.create_transaction(telegram_id, amount, 'withdraw', 'pending', asset, address)
        
        updated_user = db.update_balance(telegram_id, -amount)
        if not updated_user:
            return jsonify({'error': 'Failed to update balance'}), 500
        
        return jsonify({
            'success': True,
            'message': 'Withdrawal request created',
            'transaction_id': transaction[0],
            'new_balance': float(updated_user[2])
        })
    except Exception as e:
        logger.error(f"Withdraw error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/balance/<telegram_id>')
def get_balance(telegram_id):
    try:
        user = db.get_user(telegram_id)
        if not user:
            return jsonify({'balance': 0})
        return jsonify({'balance': float(user[2])})
    except Exception as e:
        logger.error(f"Balance error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/webhook/crypto-bot', methods=['POST'])
def crypto_bot_webhook():
    try:
        data = request.get_json()
        logger.info(f"Webhook received: {data}")
        
        update_type = data.get('update_type')
        if update_type == 'invoice_paid':
            invoice = data.get('payload', {})
            status = invoice.get('status')
            amount = float(invoice.get('amount'))
            asset = invoice.get('asset')
            payload = invoice.get('payload')
            
            if status == 'paid' and payload:
                user_id = int(payload)
                user = db.update_balance(user_id, amount)
                if user:
                    db.create_transaction(user_id, amount, 'deposit', 'completed', asset)
                    logger.info(f"Balance updated for user {user_id}: +{amount} {asset}")
        
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
