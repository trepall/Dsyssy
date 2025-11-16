import psycopg2
from config import Config
import logging

class Database:
    def __init__(self):
        self.conn = None
        self.connect()
    
    def connect(self):
        try:
            self.conn = psycopg2.connect(Config.DATABASE_URL)
            logging.info("✅ Connected to Supabase")
        except Exception as e:
            logging.error(f"❌ Database connection error: {e}")
    
    def get_user(self, telegram_id):
        try:
            with self.conn.cursor() as cur:
                cur.execute('SELECT * FROM users WHERE telegram_id = %s', (telegram_id,))
                return cur.fetchone()
        except Exception as e:
            logging.error(f"❌ Get user error: {e}")
            return None
    
    def create_user(self, telegram_id):
        try:
            with self.conn.cursor() as cur:
                cur.execute('INSERT INTO users (telegram_id) VALUES (%s) ON CONFLICT DO NOTHING RETURNING *', (telegram_id,))
                self.conn.commit()
                return cur.fetchone()
        except Exception as e:
            logging.error(f"❌ Create user error: {e}")
            return None
    
    def update_balance(self, telegram_id, amount):
        try:
            with self.conn.cursor() as cur:
                cur.execute('UPDATE users SET balance = balance + %s WHERE telegram_id = %s RETURNING *', (amount, telegram_id))
                self.conn.commit()
                return cur.fetchone()
        except Exception as e:
            logging.error(f"❌ Update balance error: {e}")
            return None
    
    def create_transaction(self, user_id, amount, tx_type, status='pending', asset='TON', address=None):
        try:
            with self.conn.cursor() as cur:
                cur.execute('INSERT INTO transactions (user_id, amount, type, status, asset, address) VALUES (%s, %s, %s, %s, %s, %s) RETURNING *', (user_id, amount, tx_type, status, asset, address))
                self.conn.commit()
                return cur.fetchone()
        except Exception as e:
            logging.error(f"❌ Create transaction error: {e}")
            return None

db = Database()
