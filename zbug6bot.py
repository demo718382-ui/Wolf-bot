import telebot
import json
import os
import time
import threading
import asyncio
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon import errors
from datetime import datetime, timedelta
import pytz

print("🚀 TELEGRAM BOT WITH TELETHON STARTING...")

# ==================== CONFIGURATION ====================
API_TOKEN = "8377183652:AAGxMNq1YAkoliSxux_w463LlDTTbqEuF6M"
ADMIN_IDS = [7171541681, 8120773616, 7867203771, 8409211588, 7777085531]

# Sudo users storage file
SUDO_FILE = "sudo_users.json"

# User Account Credentials
USER_API_ID = 25754950
USER_API_HASH = "c8954f3b465bdd257e2285929782f62c"
USER_SESSION_STRING = "YOUR_SESSION_STRING_HERE"

# Default settings
DEFAULT_INTERVAL_MIN = 10
DEFAULT_WORK_MIN = 120
DEFAULT_REST_MIN = 60

# Indian Timezone (Kolkata)
INDIAN_TIMEZONE = pytz.timezone('Asia/Kolkata')

# ==================== AUTOSET SCHEDULE CONFIG ====================
AUTOSET_SCHEDULE = [
    {"start": "06:00", "end": "09:00", "type": "work"},
    {"start": "09:00", "end": "10:00", "type": "rest"},
    {"start": "10:00", "end": "12:00", "type": "work"},
    {"start": "12:00", "end": "13:00", "type": "rest"},
    {"start": "13:00", "end": "15:00", "type": "work"},
    {"start": "15:00", "end": "16:00", "type": "rest"},
    {"start": "16:00", "end": "18:00", "type": "work"},
    {"start": "18:00", "end": "19:00", "type": "rest"},
    {"start": "19:00", "end": "21:00", "type": "work"},
    {"start": "21:00", "end": "22:00", "type": "rest"},
    {"start": "22:00", "end": "00:00", "type": "work"},
    {"start": "00:00", "end": "06:00", "type": "rest"}
]

# ==================== BOT SETUP ====================
bot = telebot.TeleBot(API_TOKEN)

# ==================== SUDO USERS MANAGEMENT ====================
def load_sudo_users():
    """Load sudo users from file"""
    try:
        if os.path.exists(SUDO_FILE):
            with open(SUDO_FILE, 'r') as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"Error loading sudo users: {e}")
        return []

def save_sudo_users(sudo_users):
    """Save sudo users to file"""
    try:
        with open(SUDO_FILE, 'w') as f:
            json.dump(sudo_users, f, indent=2)
    except Exception as e:
        print(f"Error saving sudo users: {e}")

def is_sudo(user_id):
    """Check if user is sudo"""
    sudo_users = load_sudo_users()
    return user_id in sudo_users

def is_admin_or_sudo(user_id):
    """Check if user is admin or sudo"""
    return user_id in ADMIN_IDS or is_sudo(user_id)

# Initialize sudo users
sudo_users = load_sudo_users()

# ==================== USER ACCOUNT MANAGER WITH TELETHON ====================
class UserAccountManager:
    def __init__(self, session_string=None):
        self.is_connected = False
        self.user_name = "Not Connected"
        self.user_id = None
        self.session_string = session_string or USER_SESSION_STRING
        self.client = None
        self.loop = None
        
    def connect_user_account(self):
        """Connect to user account using Telethon"""
        try:
            if not self.session_string or self.session_string == "YOUR_SESSION_STRING_HERE":
                self.is_connected = False
                self.user_name = "Session Not Set"
                return False
            
            # Disconnect existing connection if any
            self.disconnect()
            
            # Create new event loop for Telethon
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # Initialize Telethon client
            self.client = TelegramClient(
                StringSession(self.session_string),
                USER_API_ID,
                USER_API_HASH,
                loop=self.loop
            )
            
            # Connect and authenticate
            self.loop.run_until_complete(self.client.connect())
            
            if self.loop.run_until_complete(self.client.is_user_authorized()):
                me = self.loop.run_until_complete(self.client.get_me())
                self.user_name = f"{me.first_name or ''} {me.last_name or ''}".strip() or f"User{me.id}"
                self.user_id = me.id
                self.is_connected = True
                print(f"✅ User Account Connected: {self.user_name} (ID: {self.user_id})")
                return True
            else:
                self.is_connected = False
                self.user_name = "Not Authorized - Invalid Session"
                return False
                
        except Exception as e:
            print(f"❌ User account connection failed: {e}")
            self.is_connected = False
            self.user_name = f"Connection Failed: {str(e)}"
            return False
    
    def resolve_chat_identifier(self, chat_identifier):
        """Resolve chat identifier to proper chat entity"""
        if not self.is_connected or not self.client:
            return None, "User account not connected"
            
        try:
            async def resolve_chat():
                try:
                    entity = await self.client.get_entity(chat_identifier)
                    return entity, None
                except ValueError:
                    try:
                        entity = await self.client.get_entity(int(chat_identifier))
                        return entity, None
                    except (ValueError, TypeError):
                        return None, "Invalid chat identifier format"
                except Exception as e:
                    return None, f"Failed to resolve chat: {str(e)}"
            
            entity, error = self.loop.run_until_complete(resolve_chat())
            return entity, error
            
        except Exception as e:
            return None, f"Resolution failed: {str(e)}"
    
    def send_message_direct(self, chat_identifier, text):
        """Send message using Telethon to any chat identifier"""
        if not self.is_connected or not self.client:
            return False, "User account not connected"
            
        try:
            entity, error = self.resolve_chat_identifier(chat_identifier)
            if error:
                return False, error
            
            async def send_msg():
                await self.client.send_message(entity, text)
                return True
                
            success = self.loop.run_until_complete(send_msg())
            return True, f"Message sent successfully to {getattr(entity, 'title', getattr(entity, 'username', 'Unknown'))}"
            
        except errors.FloodWaitError as e:
            return False, f"Flood wait: {e.seconds} seconds"
        except errors.ChatWriteForbiddenError:
            return False, "No permission to send messages in this chat"
        except errors.ChannelPrivateError:
            return False, "Not a member of this channel/group"
        except errors.UserNotParticipantError:
            return False, "Not a member of this group/channel"
        except Exception as e:
            return False, f"Send failed: {str(e)}"
    
    def send_media_direct(self, chat_identifier, file_path, caption):
        """Send media using Telethon to any chat identifier"""
        if not self.is_connected or not self.client:
            return False, "User account not connected"
            
        try:
            entity, error = self.resolve_chat_identifier(chat_identifier)
            if error:
                return False, error
            
            async def send_media():
                await self.client.send_file(entity, file_path, caption=caption)
                return True
                
            success = self.loop.run_until_complete(send_media())
            return True, f"Media sent successfully to {getattr(entity, 'title', getattr(entity, 'username', 'Unknown'))}"
            
        except Exception as e:
            return False, f"Media send failed: {str(e)}"
    
    def disconnect(self):
        """Disconnect Telethon client"""
        if self.client and self.loop:
            try:
                if self.loop.is_running():
                    self.loop.run_until_complete(self.client.disconnect())
                self.loop.close()
            except:
                pass
            self.client = None
            self.loop = None
        self.is_connected = False

