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
TELEGRAM_BOT_TOKEN = '8289877773:AAGoKoFFLWCNAzJLCaBYezEWoRvo6vltUIs'
ADMIN_TELEGRAM_ID = '-1002611999679'
DATABASE_FILE = 'admin_licenses.db'
DATABASE_URL = os.environ.get('DATABASE_URL')
ENGINE = create_engine(DATABASE_URL)
Session = sessionmaker(bind=ENGINE)
session = Session()

class License(Base):
    __tablename__ = 'licenses'
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, nullable=False)
    client_name = Column(String, default="N/A")
    telegram_username = Column(String, default="N/A")
    mac_address = Column(String, default="N/A")
    status = Column(String, default="PENDING")
    created_at = Column(DateTime, default=datetime.now)
    activation_date = Column(DateTime)
    expiration_date = Column(DateTime)
    emails_sent = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    def check_expiry(self):
        """Check if license is expired and update status"""
        if self.expiration_date and datetime.now() > self.expiration_date:
            self.status = "EXPIRED"
            self.is_active = False
            session.commit()
            return True
        return False
    
    def renew_license(self, days):
        """Renew expired license with new days"""
        if self.status == "EXPIRED":
            self.expiration_date = datetime.now() + timedelta(days=days)
            self.status = "ACTIVE"
            self.is_active = True
            session.commit()
            return True
        return False

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
    os.system('cls')
    print(Fore.CYAN + "\n" + "=" * 50)
    print(Fore.CYAN + "✨ CREATE NEW LICENSE KEY")
    print(Fore.CYAN + "=" * 50)
    
    duration = input(Fore.YELLOW + ">> Enter duration in days (e.g., 30): ").strip()
    client_name = input(Fore.YELLOW + ">> Enter Client Name: ").strip()
    telegram_user = input(Fore.YELLOW + ">> Enter Telegram Username (@user): ").strip()
    
    try:
        duration_days = int(duration)
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
        status="ACTIVE",
        is_active=True
    )

    try:
        session.add(new_license)
        session.commit()
        print(Fore.GREEN + "\n" + Style.BRIGHT + "✅ LICENSE CREATED SUCCESSFULLY!")
        print(Fore.YELLOW + f" Key: {new_key}")
        print(Fore.YELLOW + f" Client: {client_name} ({telegram_user})")
        print(Fore.YELLOW + f"️  Expires: {expiration_date.strftime('%Y-%m-%d')}")
        print(Fore.GREEN + f" Status: ACTIVE")
        
        notification_msg = (
            f" *New License Key Created*\n"
            f" Key: `{new_key}`\n"
            f" Client: {client_name}\n"
            f" Telegram: {telegram_user}\n"
            f"️ Duration: {duration_days} days\n"
            f" Status: ACTIVE"
        )
        send_telegram_notification(notification_msg)
        
    except Exception as e:
        session.rollback()
        print(Fore.RED + f"❌ Error creating license: {e}")

