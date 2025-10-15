from flask import Flask, request, jsonify
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timedelta
import requests
import os
from colorama import Fore, Style, init
init(autoreset=True)

# ===============================================================
# SERVER CONFIGURATION
# ===============================================================
TELEGRAM_BOT_TOKEN = '8289877773:AAGoKoFFLWCNAzJLCaBYezEWoRvo6vltUIs'
ADMIN_TELEGRAM_ID = '-1002611999679'

# ===============================================================
# DATABASE CONNECTION (AIVEN MYSQL)
# ===============================================================
# !!! انتبه: الصق رابط قاعدة البيانات الخاص بك هنا !!!
# تأكد أنه يبدأ بـ mysql+pymysql وأزل ?ssl-mode=REQUIRED من النهاية
DATABASE_URL = "mysql+pymysql://avnadmin:YOUR_PASSWORD@YOUR_HOST:YOUR_PORT/defaultdb"

# يحدد مسار شهادة SSL (ملف ca.pem)
# يفترض أن ملف ca.pem موجود في نفس مجلد هذا السكريبت
basedir = os.path.abspath(os.path.dirname(__file__))
ca_path = os.path.join(basedir, 'ca.pem')

# إنشاء اتصال بقاعدة البيانات مع تفعيل SSL
try:
    ENGINE = create_engine(
        DATABASE_URL,
        connect_args={
            "ssl": {
                "ca": ca_path
            }
        }
    )
    Base = declarative_base()
    Session = sessionmaker(bind=ENGINE)
    app = Flask(__name__)
except Exception as e:
    print(Fore.RED + f"❌ DATABASE CONNECTION FAILED: {e}")
    exit()

# ===============================================================
# DATABASE MODEL
# ===============================================================
class License(Base):
    __tablename__ = 'licenses'
    id = Column(Integer, primary_key=True)
    key = Column(String(255), unique=True, nullable=False)
    client_name = Column(String(255), default="N/A")
    telegram_username = Column(String(255), default="N/A")
    mac_address = Column(String(255), default="N/A")
    status = Column(String(255), default="PENDING")
    created_at = Column(DateTime, default=datetime.now)
    activation_date = Column(DateTime)
    expiration_date = Column(DateTime)
    emails_sent = Column(Integer, default=0)
    is_active = Column(Boolean, default=True) # Added for consistency with admin_cli

# ===============================================================
# UTILITY FUNCTIONS
# ===============================================================
def send_telegram_notification(message):
    """Sends a markdown notification to the admin Telegram group/ID."""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': ADMIN_TELEGRAM_ID,
            'text': message,
            'parse_mode': 'Markdown'
        }
        requests.post(url, json=payload, timeout=5)
    except Exception:
        pass

# ===============================================================
# FLASK API ROUTES
# ===============================================================
@app.route('/api/check_license', methods=['POST'])
def check_license_api():
    """Handles license verification, MAC binding, and status updates."""
    data = request.get_json()
    license_key = data.get('key')
    mac_address = data.get('mac_address')
    total_sent = data.get('total_sent', 0)

    session = Session()
    license_entry = session.query(License).filter_by(key=license_key).first()

    if not license_entry:
        session.close()
        print(Fore.RED + f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Attempt with unknown key: {license_key}")
        return jsonify({'status': 'invalid', 'message': 'License key not found.'}), 200

    if not license_entry.is_active:
        session.close()
        print(Fore.YELLOW + f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ INACTIVE key used: {license_key}")
        return jsonify({'status': 'invalid', 'message': 'License is not active. Please contact support.'}), 200
        
    if license_entry.expiration_date and license_entry.expiration_date < datetime.now():
        license_entry.status = 'EXPIRED'
        license_entry.is_active = False
        session.commit()
        session.close()
        print(Fore.RED + f"[{datetime.now().strftime('%H:%M:%S')}] ❌ EXPIRED key used: {license_key}")
        return jsonify({'status': 'invalid', 'message': 'License has expired.'}), 200

    license_entry.emails_sent = total_sent

    if license_entry.mac_address in [None, "N/A", ""]:
        license_entry.status = 'ACTIVE'
        license_entry.mac_address = mac_address
        license_entry.activation_date = datetime.now()
        
        notification_msg = (
            f"✅ *New License ACTIVATED*\n"
            f"🔑 Key: `{license_key}`\n"
            f"👤 Client: {license_entry.client_name}\n"
            f"💻 MAC: `{mac_address}`\n"
            f"🗓️ Expires: {license_entry.expiration_date.strftime('%Y-%m-%d')}"
        )
        send_telegram_notification(notification_msg)
        print(Fore.GREEN + f"[{datetime.now().strftime('%H:%M:%S')}] ✅ NEW ACTIVATION: {license_key} by {mac_address}")

    elif license_entry.mac_address != mac_address:
        session.close()
        print(Fore.RED + f"[{datetime.now().strftime('%H:%M:%S')}] ❌ MAC MISMATCH: {license_key} attempted by {mac_address}")
        return jsonify({'status': 'invalid', 'message': 'License is already bound to another machine.'}), 200

    duration_days = (license_entry.expiration_date - datetime.now()).days if license_entry.expiration_date else 9999
    session.commit()
    session.close()

    print(Fore.GREEN + f"[{datetime.now().strftime('%H:%M:%S')}] 👍 Key OK: {license_key} | Sent: {total_sent}")
    return jsonify({
        'status': 'valid',
        'duration_days': duration_days,
        'message': 'License is valid and active.'
    }), 200

# ===============================================================
# SERVER ENTRY POINT
# ===============================================================
if __name__ == '__main__':
    os.system('cls' if os.name == 'nt' else 'clear')
    Base.metadata.create_all(ENGINE)
    print(Fore.CYAN + Style.BRIGHT + "\n" + "=" * 50)
    print(Fore.CYAN + "| VEX-SENDER V2 LICENSING SERVER ONLINE |")
    print(Fore.CYAN + f"| Hosted at: http://0.0.0.0:5000/api/check_license |")
    print(Fore.CYAN + "=" * 50)
    # The app.run line is only for local testing. Render will use Gunicorn.
    # app.run(host='0.0.0.0', port=5000)