# ==================== STATE MANAGEMENT ====================
ADMIN_STATES_FILE = "admin_states.json"

DEFAULT_STATE = {
    "target_entities": [],
    "interval_min": DEFAULT_INTERVAL_MIN,
    "work_min": DEFAULT_WORK_MIN,
    "rest_min": DEFAULT_REST_MIN,
    "scheduled_message": None,
    "running": False,
    "bot_started": False,
    "autoschedule_enabled": False,
    "user_session_string": USER_SESSION_STRING,
    "last_message_time": 0  # Track last message time to prevent spam
}

def load_admin_states():
    """Load states for all admins"""
    try:
        if os.path.exists(ADMIN_STATES_FILE):
            with open(ADMIN_STATES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Error loading admin states: {e}")
        return {}

def save_admin_states(admin_states):
    """Save states for all admins"""
    try:
        with open(ADMIN_STATES_FILE, 'w', encoding='utf-8') as f:
            json.dump(admin_states, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving admin states: {e}")

def get_admin_state(admin_id):
    """Get state for specific admin"""
    admin_states = load_admin_states()
    admin_id_str = str(admin_id)
    
    if admin_id_str not in admin_states:
        admin_states[admin_id_str] = DEFAULT_STATE.copy()
        save_admin_states(admin_states)
    
    return admin_states[admin_id_str]

def save_admin_state(admin_id, state):
    """Save state for specific admin"""
    admin_states = load_admin_states()
    admin_id_str = str(admin_id)
    admin_states[admin_id_str] = state
    save_admin_states(admin_states)

def get_user_manager_for_admin(admin_id):
    """Get user manager instance for specific admin"""
    state = get_admin_state(admin_id)
    session_string = state.get("user_session_string", USER_SESSION_STRING)
    
    user_mgr = UserAccountManager(session_string)
    user_mgr.connect_user_account()
    return user_mgr

# ==================== UTILITY FUNCTIONS ====================
def is_admin(user_id):
    return user_id in ADMIN_IDS

def notify_admins(text):
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id, text)
        except Exception as e:
            print(f"Failed to notify admin {admin_id}: {e}")

def download_media(file_id, file_name):
    """Download media file from Telegram"""
    try:
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        file_path = f"downloads/{file_name}"
        os.makedirs("downloads", exist_ok=True)
        
        with open(file_path, 'wb') as new_file:
            new_file.write(downloaded_file)
        
        return file_path
    except Exception as e:
        print(f"Download error: {e}")
        return None

def validate_chat_identifier(identifier):
    """Validate chat identifier format"""
    if not identifier or not identifier.strip():
        return False, "Identifier cannot be empty"
    
    identifier = identifier.strip()
    
    if identifier.lstrip('-').isdigit():
        return True, "numeric_id"
    
    if identifier.startswith('@'):
        if len(identifier) > 1 and all(c.isalnum() or c == '_' for c in identifier[1:]):
            return True, "username"
        return False, "Invalid username format"
    
    if 't.me' in identifier or 'telegram.me' in identifier:
        return True, "invite_link"
    
    if all(c.isalnum() or c == '_' for c in identifier):
        return True, "username"
    
    return False, "Invalid identifier format"

def get_indian_time():
    """Get current Indian time (Kolkata - IST)"""
    return datetime.now(INDIAN_TIMEZONE)

def format_time_12hr(time_str):
    """Convert 24hr time to 12hr format with AM/PM"""
    try:
        hour, minute = map(int, time_str.split(':'))
        if hour == 0:
            return f"12:{minute:02d} AM"
        elif hour < 12:
            return f"{hour}:{minute:02d} AM"
        elif hour == 12:
            return f"12:{minute:02d} PM"
        else:
            return f"{hour-12}:{minute:02d} PM"
    except:
        return time_str

def get_current_time_slot():
    """Get current time slot from schedule"""
    now = get_indian_time()
    current_hour = now.hour
    current_minute = now.minute
    
    for slot in AUTOSET_SCHEDULE:
        start_hour, start_min = map(int, slot["start"].split(":"))
        end_hour, end_min = map(int, slot["end"].split(":"))
        
        start_total = start_hour * 60 + start_min
        end_total = end_hour * 60 + end_min
        current_total = current_hour * 60 + current_minute
        
        if start_total > end_total:
            if current_total >= start_total or current_total < end_total:
                return slot
        else:
            if start_total <= current_total < end_total:
                return slot
    
    if 6 <= current_hour < 9:
        return AUTOSET_SCHEDULE[0]
    elif 9 <= current_hour < 10:
        return AUTOSET_SCHEDULE[1]
    elif 10 <= current_hour < 12:
        return AUTOSET_SCHEDULE[2]
    elif 12 <= current_hour < 13:
        return AUTOSET_SCHEDULE[3]
    elif 13 <= current_hour < 15:
        return AUTOSET_SCHEDULE[4]
    elif 15 <= current_hour < 16:
        return AUTOSET_SCHEDULE[5]
    elif 16 <= current_hour < 18:
        return AUTOSET_SCHEDULE[6]
    elif 18 <= current_hour < 19:
        return AUTOSET_SCHEDULE[7]
    elif 19 <= current_hour < 21:
        return AUTOSET_SCHEDULE[8]
    elif 21 <= current_hour < 22:
        return AUTOSET_SCHEDULE[9]
    elif 22 <= current_hour < 24:
        return AUTOSET_SCHEDULE[10]
    else:
        return AUTOSET_SCHEDULE[11]

def get_current_time_formatted():
    """Get current Indian time in 12hr format"""
    return get_indian_time().strftime("%I:%M %p")

def get_next_slots():
    """Get current, next work and next rest slots"""
    current_slot = get_current_time_slot()
    current_index = AUTOSET_SCHEDULE.index(current_slot)
    
    next_work = None
    next_rest = None
    
    for i in range(current_index + 1, len(AUTOSET_SCHEDULE)):
        if AUTOSET_SCHEDULE[i]["type"] == "work":
            next_work = AUTOSET_SCHEDULE[i]
            break
    
    if not next_work:
        for i in range(0, current_index):
            if AUTOSET_SCHEDULE[i]["type"] == "work":
                next_work = AUTOSET_SCHEDULE[i]
                break
    
    for i in range(current_index + 1, len(AUTOSET_SCHEDULE)):
        if AUTOSET_SCHEDULE[i]["type"] == "rest":
            next_rest = AUTOSET_SCHEDULE[i]
            break
    
    if not next_rest:
        for i in range(0, current_index):
            if AUTOSET_SCHEDULE[i]["type"] == "rest":
                next_rest = AUTOSET_SCHEDULE[i]
                break
    
    return current_slot, next_work, next_rest

# ==================== SUDO COMMAND HANDLERS ====================
@bot.message_handler(commands=['addsudo'])
def addsudo_handler(message):
    """Add user to sudo"""
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Only main admin can use this command!")
        return
    
    if len(message.text.split()) < 2:
        bot.reply_to(message, "⚠️ Usage: /addsudo <user_id>")
        return
    
    try:
        user_id = int(message.text.split()[1])
        sudo_users = load_sudo_users()
        
        if user_id in sudo_users:
            bot.reply_to(message, "ℹ️ User is already a sudo admin!")
        else:
            sudo_users.append(user_id)
            save_sudo_users(sudo_users)
            bot.reply_to(message, f"✅ User {user_id} added as sudo admin!")
            
    except ValueError:
        bot.reply_to(message, "❌ Invalid user ID!")

@bot.message_handler(commands=['remsudo'])
def remsudo_handler(message):
    """Remove user from sudo"""
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Only main admin can use this command!")
        return
    
    if len(message.text.split()) < 2:
        bot.reply_to(message, "⚠️ Usage: /remsudo <user_id>")
        return
    
    try:
        user_id = int(message.text.split()[1])
        sudo_users = load_sudo_users()
        
        if user_id in sudo_users:
            sudo_users.remove(user_id)
            save_sudo_users(sudo_users)
            bot.reply_to(message, f"✅ User {user_id} removed from sudo!")
        else:
            bot.reply_to(message, "❌ User is not a sudo admin!")
            
    except ValueError:
        bot.reply_to(message, "❌ Invalid user ID!")

@bot.message_handler(commands=['adminlist'])
def adminlist_handler(message):
    """Show all admins and sudo admins"""
    if not is_admin_or_sudo(message.from_user.id):
        return
    
    main_admins = ADMIN_IDS
    sudo_admins = load_sudo_users()
    
    admin_list_text = "👑 **Admin List**\n\n"
    
    admin_list_text += "🔸 **Main Admins:**\n"
    for i, admin_id in enumerate(main_admins, 1):
        admin_list_text += f"{i}. `{admin_id}`\n"
    
    admin_list_text += "\n🔹 **Sudo Admins:**\n"
    if sudo_admins:
        for i, sudo_id in enumerate(sudo_admins, 1):
            admin_list_text += f"{i}. `{sudo_id}`\n"
    else:
        admin_list_text += "No sudo admins added yet.\n"
    
    admin_list_text += f"\n📊 Total: {len(main_admins)} main + {len(sudo_admins)} sudo = {len(main_admins) + len(sudo_admins)} admins"
    
    bot.reply_to(message, admin_list_text)

# ==================== COMMAND HANDLERS ====================
@bot.message_handler(commands=['start'])
def start_handler(message):
    if not is_admin_or_sudo(message.from_user.id):
        bot.reply_to(message, "❌ Not authorized")
        return
    
    state = get_admin_state(message.from_user.id)
    
    if not state["bot_started"]:
        state["bot_started"] = True
        save_admin_state(message.from_user.id, state)
        
        user_manager = get_user_manager_for_admin(message.from_user.id)
        
        welcome_text = f"""🚀 **User Account Scheduler Bot Started!**

🤖 Bot Account: ✅ Connected
👤 User Account: {'✅ ' + user_manager.user_name if user_manager.is_connected else '❌ ' + user_manager.user_name}
🆔 User ID: {user_manager.user_id or 'N/A'}
🎯 Entities: {len(state['target_entities'])}

💡 Use /help for all commands"""
        
        bot.reply_to(message, welcome_text)
    else:
        user_manager = get_user_manager_for_admin(message.from_user.id)
        entities_count = len(state["target_entities"])
        user_status = f"{'✅ ' + user_manager.user_name if user_manager.is_connected else '❌ ' + user_manager.user_name}"
        
        status_text = f"""🤖 User Account Scheduler Bot

🔹 Status: ✅ Running  
🔹 User Account: {user_status}
🔹 User ID: {user_manager.user_id or 'N/A'}
🔹 Entities: {entities_count}
🔹 Scheduler: {'🟢 RUNNING' if state['running'] else '🔴 STOPPED'}
🔹 Auto Schedule: {'🟢 ACTIVE' if state.get('autoschedule_enabled') else '🔴 INACTIVE'}"""
        
        bot.reply_to(message, status_text)

@bot.message_handler(commands=['help'])
def help_handler(message):
    if not is_admin_or_sudo(message.from_user.id):
        return
    
    help_text = """
🤖 **User Account Scheduler Bot - Commands**

🔐 **Account Settings:**
/setsession - Set user session string
/checkuser - Check user account status

🎯 **Entity Management:**
/addentity <identifier> - Add group/channel
/listentities - Show all entities
/removeentity <number> - Remove entity
/clearentities - Clear all entities

📝 **Message Setup:**
/setmsg - Reply to any message to set as scheduled content

⚙️ **Scheduler Controls:**
/setcycle <interval> <work> <rest> - Set timing
/start_scheduler - Start sending messages
/stop_scheduler - Stop sending
/status - Check current status

🔄 **Auto Schedule:**
/autoset - Start automatic daily schedule
/autostop - Stop auto schedule
/autowork - Show current work schedule status

🔧 **Testing:**
/test <identifier> - Test message sending

👑 **Admin Management:**
/addsudo <user_id> - Add sudo admin (main admin only)
/remsudo <user_id> - Remove sudo admin (main admin only)
/adminlist - Show all admins

🗑️ **Data Management:**
/clearcache - Clear all data and reset bot
"""
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['clearcache'])
def clearcache_handler(message):
    if not is_admin_or_sudo(message.from_user.id):
        return
    
    try:
        if os.path.exists(ADMIN_STATES_FILE):
            file_size = os.path.getsize(ADMIN_STATES_FILE)
            os.remove(ADMIN_STATES_FILE)
        else:
            file_size = 0
            
        import shutil
        if os.path.exists("downloads"):
            shutil.rmtree("downloads")
            os.makedirs("downloads", exist_ok=True)
        
        bot.reply_to(message, f"""🗑️ **Cache Cleared Successfully!**

✅ Admin states file deleted
✅ Temporary files cleaned
📊 Freed up: {file_size} bytes

All data has been reset. Use /start to begin fresh.""")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error clearing cache: {str(e)}")