def view_all_licenses():
    os.system('cls')
    print(Fore.CYAN + "\n" + "=" * 120)
    print(Fore.CYAN + " VEX-SENDER LICENSE DASHBOARD")
    print(Fore.CYAN + "=" * 120)
    
    # Check for expired licenses before displaying
    licenses = session.query(License).all()
    for license in licenses:
        license.check_expiry()
    
    licenses = session.query(License).all()
    
    if not licenses:
        print(Fore.YELLOW + "⚠️ No licenses found in the database.")
        return

    # Print header
    header = f"{Fore.CYAN}{'KEY':<24}{'CLIENT NAME':<20}{'TELEGRAM':<15}{'STATUS':<12}{'API':<8}{'SENT':<8}{'MAC ADDRESS':<20}{'EXPIRY':<12}"
    print(header)
    print(Fore.CYAN + "-" * 120)

    for lic in licenses:
        expiry_str = lic.expiration_date.strftime('%Y-%m-%d') if lic.expiration_date else 'N/A'
        
        # Status color and icon
        if lic.status == "ACTIVE":
            status_color = Fore.GREEN
            status_icon = ""
        elif lic.status == "EXPIRED":
            status_color = Fore.RED
            status_icon = ""
        else:
            status_color = Fore.YELLOW
            status_icon = ""

        # API status
        api_status = "" if lic.is_active else ""
        api_color = Fore.GREEN if lic.is_active else Fore.RED

        # Handle mac_address (could be None)
        mac_display = "Not set"
        if lic.mac_address:
            if len(lic.mac_address) > 18:
                mac_display = lic.mac_address[:15] + '...'
            else:
                mac_display = lic.mac_address

        line = (
            f"{Fore.WHITE}{lic.key:<24}"
            f"{Fore.LIGHTBLUE_EX}{lic.client_name:<20}"
            f"{Fore.LIGHTMAGENTA_EX}{lic.telegram_username:<15}"
            f"{status_color}{status_icon} {lic.status:<10}"
            f"{api_color}{api_status:<8}"
            f"{Fore.CYAN}{lic.emails_sent:<8}"
            f"{Fore.YELLOW}{mac_display:<20}"
            f"{Fore.WHITE}{expiry_str:<12}"
        )
        print(line)

def delete_existing_license():
    os.system('cls')
    print(Fore.RED + "\n" + "=" * 50)
    print(Fore.RED + "️ DELETE LICENSE KEY")
    print(Fore.RED + "=" * 50)
    
    key_to_delete = input(Fore.YELLOW + ">> Enter License Key to delete: ").strip()
    
    license_to_delete = session.query(License).filter_by(key=key_to_delete).first()
    
    if license_to_delete:
        confirm = input(Fore.RED + f"⚠️ Are you sure you want to delete license for {license_to_delete.client_name}? (y/n): ").lower().strip()
        if confirm == 'y':
            session.delete(license_to_delete)
            session.commit()
            print(Fore.GREEN + f"✅ License {key_to_delete} deleted successfully.")
            
            notification_msg = (
                f"️ *License Key Deleted*\n"
                f" Key: `{key_to_delete}`\n"
                f" Client: {license_to_delete.client_name}"
            )
            send_telegram_notification(notification_msg)
        else:
            print(Fore.YELLOW + "Deletion cancelled.")
    else:
        print(Fore.RED + f"❌ License key {key_to_delete} not found.")

def modify_license_duration():
    os.system('cls')
    print(Fore.CYAN + "\n" + "=" * 50)
    print(Fore.CYAN + " MODIFY LICENSE DURATION")
    print(Fore.CYAN + "=" * 50)
    
    key_to_modify = input(Fore.YELLOW + ">> Enter License Key to modify: ").strip()
    
    license_to_modify = session.query(License).filter_by(key=key_to_modify).first()
    
    if not license_to_modify:
        print(Fore.RED + f"❌ License key {key_to_modify} not found.")
        return

    # Check if license is expired
    is_expired = license_to_modify.check_expiry()
    
    print(Fore.GREEN + f"\n Current License Info:")
    print(Fore.YELLOW + f" Client: {license_to_modify.client_name}")
    print(Fore.YELLOW + f" Status: {license_to_modify.status}")
    print(Fore.YELLOW + f"️  Current Expiry: {license_to_modify.expiration_date.strftime('%Y-%m-%d') if license_to_modify.expiration_date else 'N/A'}")
    
    if is_expired:
        print(Fore.RED + f"⚠️  This license has EXPIRED!")
    
    try:
        new_duration = input(Fore.YELLOW + ">> Enter new duration in days: ").strip()
        new_duration_days = int(new_duration)
        
        # Calculate new expiration date
        if license_to_modify.activation_date:
            new_expiration = license_to_modify.activation_date + timedelta(days=new_duration_days)
        else:
            new_expiration = datetime.now() + timedelta(days=new_duration_days)
        
        # Confirm modification
        confirm = input(Fore.CYAN + f"⚠️ Change expiry to {new_expiration.strftime('%Y-%m-%d')}? (y/n): ").lower().strip()
        if confirm == 'y':
            old_expiry = license_to_modify.expiration_date
            license_to_modify.expiration_date = new_expiration
            
            # If license was expired, reactivate it
            if license_to_modify.status == "EXPIRED":
                license_to_modify.status = "ACTIVE"
                license_to_modify.is_active = True
            
            session.commit()
            
            print(Fore.GREEN + f"✅ License duration updated successfully!")
            print(Fore.YELLOW + f" New expiry: {new_expiration.strftime('%Y-%m-%d')}")
            if is_expired:
                print(Fore.GREEN + f"✅ License reactivated!")
            
            notification_msg = (
                f" *License Duration Modified*\n"
                f" Key: `{key_to_modify}`\n"
                f" Client: {license_to_modify.client_name}\n"
                f"️ Old Expiry: {old_expiry.strftime('%Y-%m-%d') if old_expiry else 'N/A'}\n"
                f"️ New Expiry: {new_expiration.strftime('%Y-%m-%d')}\n"
                f" Duration: {new_duration_days} days" +
                (f"\n✅ License Reactivated from EXPIRED" if is_expired else "")
            )
            send_telegram_notification(notification_msg)
        else:
            print(Fore.YELLOW + "Modification cancelled.")
            
    except ValueError:
        print(Fore.RED + "❌ Invalid duration. Please enter a number.")

