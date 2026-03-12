import os
import time
import redis
import psycopg2
import logging
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'devops_secure_key_default_123')

DB_HOST = os.getenv('DB_HOST', '192.168.0.52')
DB_NAME = os.getenv('DB_NAME', 'devops_db')
DB_USER = os.getenv('DB_USER', 'devops_admin')
DB_PASS = os.getenv('DB_PASS', 'SuperSecretPassword123')
REDIS_HOST = os.getenv('REDIS_HOST', '192.168.0.52')

def get_db_connection():
    retries = 10
    while retries > 0:
        try:
            conn = psycopg2.connect(
                host=DB_HOST, 
                database=DB_NAME,
                user=DB_USER, 
                password=DB_PASS,
                connect_timeout=5
            )
            return conn
        except Exception as e:
            logger.error(f"Ожидание БД {DB_HOST}... Ошибка: {e}. Попыток осталось: {retries}")
            retries -= 1
            time.sleep(5)
    return None

cache = None
try:
    cache = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True, socket_connect_timeout=5)
    logger.info(f"Подключение к Redis на {REDIS_HOST} настроено.")
except Exception as e:
    logger.error(f"Не удалось инициализировать Redis: {e}")

def init_db():
    logger.info("Проверка и инициализация таблиц базы данных...")
    conn = get_db_connection()
    if not conn:
        logger.critical("Не удалось подключиться к базе данных. Приложение может работать некорректно.")
        return
    
    try:
        cur = conn.cursor()
        # Таблица пользователей
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS access_logs (
                id SERIAL PRIMARY KEY,
                username TEXT,
                ip_address TEXT,
                visit_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        conn.commit()
        cur.close()
        logger.info("База данных готова к работе.")
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц: {e}")
    finally:
        conn.close()

BASE_STYLE = """
<style>
    body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #f0f2f5; display: flex; justify-content: center; padding-top: 50px; color: #333; }
    .card { background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); width: 450px; }
    input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 6px; box-sizing: border-box; }
    button { width: 100%; padding: 12px; background: #1a73e8; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; }
    button:hover { background: #1557b0; }
    .nav { margin-bottom: 20px; text-align: right; font-size: 0.9rem; }
    .log-item { background: #f8f9fa; padding: 10px; margin: 5px 0; border-radius: 6px; border-left: 4px solid #1a73e8; font-size: 0.85rem; }
</style>
"""

@app.route('/')
def index():
    hits = "N/A"
    if cache:
        try:
            hits = cache.incr('total_site_hits')
        except Exception as e:
            logger.warning(f"Ошибка инкремента Redis: {e}")

    if 'user' in session:
        conn = get_db_connection()
        if not conn:
            return "Ошибка подключения к БД. Пожалуйста, попробуйте позже."
        
        cur = conn.cursor()
        cur.execute('SELECT username, ip_address, visit_time FROM access_logs ORDER BY id DESC LIMIT 5')
        logs = cur.fetchall()
        cur.close()
        conn.close()
        
        return render_template_string(f"""
            {BASE_STYLE}
            <div class="card">
                <div class="nav">Вы вошли как <b>{session['user']}</b> | <a href="/logout">Выйти</a></div>
                <h1>Статистика системы</h1>
                <p>Просмотров (Redis): <b style="color: #1a73e8;">{hits}</b></p>
                <hr>
                <h3>Последние активности:</h3>
                <div style="list-style: none; padding: 0;">
                    {"".join([f"<div class='log-item'><b>{l[0]}</b> ({l[1]})<br><small>{l[2].strftime('%Y-%m-%d %H:%M:%S')}</small></div>" for l in logs])}
                </div>
            </div>
        """)
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user = request.form['username']
        pw = request.form['password']
        conn = get_db_connection()
        if not conn: return "Ошибка БД"
        cur = conn.cursor()
        try:
            cur.execute('INSERT INTO users (username, password_hash) VALUES (%s, %s)', 
                        (user, generate_password_hash(pw)))
            conn.commit()
            logger.info(f"Новый пользователь зарегистрирован: {user}")
            return redirect(url_for('login'))
        except Exception as e:
            logger.error(f"Ошибка при регистрации {user}: {e}")
            return "Этот логин уже занят или произошла ошибка."
        finally:
            cur.close()
            conn.close()
    return render_template_string(f'{BASE_STYLE}<div class="card"><h1>Регистрация</h1><form method="post"><input name="username" placeholder="Логин" required><input name="password" type="password" placeholder="Пароль" required><button type="submit">Создать аккаунт</button></form><br><center><a href="/login">Уже есть аккаунт? Войти</a></center></div>')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form['username']
        pw = request.form['password']
        conn = get_db_connection()
        if not conn: return "Ошибка БД"
        cur = conn.cursor()
        try:
            cur.execute('SELECT password_hash FROM users WHERE username = %s', (user,))
            row = cur.fetchone()
            if row and check_password_hash(row[0], pw):
                session['user'] = user
                ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0]
                cur.execute('INSERT INTO access_logs (username, ip_address) VALUES (%s, %s)', (user, ip))
                conn.commit()
                return redirect(url_for('index'))
            else:
                return "Неверный логин или пароль."
        finally:
            cur.close()
            conn.close()
    return render_template_string(f'{BASE_STYLE}<div class="card"><h1>Вход в систему</h1><form method="post"><input name="username" placeholder="Логин" required><input name="password" type="password" placeholder="Пароль" required><button type="submit">Войти</button></form><br><center><a href="/register">Еще нет аккаунта?</a></center></div>')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == "__main__":
    init_db()
    # Запуск Flask
    app.run(host='0.0.0.0', port=5000)