@bot.message_handler(commands=['setsession'])
def setsession_handler(message):
    if not is_admin_or_sudo(message.from_user.id):
        return
    
    if len(message.text.split()) < 2:
        bot.reply_to(message, "❌ Usage: /setsession <session_string>")
        return
    
    session_string = message.text.split(maxsplit=1)[1]
    
    state = get_admin_state(message.from_user.id)
    state["user_session_string"] = session_string
    save_admin_state(message.from_user.id, state)
    
    user_manager = UserAccountManager(session_string)
    user_connected = user_manager.connect_user_account()
    
    if user_connected:
        bot.reply_to(message, f"""✅ **User Account Connected Successfully!**

👤 Account Name: {user_manager.user_name}
🆔 Account ID: {user_manager.user_id}
🔗 Status: ✅ Connected via Telethon""")
    else:
        bot.reply_to(message, f"❌ **Failed to connect user account**\n\nError: {user_manager.user_name}")

@bot.message_handler(commands=['checkuser'])
def checkuser_handler(message):
    if not is_admin_or_sudo(message.from_user.id):
        return
    
    user_manager = get_user_manager_for_admin(message.from_user.id)
    
    if user_manager.is_connected:
        bot.reply_to(message, f"""✅ **User Account Status**

👤 Name: {user_manager.user_name}
🆔 ID: {user_manager.user_id}
🔗 Status: ✅ Connected via Telethon""")
    else:
        bot.reply_to(message, f"❌ **User Account Not Connected**\n\nReason: {user_manager.user_name}")