def toggle_license_activation():
    os.system('cls')
    print(Fore.CYAN + "\n" + "=" * 50)
    print(Fore.CYAN + " TOGGLE LICENSE ACTIVATION")
    print(Fore.CYAN + "=" * 50)
    
    key_to_toggle = input(Fore.YELLOW + ">> Enter License Key to toggle: ").strip()
    
    license_to_toggle = session.query(License).filter_by(key=key_to_toggle).first()
    
    if not license_to_toggle:
        print(Fore.RED + f"❌ License key {key_to_toggle} not found.")
        return

    # Check if license is expired
    is_expired = license_to_toggle.check_expiry()
    if is_expired:
        print(Fore.RED + f"⚠️  This license has EXPIRED and cannot be activated!")
        input(Fore.YELLOW + "\nPress Enter to continue...")
        return

    current_status = "ACTIVE" if license_to_toggle.is_active else "INACTIVE"
    new_status = not license_to_toggle.is_active
    
    print(Fore.GREEN + f"\n Current License Info:")
    print(Fore.YELLOW + f" Client: {license_to_toggle.client_name}")
    print(Fore.YELLOW + f" Current API Status: {current_status}")
    print(Fore.YELLOW + f" MAC Address: {license_to_toggle.mac_address or 'Not set'}")
    
    action = "activate" if new_status else "deactivate"
    confirm = input(Fore.CYAN + f"⚠️ Are you sure you want to {action} this license? (y/n): ").lower().strip()
    
    if confirm == 'y':
        old_mac = license_to_toggle.mac_address
        old_status = "ACTIVE" if license_to_toggle.is_active else "INACTIVE"
        
        # If deactivating, clear MAC address
        if not new_status:
            license_to_toggle.mac_address = None
            if license_to_toggle.status == "ACTIVE":
                license_to_toggle.status = "INACTIVE"
        
        license_to_toggle.is_active = new_status
        session.commit()
        
        new_status_text = "ACTIVE" if new_status else "INACTIVE"
        status_color = Fore.GREEN if new_status else Fore.RED
        
        print(status_color + f"\n✅ License {action}d successfully!")
        print(Fore.YELLOW + f" New API Status: {new_status_text}")
        
        if not new_status and old_mac:
            print(Fore.YELLOW + f"️  MAC Address cleared: {old_mac}")
        
        notification_msg = (
            f" *License Activation Changed*\n"
            f" Key: `{key_to_toggle}`\n"
            f" Client: {license_to_toggle.client_name}\n"
            f" Old Status: {old_status}\n"
            f" New Status: {new_status_text}" +
            (f"\n️ MAC Address Cleared" if not new_status and old_mac else "")
        )
        send_telegram_notification(notification_msg)
    else:
        print(Fore.YELLOW + "Operation cancelled.")

