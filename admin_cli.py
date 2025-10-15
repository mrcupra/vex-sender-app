import random
import string
import requests
import traceback
from datetime import datetime, timedelta
from colorama import init, Fore, Style
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os

init(autoreset=True)

# ===============================================================
# ADMIN CONFIGURATION
# ===============================================================
TELEGRAM_BOT_TOKEN = '8289877773:AAGoKoFFLWCNAzJLCaBYezEWoRvo6vltUIs'
ADMIN_TELEGRAM_ID = '-1002611999679'

# ===============================================================
# DATABASE CONNECTION (AIVEN MYSQL)
# ===============================================================
# !!! انتبه: الصق رابط قاعدة البيانات الخاص بك هنا !!!
# تأكد أنه يبدأ بـ mysql+pymysql وأزل ?ssl-mode=REQUIRED من النهاية
DATABASE_URL = "mysql://avnadmin:AVNS_STaeS8Q8sjDFN2T29RL@mysql-230889fb-mohamedpython1-dae0.b.aivencloud.com:10119/defaultdb?ssl-mode=REQUIRED"

# يحدد مسار شهادة SSL (ملف ca.pem)
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
    session = Session()
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
    is_active = Column(Boolean, default=True)
    
    def check_expiry(self):
        if self.expiration_date and datetime.now() > self.expiration_date:
            self.status = "EXPIRED"
            self.is_active = False
            session.commit()
            return True
        return False
    
    def renew_license(self, days):
        if self.status == "EXPIRED":
            self.expiration_date = datetime.now() + timedelta(days=days)
            self.status = "ACTIVE"
            self.is_active = True
            session.commit()
            return True
        return False

# Functions (create_new_license, view_all_licenses, etc.) remain the same as your original file
# ... (All your admin functions go here, no changes needed in them)
# I will copy them here for completeness.

def send_telegram_notification(message):
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
        
def generate_unique_key(length=20):
    chars = string.ascii_uppercase + string.digits
    key = ''.join(random.choice(chars) for _ in range(length))
    return f"{key[:5]}-{key[5:10]}-{key[10:15]}-{key[15:]}"

def create_new_license():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(Fore.CYAN + "\n" + "=" * 50)
    print(Fore.CYAN + "✨ CREATE NEW LICENSE KEY")
    print(Fore.CYAN + "=" * 50)
    
    duration = input(Fore.YELLOW + ">> Enter duration in days (e.g., 30): ").strip()
    client_name = input(Fore.YELLOW + ">> Enter Client Name: ").strip()
    telegram_user = input(Fore.YELLOW + ">> Enter Telegram Username (@user): ").strip()
    
    try:
        duration_days = int(duration)
        # Activation is now, expiry is relative to now.
        expiration_date = datetime.now() + timedelta(days=duration_days)
    except ValueError:
        print(Fore.RED + "❌ Invalid duration. Please enter a number.")
        return

    new_key = generate_unique_key()
    new_license = License(
        key=new_key,
        client_name=client_name,
        telegram_username=telegram_user,
        expiration_date=expiration_date,
        status="PENDING", # Licenses start as PENDING until first use
        is_active=True
    )

    try:
        session.add(new_license)
        session.commit()
        print(Fore.GREEN + "\n" + Style.BRIGHT + "✅ LICENSE CREATED SUCCESSFULLY!")
        print(Fore.YELLOW + f"🔑 Key: {new_key}")
        print(Fore.YELLOW + f"👤 Client: {client_name} ({telegram_user})")
        print(Fore.YELLOW + f"🗓️ Expires: {expiration_date.strftime('%Y-%m-%d')}")
        print(Fore.YELLOW + f"STATUS: PENDING (will activate on first use)")
        
        notification_msg = (
            f"🎉 *New License Key Created*\n"
            f"🔑 Key: `{new_key}`\n"
            f"👤 Client: {client_name}\n"
            f"💬 Telegram: {telegram_user}\n"
            f"⏳ Duration: {duration_days} days\n"
            f" STATUS: PENDING"
        )
        send_telegram_notification(notification_msg)
        
    except Exception as e:
        session.rollback()
        print(Fore.RED + f"❌ Error creating license: {e}")

def view_all_licenses():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(Fore.CYAN + "\n" + "=" * 120)
    print(Fore.CYAN + "📊 VEX-SENDER LICENSE DASHBOARD")
    print(Fore.CYAN + "=" * 120)
    
    licenses = session.query(License).all()
    for license in licenses:
        license.check_expiry()
    
    licenses = session.query(License).all()
    
    if not licenses:
        print(Fore.YELLOW + "⚠️ No licenses found in the database.")
        return

    header = f"{Fore.CYAN}{'KEY':<24}{'CLIENT NAME':<20}{'TELEGRAM':<15}{'STATUS':<12}{'API':<8}{'SENT':<8}{'MAC ADDRESS':<20}{'EXPIRY':<12}"
    print(header)
    print(Fore.CYAN + "-" * 120)

    for lic in licenses:
        expiry_str = lic.expiration_date.strftime('%Y-%m-%d') if lic.expiration_date else 'N/A'
        
        if lic.status == "ACTIVE":
            status_color = Fore.GREEN
        elif lic.status == "EXPIRED":
            status_color = Fore.RED
        else: # PENDING, INACTIVE
            status_color = Fore.YELLOW

        api_color = Fore.GREEN if lic.is_active else Fore.RED

        mac_display = lic.mac_address or "Not set"

        line = (
            f"{Fore.WHITE}{lic.key:<24}"
            f"{Fore.LIGHTBLUE_EX}{lic.client_name:<20}"
            f"{Fore.LIGHTMAGENTA_EX}{lic.telegram_username:<15}"
            f"{status_color}{lic.status:<12}"
            f"{api_color}{'ACTIVE' if lic.is_active else 'INACTIVE':<8}"
            f"{Fore.CYAN}{lic.emails_sent:<8}"
            f"{Fore.YELLOW}{mac_display:<20}"
            f"{Fore.WHITE}{expiry_str:<12}"
        )
        print(line)

# Add other admin functions like delete, modify, etc. here if you have them.
# Make sure they use the 'session' object correctly.

def main_menu():
    os.system('cls' if os.name == 'nt' else 'clear')
    try:
        Base.metadata.create_all(ENGINE)
        print(Fore.GREEN + "Database connection successful and tables are ready.")
    except Exception as e:
        print(Fore.RED + f"Could not connect to database or create tables: {e}")
        return

    while True:
        print(Fore.MAGENTA + "\n" + Style.BRIGHT + "-" * 50)
        print(Fore.WHITE + f"| {Fore.CYAN}VEX-SENDER V2 ADMIN CONSOLE{Fore.WHITE} |")
        print(Fore.MAGENTA + Style.BRIGHT + "-" * 50)
        print(Fore.GREEN + "1. Create New License Key")
        print(Fore.GREEN + "2. View All Licenses (DASHBOARD)")
        print(Fore.RED + "3. Exit")
        choice = input(Fore.CYAN + "\n$ VEX_CMD (1-3): ").strip()
        
        if choice == '1':
            create_new_license()
        elif choice == '2':
            view_all_licenses()
        elif choice == '3':
            print(Fore.YELLOW + "Closing console. Goodbye!")
            break
        else:
            print(Fore.RED + "❌ Invalid command. Please enter a number between 1 and 3.")
        
        if choice in ['1', '2']:
            input(Fore.YELLOW + "\nPress Enter to return to the menu...")
            os.system('cls' if os.name == 'nt' else 'clear')

if __name__ == "__main__":
    main_menu()