@bot.message_handler(commands=['setmsg'])
def setmsg_handler(message):
    if not is_admin_or_sudo(message.from_user.id):
        return
    
    state = get_admin_state(message.from_user.id)
    if not state["bot_started"]:
        bot.reply_to(message, "❌ Bot is not started. Use /start first")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Please reply to a message that you want to set as scheduled message")
        return
    
    replied = message.reply_to_message
    msg_data = {
        "text": replied.text or replied.caption or "",
        "file_id": None,
        "file_type": None
    }
    
    # Handle different media types
    if replied.photo:
        msg_data["file_id"] = replied.photo[-1].file_id
        msg_data["file_type"] = "photo"
        print(f"📷 Photo message set - File ID: {msg_data['file_id']}")
    elif replied.video:
        msg_data["file_id"] = replied.video.file_id
        msg_data["file_type"] = "video"
        print(f"🎥 Video message set - File ID: {msg_data['file_id']}")
    elif replied.document:
        msg_data["file_id"] = replied.document.file_id
        msg_data["file_type"] = "document"
        print(f"📄 Document message set - File ID: {msg_data['file_id']}")
    elif replied.audio:
        msg_data["file_id"] = replied.audio.file_id
        msg_data["file_type"] = "audio"
        print(f"🎵 Audio message set - File ID: {msg_data['file_id']}")
    
    state["scheduled_message"] = msg_data
    save_admin_state(message.from_user.id, state)
    
    # Create preview
    if msg_data["file_id"]:
        preview = f"📷 {msg_data['file_type'].title()}" + (f" + Text" if msg_data["text"] else "")
    else:
        preview = msg_data['text'][:100] + "..." if len(msg_data['text']) > 100 else msg_data['text']
    
    bot.reply_to(message, f"✅ **Message Set Successfully!**\n\nContent: {preview}")