def renew_expired_license():
    os.system('cls')
    print(Fore.GREEN + "\n" + "=" * 50)
    print(Fore.GREEN + " RENEW EXPIRED LICENSE")
    print(Fore.GREEN + "=" * 50)
    
    key_to_renew = input(Fore.YELLOW + ">> Enter expired License Key to renew: ").strip()
    
    license_to_renew = session.query(License).filter_by(key=key_to_renew).first()
    
    if not license_to_renew:
        print(Fore.RED + f"❌ License key {key_to_renew} not found.")
        return

    # Check if license is actually expired
    if license_to_renew.status != "EXPIRED":
        print(Fore.YELLOW + f"⚠️  This license is not expired. Current status: {license_to_renew.status}")
        return

    try:
        new_duration = input(Fore.YELLOW + ">> Enter renewal duration in days: ").strip()
        new_duration_days = int(new_duration)
        
        # Renew the license
        if license_to_renew.renew_license(new_duration_days):
            print(Fore.GREEN + f"✅ License renewed successfully!")
            print(Fore.YELLOW + f" Client: {license_to_renew.client_name}")
            print(Fore.YELLOW + f"️  New expiry: {license_to_renew.expiration_date.strftime('%Y-%m-%d')}")
            print(Fore.GREEN + f" Status: ACTIVE")
            
            notification_msg = (
                f" *Expired License Renewed*\n"
                f" Key: `{key_to_renew}`\n"
                f" Client: {license_to_renew.client_name}\n"
                f"️ New Expiry: {license_to_renew.expiration_date.strftime('%Y-%m-%d')}\n"
                f" Duration: {new_duration_days} days"
            )
            send_telegram_notification(notification_msg)
        else:
            print(Fore.RED + "❌ Failed to renew license.")
            
    except ValueError:
        print(Fore.RED + "❌ Invalid duration. Please enter a number.")

def main_menu():
    os.system('cls')
    Base.metadata.create_all(ENGINE)
    while True:
        print(Fore.MAGENTA + "\n" + Style.BRIGHT + "-" * 50)
        print(Fore.WHITE + f"| {Fore.CYAN}VEX-SENDER V2 ADMIN CONSOLE{Fore.WHITE} |")
        print(Fore.WHITE + f"| {Fore.YELLOW}ADMIN: MOHAMED SAMY{Fore.WHITE}{' ' * 24}|")
        print(Fore.MAGENTA + Style.BRIGHT + "-" * 50)
        print(Fore.GREEN + "1. Create New License Key")
        print(Fore.GREEN + "2. View All Licenses (DASHBOARD)")
        print(Fore.CYAN + "3. Modify License Duration")
        print(Fore.BLUE + "4. Toggle License Activation")
        print(Fore.GREEN + "5. Renew Expired License")
        print(Fore.RED + "6. Delete License Key")
        print(Fore.YELLOW + "7. Exit")
        choice = input(Fore.CYAN + "\n$ VEX_CMD (1-7): ").strip()
        
        if choice == '1':
            create_new_license()
        elif choice == '2':
            view_all_licenses()
        elif choice == '3':
            modify_license_duration()
        elif choice == '4':
            toggle_license_activation()
        elif choice == '5':
            renew_expired_license()
        elif choice == '6':
            delete_existing_license()
        elif choice == '7':
            print(Fore.YELLOW + "Closing console. Goodbye!")
            break
        else:
            print(Fore.RED + "❌ Invalid command. Please enter a number between 1 and 7.")
        
        if choice in ['1', '2', '3', '4', '5', '6']:
            input(Fore.YELLOW + "\nPress Enter to return to the menu...")
            os.system('cls')

if __name__ == "__main__":
    main_menu()