@bot.message_handler(commands=['addentity'])
def addentity_handler(message):
    if not is_admin_or_sudo(message.from_user.id):
        return
    
    state = get_admin_state(message.from_user.id)
    if not state["bot_started"]:
        bot.reply_to(message, "❌ Bot is not started. Use /start first")
        return
    
    if len(message.text.split()) < 2:
        bot.reply_to(message, "❌ Usage: /addentity <identifier>\n\nExamples:\n/addentity @username\n/addentity -100123456789\n/addentity https://t.me/joinchat/...")
        return
    
    entity_input = message.text.split(maxsplit=1)[1].strip()
    
    is_valid, id_type = validate_chat_identifier(entity_input)
    if not is_valid:
        bot.reply_to(message, f"❌ Invalid chat identifier: {id_type}")
        return
    
    user_manager = get_user_manager_for_admin(message.from_user.id)
    if not user_manager.is_connected:
        bot.reply_to(message, "❌ User account not connected. Use /setsession first.")
        return
    
    entity, error = user_manager.resolve_chat_identifier(entity_input)
    if error:
        bot.reply_to(message, f"❌ Cannot access this chat: {error}\n\nMake sure:\n• The user account is member of the group/channel\n• The identifier is correct\n• It's a valid chat")
        return
    
    entity_info = {
        'title': getattr(entity, 'title', getattr(entity, 'username', entity_input)),
        'identifier': entity_input,
        'type': id_type,
        'resolved_name': getattr(entity, 'title', getattr(entity, 'username', 'Unknown')),
        'added_at': time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    for existing in state["target_entities"]:
        if existing['identifier'] == entity_info['identifier']:
            bot.reply_to(message, "ℹ️ This entity is already in the list")
            return
    
    state["target_entities"].append(entity_info)
    save_admin_state(message.from_user.id, state)
    
    bot.reply_to(message, f"""✅ **Entity Added!**

📝 Name: {entity_info['resolved_name']}
🔗 Type: {entity_info['type']}
🆔 Identifier: {entity_info['identifier']}
📊 Total: {len(state['target_entities'])} entities""")

@bot.message_handler(commands=['listentities'])
def listentities_handler(message):
    if not is_admin_or_sudo(message.from_user.id):
        return
    
    state = get_admin_state(message.from_user.id)
    entities = state["target_entities"]
    
    if not entities:
        bot.reply_to(message, "❌ No entities added yet.")
        return
    
    response = "🎯 **Target Entities:**\n\n"
    for i, entity in enumerate(entities, 1):
        response += f"{i}. **{entity['resolved_name']}**\n"
        response += f"   🔗 {entity['type']}: `{entity['identifier']}`\n\n"
    
    response += f"📊 Total: {len(entities)} entities"
    
    bot.reply_to(message, response)

@bot.message_handler(commands=['removeentity'])
def removeentity_handler(message):
    if not is_admin_or_sudo(message.from_user.id):
        return
    
    state = get_admin_state(message.from_user.id)
    entities = state["target_entities"]
    
    if not entities:
        bot.reply_to(message, "❌ No entities to remove")
        return
    
    if len(message.text.split()) < 2:
        response = "🗑️ **Remove Entity**\n\n"
        for i, entity in enumerate(entities, 1):
            response += f"{i}. {entity['resolved_name']} (`{entity['identifier']}`)\n"
        
        response += f"\nUsage: /removeentity <number>"
        bot.reply_to(message, response)
        return
    
    try:
        entity_num = int(message.text.split()[1])
        if 1 <= entity_num <= len(entities):
            removed_entity = entities[entity_num - 1]
            state["target_entities"].pop(entity_num - 1)
            save_admin_state(message.from_user.id, state)
            bot.reply_to(message, f"✅ **Entity Removed:** {removed_entity['resolved_name']} (`{removed_entity['identifier']}`)")
        else:
            bot.reply_to(message, f"❌ Invalid number. Use 1-{len(entities)}")
    except ValueError:
        bot.reply_to(message, "❌ Please enter a valid number")

@bot.message_handler(commands=['clearentities'])
def clearentities_handler(message):
    if not is_admin_or_sudo(message.from_user.id):
        return
    
    state = get_admin_state(message.from_user.id)
    if not state["target_entities"]:
        bot.reply_to(message, "❌ No entities to clear")
        return
    
    entity_count = len(state["target_entities"])
    state["target_entities"] = []
    save_admin_state(message.from_user.id, state)
    
    bot.reply_to(message, f"🗑️ **All Entities Cleared!**\n\n{entity_count} entities removed.")


@bot.message_handler(commands=['allentity'])
def allentity_handler(message):
    if not is_admin_or_sudo(message.from_user.id):
        return
    
    state = get_admin_state(message.from_user.id)
    if not state["bot_started"]:
        bot.reply_to(message, "❌ Bot is not started. Use /start first")
        return
    
    user_manager = get_user_manager_for_admin(message.from_user.id)
    if not user_manager.is_connected:
        bot.reply_to(message, "❌ User account not connected. Use /setsession first.")
        return

    bot.reply_to(message, "🔄 Fetching all your groups and channels...")
    
    try:
        async def get_all_dialogs():
            dialogs = []
            async for dialog in user_manager.client.iter_dialogs():
                if dialog.is_group or dialog.is_channel:
                    # Skip if it's the user's saved messages
                    if dialog.id == user_manager.user_id:
                        continue
                    dialogs.append(dialog)
            return dialogs
        
        dialogs = user_manager.loop.run_until_complete(get_all_dialogs())
        
        added_count = 0
        already_count = 0
        
        for dialog in dialogs:
            entity = dialog.entity
            
            # Get identifier
            if hasattr(entity, 'username') and entity.username:
                identifier = f"@{entity.username}"
            else:
                identifier = str(entity.id)
            
            entity_info = {
                'title': getattr(entity, 'title', getattr(entity, 'username', identifier)),
                'identifier': identifier,
                'type': 'username' if hasattr(entity, 'username') and entity.username else 'numeric_id',
                'resolved_name': getattr(entity, 'title', getattr(entity, 'username', 'Unknown')),
                'added_at': time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Check if already exists
            exists = False
            for existing in state["target_entities"]:
                if existing['identifier'] == entity_info['identifier']:
                    exists = True
                    already_count += 1
                    break
            
            if not exists:
                state["target_entities"].append(entity_info)
                added_count += 1
        
        save_admin_state(message.from_user.id, state)
        
        response = f"""✅ **All Groups/Channels Added!**

📊 Results:
• ✅ Newly Added: {added_count}
• ℹ️ Already Existed: {already_count}
• 📝 Total Now: {len(state['target_entities'])} entities

💡 Use /listentities to see all groups
🚀 Use /autoset to start auto-scheduling"""

        bot.reply_to(message, response)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error fetching groups: {str(e)}")

@bot.message_handler(commands=['delentity'])
def delentity_handler(message):
    if not is_admin_or_sudo(message.from_user.id):
        return
    
    state = get_admin_state(message.from_user.id)
    entities = state["target_entities"]
    
    if not entities:
        bot.reply_to(message, "❌ No entities to delete")
        return
    
    entity_count = len(entities)
    state["target_entities"] = []
    save_admin_state(message.from_user.id, state)
    
    bot.reply_to_message(message, f"""🗑️ **All Entities Deleted!**

✅ Removed {entity_count} groups/channels
📝 Target list is now empty

💡 Use /allentity to add all groups again
🔧 Use /addentity to add specific groups""")



@bot.message_handler(commands=['setcycle'])
def setcycle_handler(message):
    if not is_admin_or_sudo(message.from_user.id):
        return
    
    parts = message.text.split()
    if len(parts) != 4:
        bot.reply_to(message, "❌ Usage: /setcycle <interval> <work> <rest>")
        return
    
    try:
        interval = int(parts[1])
        work = int(parts[2])
        rest = int(parts[3])
        
        if interval <= 0 or work <= 0 or rest <= 0:
            bot.reply_to(message, "❌ All values must be positive numbers")
            return
        
        state = get_admin_state(message.from_user.id)
        state["interval_min"] = interval
        state["work_min"] = work
        state["rest_min"] = rest
        save_admin_state(message.from_user.id, state)
        
        bot.reply_to(message, f"✅ **Cycle Updated!**\n\nInterval: {interval}m\nWork: {work}m\nRest: {rest}m")
        
    except ValueError:
        bot.reply_to(message, "❌ Please enter valid numbers")

@bot.message_handler(commands=['status'])
def status_handler(message):
    if not is_admin_or_sudo(message.from_user.id):
        return
    
    state = get_admin_state(message.from_user.id)
    entities = state["target_entities"]
    message_data = state["scheduled_message"]
    
    user_manager = get_user_manager_for_admin(message.from_user.id)
    
    current_slot = get_current_time_slot()
    current_time = get_current_time_formatted()
    
    status_text = f"""
🤖 **Bot Status**

🕒 Indian Time: {current_time}
🔹 Bot: ✅ RUNNING
🔹 Scheduler: {'🟢 ACTIVE' if state['running'] else '🔴 INACTIVE'}
🔹 Auto Schedule: {'🟢 ACTIVE' if state.get('autoschedule_enabled') else '🔴 INACTIVE'}
🔹 User Account: {'✅ ' + user_manager.user_name if user_manager.is_connected else '❌ ' + user_manager.user_name}
🔹 User ID: {user_manager.user_id or 'N/A'}
🔹 Entities: {len(entities)}
🔹 Current Slot: {'🟢 WORK' if current_slot['type'] == 'work' else '🔴 REST'} ({format_time_12hr(current_slot['start'])} to {format_time_12hr(current_slot['end'])})

⚙️ Settings:
• Interval: {state['interval_min']}m
• Work: {state['work_min']}m  
• Rest: {state['rest_min']}m
"""
    
    if message_data:
        if message_data.get("file_id"):
            preview = f"📷 Media ({message_data.get('file_type', 'file')})"
            if message_data.get("text"):
                preview += f" - {message_data['text'][:30]}..."
        else:
            preview = message_data.get('text', '')[:50] + "..." if len(message_data.get('text', '')) > 50 else message_data.get('text', 'No text')
        status_text += f"🔹 Message: {preview}"
    else:
        status_text += "🔹 Message: ❌ Not set"
        
    bot.reply_to(message, status_text)

@bot.message_handler(commands=['test'])
def test_handler(message):
    if not is_admin_or_sudo(message.from_user.id):
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ Usage: /test <chat_identifier>\n\nExamples:\n/test @username\n/test -100123456789\n/test https://t.me/joinchat/...")
        return
    
    chat_identifier = parts[1]
    
    is_valid, id_type = validate_chat_identifier(chat_identifier)
    if not is_valid:
        bot.reply_to(message, f"❌ Invalid chat identifier: {id_type}")
        return
    
    user_manager = get_user_manager_for_admin(message.from_user.id)
    
    if user_manager.is_connected:
        success, result = user_manager.send_message_direct(chat_identifier, "🧪 This is a TEST message sent via Telethon from your User Account!")
        if success:
            bot.reply_to(message, f"✅ **Test SUCCESSFUL!**\n\nAccount: {user_manager.user_name}\nType: {id_type}\nResult: {result}")
        else:
            bot.reply_to(message, f"❌ **Test FAILED!**\n\nError: {result}")
    else:
        bot.reply_to(message, f"❌ **User Account Not Connected!**\n\nStatus: {user_manager.user_name}")

@bot.message_handler(commands=['autoset'])
def autoset_handler(message):
    if not is_admin_or_sudo(message.from_user.id):
        return
    
    state = get_admin_state(message.from_user.id)
    if not state["bot_started"]:
        bot.reply_to(message, "❌ Bot is not started. Use /start first")
        return
    
    user_manager = get_user_manager_for_admin(message.from_user.id)
    if not user_manager.is_connected:
        bot.reply_to(message, f"❌ User account not connected!\n\nUse /setsession first.")
        return
        
    if not state["scheduled_message"]:
        bot.reply_to(message, "❌ No message set. Use /setmsg first")
        return
        
    entities = state["target_entities"]
    if not entities:
        bot.reply_to(message, "❌ No entities added. Use /addentity first")
        return
    
    current_slot = get_current_time_slot()
    current_time = get_current_time_formatted()
    
    state["autoschedule_enabled"] = True
    state["interval_min"] = 10
    save_admin_state(message.from_user.id, state)
    
    if not any(thread.name == "autoscheduler" for thread in threading.enumerate()):
        scheduler_thread = threading.Thread(target=autoscheduler_loop, name="autoscheduler")
        scheduler_thread.daemon = True
        scheduler_thread.start()
        print("🚀 Auto scheduler thread started")
    
    if current_slot["type"] == "work":
        state["running"] = True
        save_admin_state(message.from_user.id, state)
        response = f"""✅ **AUTO SCHEDULE ACTIVATED!**

🕒 Indian Time: {current_time}
🚀 **Started Immediately - Current Slot: 🟢 WORK**
⏰ Work Period: {format_time_12hr(current_slot['start'])} to {format_time_12hr(current_slot['end'])}
🔹 Interval: 10 minutes
🔹 Auto-switching: Enabled
🔹 Messages: ✅ SENDING NOW"""

        if entities and state["scheduled_message"]:
            test_entity = entities[0]
            message_text = state["scheduled_message"].get("text", "Hello 👋")
            test_success, test_result = user_manager.send_message_direct(
                test_entity['identifier'], 
                message_text
            )
            if test_success:
                response += f"\n🔹 Test Message: ✅ Sent to {test_entity['resolved_name']}"
            else:
                response += f"\n🔹 Test Message: ❌ Failed - {test_result}"
                
    else:
        state["running"] = False
        save_admin_state(message.from_user.id, state)
        response = f"""✅ **AUTO SCHEDULE ACTIVATED!**

🕒 Indian Time: {current_time}
💤 **Current Slot: 🔴 REST**
⏰ Rest Period: {format_time_12hr(current_slot['start'])} to {format_time_12hr(current_slot['end'])}
🔹 Next Work: {format_time_12hr(current_slot['end'])}
🔹 Auto-switching: Enabled"""
    
    bot.reply_to(message, response)

@bot.message_handler(commands=['autowork'])
def autowork_handler(message):
    if not is_admin_or_sudo(message.from_user.id):
        return
    
    state = get_admin_state(message.from_user.id)
    if not state.get("autoschedule_enabled"):
        bot.reply_to(message, "❌ Auto schedule is not active. Use /autoset first")
        return
    
    current_slot, next_work, next_rest = get_next_slots()
    current_time = get_current_time_formatted()
    
    now = get_indian_time()
    current_end_time = now.replace(
        hour=int(current_slot["end"].split(":")[0]),
        minute=int(current_slot["end"].split(":")[1]),
        second=0, microsecond=0
    )
    if current_end_time < now:
        current_end_time += timedelta(days=1)
    
    time_until_current_end = current_end_time - now
    hours_left = time_until_current_end.seconds // 3600
    minutes_left = (time_until_current_end.seconds % 3600) // 60
    
    response = f"""📊 **AUTO SCHEDULE STATUS**

🕒 Indian Time: {current_time}
🎯 Current Slot: {'🟢 WORK' if current_slot['type'] == 'work' else '🔴 REST'}
⏰ Current Period: {format_time_12hr(current_slot['start'])} - {format_time_12hr(current_slot['end'])}
⏳ Time Left: {hours_left}h {minutes_left}m
🔹 Scheduler Status: {'🟢 RUNNING' if state['running'] else '🔴 STOPPED'}

"""
    
    if current_slot["type"] == "work":
        response += f"""🔹 Status: 🟢 SENDING MESSAGES
🔹 Interval: 10 minutes
🔹 Next Rest: {format_time_12hr(next_rest['start'])} - {format_time_12hr(next_rest['end'])}"""
    else:
        response += f"""🔹 Status: 🔴 RESTING - NO MESSAGES
🔹 Next Work: {format_time_12hr(next_work['start'])} - {format_time_12hr(next_work['end'])}"""
    
    bot.reply_to(message, response)

@bot.message_handler(commands=['autostop'])
def autostop_handler(message):
    if not is_admin_or_sudo(message.from_user.id):
        return
    
    state = get_admin_state(message.from_user.id)
    state["autoschedule_enabled"] = False
    state["running"] = False
    save_admin_state(message.from_user.id, state)
    
    bot.reply_to(message, "⏹️ **Auto Schedule Stopped!**\n\nManual control enabled.")

@bot.message_handler(commands=['start_scheduler'])
def start_scheduler_handler(message):
    if not is_admin_or_sudo(message.from_user.id):
        return
    
    state = get_admin_state(message.from_user.id)
    if not state["bot_started"]:
        bot.reply_to(message, "❌ Bot is not started. Use /start first")
        return
    
    user_manager = get_user_manager_for_admin(message.from_user.id)
    if not user_manager.is_connected:
        bot.reply_to(message, f"❌ User account not connected!\n\nUse /setsession first.")
        return
    
    if state["running"]:
        bot.reply_to(message, "ℹ️ Scheduler is already running")
        return
        
    if not state["scheduled_message"]:
        bot.reply_to(message, "❌ No message set. Use /setmsg first")
        return
        
    entities = state["target_entities"]
    if not entities:
        bot.reply_to(message, "❌ No entities added. Use /addentity first")
        return
    
    state["running"] = True
    save_admin_state(message.from_user.id, state)
    
    scheduler_thread = threading.Thread(target=scheduler_loop, args=(message.from_user.id,))
    scheduler_thread.daemon = True
    scheduler_thread.start()
    
    entities_count = len(entities)
    
    bot.reply_to(message, f"""🚀 **SCHEDULER STARTED!**

👤 From: {user_manager.user_name}
🎯 Entities: {entities_count}
🕐 Interval: {state['interval_min']}m
💼 Work: {state['work_min']}m
😴 Rest: {state['rest_min']}m""")

@bot.message_handler(commands=['stop_scheduler'])
def stop_scheduler_handler(message):
    if not is_admin_or_sudo(message.from_user.id):
        return
    
    state = get_admin_state(message.from_user.id)
    if not state["bot_started"]:
        bot.reply_to(message, "❌ Bot is not started")
        return
    
    if not state["running"]:
        bot.reply_to(message, "ℹ️ Scheduler is not running")
        return
        
    state["running"] = False
    save_admin_state(message.from_user.id, state)
    
    bot.reply_to(message, "⏹️ **Scheduler Stopped!**")

# ==================== SCHEDULER SYSTEM ====================
def scheduler_loop(admin_id):
    print(f"⏰ SCHEDULER: Started for admin {admin_id}")
    
    try:
        while True:
            state = get_admin_state(admin_id)
            if not state["running"]:
                break
                
            work_end = time.time() + (state["work_min"] * 60)
            print(f"⏰ SCHEDULER: Work window started for {state['work_min']}m")
            
            last_message_time = 0
            
            while state["running"] and time.time() < work_end:
                current_time = time.time()
                
                # Check if enough time has passed since last message
                if current_time - last_message_time >= state["interval_min"] * 60:
                    messages_sent = send_messages(admin_id)
                    if messages_sent > 0:
                        print(f"⏰ SCHEDULER: Sent {messages_sent} messages")
                        last_message_time = current_time
                
                # Small sleep to prevent high CPU usage
                time.sleep(10)
                state = get_admin_state(admin_id)

            if not state["running"]:
                break
                
            rest = state["rest_min"] * 60
            print(f"⏰ SCHEDULER: Resting for {state['rest_min']}m")
            
            rest_start = time.time()
            while state["running"] and (time.time() - rest_start) < rest:
                time.sleep(30)
                state = get_admin_state(admin_id)
                
    except Exception as e:
        print(f"⏰ SCHEDULER ERROR: {e}")
        notify_admins(f"❌ **Scheduler Error**\n{str(e)}")
    finally:
        state = get_admin_state(admin_id)
        state["running"] = False
        save_admin_state(admin_id, state)
        print("⏰ SCHEDULER: Stopped")

def autoscheduler_loop():
    """Auto scheduler that follows the fixed timetable"""
    print("🤖 AUTOSCHEDULER: Started with fixed timetable")
    
    try:
        while True:
            admin_states = load_admin_states()
            any_autoschedule_active = False
            
            for admin_id_str, state in admin_states.items():
                if state.get("autoschedule_enabled", False):
                    any_autoschedule_active = True
                    
                    current_slot = get_current_time_slot()
                    
                    if current_slot["type"] == "work" and not state["running"]:
                        state["running"] = True
                        state["interval_min"] = 10
                        save_admin_state(int(admin_id_str), state)
                        print(f"🤖 AUTOSCHEDULER: Work started for admin {admin_id_str}")
                        
                    elif current_slot["type"] == "rest" and state["running"]:
                        state["running"] = False
                        save_admin_state(int(admin_id_str), state)
                        print(f"🤖 AUTOSCHEDULER: Rest started for admin {admin_id_str}")
                    
                    # For auto schedule, send messages with proper interval
                    if state["running"]:
                        current_time = time.time()
                        last_message_time = state.get("last_message_time", 0)
                        
                        # Check if 10 minutes have passed since last message
                        if current_time - last_message_time >= 10 * 60:  # 10 minutes in seconds
                            messages_sent = send_messages(int(admin_id_str))
                            if messages_sent > 0:
                                print(f"🤖 AUTOSCHEDULER: Sent {messages_sent} messages for admin {admin_id_str}")
                                # Update last message time
                                state["last_message_time"] = current_time
                                save_admin_state(int(admin_id_str), state)
            
            if not any_autoschedule_active:
                print("🤖 AUTOSCHEDULER: No active autoschedule, stopping...")
                break
            
            # Check every 30 seconds instead of every minute for better responsiveness
            time.sleep(30)
            
    except Exception as e:
        print(f"🤖 AUTOSCHEDULER ERROR: {e}")
        notify_admins(f"❌ **Auto Scheduler Error**\n{str(e)}")
    finally:
        admin_states = load_admin_states()
        for admin_id_str in admin_states:
            admin_states[admin_id_str]["running"] = False
            admin_states[admin_id_str]["autoschedule_enabled"] = False
        save_admin_states(admin_states)
        print("🤖 AUTOSCHEDULER: Stopped")

def send_messages(admin_id):
    state = get_admin_state(admin_id)
    entities = state["target_entities"]
    message_data = state["scheduled_message"]
    
    if not entities or not message_data or not state["running"]:
        return 0
    
    success_count = 0
    
    user_manager = get_user_manager_for_admin(admin_id)
    
    for entity_info in entities:
        try:
            if message_data.get("file_id"):
                file_path = download_media(message_data["file_id"], f"scheduled_{message_data['file_type']}")
                if file_path:
                    success, result = user_manager.send_media_direct(entity_info['identifier'], file_path, message_data.get("text", ""))
                    if success:
                        success_count += 1
                        print(f"✅ Sent media to {entity_info['resolved_name']}")
                    else:
                        print(f"❌ Failed to send media to {entity_info['resolved_name']}: {result}")
                    
                    try:
                        os.remove(file_path)
                    except:
                        pass
            else:
                success, result = user_manager.send_message_direct(entity_info['identifier'], message_data.get("text", ""))
                if success:
                    success_count += 1
                    print(f"✅ Sent text to {entity_info['resolved_name']}")
                else:
                    print(f"❌ Failed to send text to {entity_info['resolved_name']}: {result}")
            
            # Small delay between sending to different entities
            time.sleep(2)
            
        except Exception as e:
            print(f"⏰ SEND ERROR to {entity_info['resolved_name']}: {e}")
    
    return success_count

# ==================== MAIN EXECUTION ====================
if __name__ == "__main__":
    print("=" * 60)
    print("🤖 USER ACCOUNT SCHEDULER BOT - INDIAN TIME")
    print("=" * 60)
    
    os.makedirs("downloads", exist_ok=True)
    
    admin_states = load_admin_states()
    for admin_id in ADMIN_IDS:
        if str(admin_id) not in admin_states:
            admin_states[str(admin_id)] = DEFAULT_STATE.copy()
    save_admin_states(admin_states)
    
    print("🔧 Initialization complete!")
    print("🔗 Starting bot polling...")
    
    notify_admins("🤖 **User Account Bot Started!**\n\nSend /start to begin.")
    
    print("✅ BOT IS NOW RUNNING!")
    
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"❌ Bot polling error: {e}")