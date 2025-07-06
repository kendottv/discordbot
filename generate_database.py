import os
import json
import sqlite3
from datetime import datetime

# 資料庫檔案路徑
DB_FILE = "bot_data.db"

# 確保 data 和 config 資料夾存在
os.makedirs("data", exist_ok=True)
os.makedirs("config", exist_ok=True)

# 連線到 SQLite 資料庫
db = sqlite3.connect(DB_FILE)
cursor = db.cursor()

# 創建表格
def create_tables():
    # Game 表格（預留，無對應 JSON）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS game_scores (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            score INTEGER DEFAULT 0
        )
    """)

    # Vote 表格（預留，無對應 JSON）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS polls (
            id TEXT PRIMARY KEY,
            question TEXT,
            options TEXT,
            voters TEXT,
            creator TEXT,
            creator_id INTEGER,
            active INTEGER DEFAULT 1
        )
    """)

    # Welcome 表格
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS welcome_config (
            guild_id INTEGER PRIMARY KEY,
            welcome_channel INTEGER,
            welcome_message TEXT,
            auto_role INTEGER,
            dm_welcome INTEGER DEFAULT 0,
            dm_message TEXT
        )
    """)

    # Level 表格
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS level_data (
            user_id INTEGER PRIMARY KEY,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 0,
            total_messages INTEGER DEFAULT 0,
            last_message TEXT
        )
    """)

    # Level Config 表格
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS level_config (
            guild_id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 0,
            xp_per_message TEXT,
            cooldown_seconds INTEGER DEFAULT 60,
            level_up_channel INTEGER,
            level_up_message TEXT,
            level_roles TEXT,
            blacklist_channels TEXT
        )
    """)

    # Weather 表格
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weather_channels (
            guild_id INTEGER PRIMARY KEY,
            channel_id INTEGER,
            cities TEXT
        )
    """)

    # YTNotification 表格
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS yt_config (
            guild_id INTEGER PRIMARY KEY,
            discord_channel_id INTEGER,
            channel_ids TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS yt_last_videos (
            channel_id TEXT PRIMARY KEY,
            video_id TEXT
        )
    """)

    # Twitch Config 表格（更新：添加 default_message）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS twitch_config (
            guild_id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 0,
            client_id TEXT,
            client_secret TEXT,
            notification_channel INTEGER,
            check_interval INTEGER DEFAULT 60,
            default_message TEXT,
            mention_everyone INTEGER DEFAULT 0,
            mention_role INTEGER
        )
    """)

    # Twitch Streamers 表格
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS twitch_streamers (
            username TEXT PRIMARY KEY,
            guild_id INTEGER,
            discord_role INTEGER,
            custom_message TEXT,
            is_live INTEGER DEFAULT 0,
            stream_id TEXT,
            last_checked TEXT
        )
    """)

# 遷移 JSON 資料到 SQLite
def migrate_data():
    # Welcome 資料
    welcome_file = "config/welcome_config.json"
    if os.path.exists(welcome_file):
        try:
            with open(welcome_file, "r", encoding="utf-8") as f:
                welcome_config = json.load(f)
            if isinstance(welcome_config, dict):
                cursor.execute("""
                    INSERT OR REPLACE INTO welcome_config (guild_id, welcome_channel, welcome_message, auto_role, dm_welcome, dm_message)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (1130523145313456268, welcome_config.get("welcome_channel"), welcome_config.get("welcome_message"),
                      welcome_config.get("auto_role"), 1 if welcome_config.get("dm_welcome") else 0,
                      welcome_config.get("dm_message")))
            else:
                print(f"⚠️ {welcome_file} 格式不符，預期為字典")
        except json.JSONDecodeError as e:
            print(f"⚠️ {welcome_file} 解析錯誤: {e}")

    # Level Data 資料
    level_data_file = "data/level_data.json"
    if os.path.exists(level_data_file):
        try:
            with open(level_data_file, "r", encoding="utf-8") as f:
                level_data = json.load(f)
            if isinstance(level_data, dict):
                for user_id, data in level_data.items():
                    cursor.execute("""
                        INSERT OR REPLACE INTO level_data (user_id, xp, level, total_messages, last_message)
                        VALUES (?, ?, ?, ?, ?)
                    """, (int(user_id), data.get("xp", 0), data.get("level", 0),
                          data.get("total_messages", 0), data.get("last_message")))
            else:
                print(f"⚠️ {level_data_file} 格式不符，預期為字典")
        except json.JSONDecodeError as e:
            print(f"⚠️ {level_data_file} 解析錯誤: {e}")

    # Level Config 資料
    level_config_file = "config/level_config.json"
    if os.path.exists(level_config_file):
        try:
            with open(level_config_file, "r", encoding="utf-8") as f:
                level_config = json.load(f)
            if isinstance(level_config, dict):
                cursor.execute("""
                    INSERT OR REPLACE INTO level_config (guild_id, enabled, xp_per_message, cooldown_seconds, level_up_channel, level_up_message, level_roles, blacklist_channels)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (1130523145313456268, 1 if level_config.get("enabled") else 0,
                      json.dumps(level_config.get("xp_per_message", [15, 25])),
                      level_config.get("cooldown_seconds", 60), level_config.get("level_up_channel"),
                      level_config.get("level_up_message"), json.dumps(level_config.get("level_roles", {})),
                      json.dumps(level_config.get("blacklist_channels", []))))
            else:
                print(f"⚠️ {level_config_file} 格式不符，預期為字典")
        except json.JSONDecodeError as e:
            print(f"⚠️ {level_config_file} 解析錯誤: {e}")

    # Weather 資料
    weather_file = "data/weather_data.json"
    if os.path.exists(weather_file):
        try:
            with open(weather_file, "r", encoding="utf-8") as f:
                weather_data = json.load(f)
            if isinstance(weather_data, dict):
                for guild_id, data in weather_data.items():
                    cursor.execute("""
                        INSERT OR REPLACE INTO weather_channels (guild_id, channel_id, cities)
                        VALUES (?, ?, ?)
                    """, (int(guild_id), data.get("channel_id"), json.dumps([data.get("city", "Taipei")])))
            else:
                print(f"⚠️ {weather_file} 格式不符，預期為字典")
        except json.JSONDecodeError as e:
            print(f"⚠️ {weather_file} 解析錯誤: {e}")

    # YTNotification 資料
    yt_file = "data/yt_data.json"
    if os.path.exists(yt_file):
        try:
            with open(yt_file, "r", encoding="utf-8") as f:
                yt_data = json.load(f)
            if isinstance(yt_data, dict):
                for guild_id, data in yt_data.items():
                    cursor.execute("""
                        INSERT OR REPLACE INTO yt_config (guild_id, discord_channel_id, channel_ids)
                        VALUES (?, ?, ?)
                    """, (int(guild_id), data.get("discord_channel_id"), json.dumps(data.get("channel_ids", []))))
            else:
                print(f"⚠️ {yt_file} 格式不符，預期為字典")
        except json.JSONDecodeError as e:
            print(f"⚠️ {yt_file} 解析錯誤: {e}")

    # Twitch Config 資料
    twitch_config_file = "config/twitch_config.json"
    if os.path.exists(twitch_config_file):
        try:
            with open(twitch_config_file, "r", encoding="utf-8") as f:
                twitch_config = json.load(f)
            if isinstance(twitch_config, dict):
                cursor.execute("""
                    INSERT OR REPLACE INTO twitch_config (guild_id, enabled, client_id, client_secret, notification_channel, check_interval, default_message, mention_everyone, mention_role)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (1130523145313456268, 1 if twitch_config.get("enabled") else 0, twitch_config.get("client_id"),
                      twitch_config.get("client_secret"), twitch_config.get("notification_channel"),
                      twitch_config.get("check_interval", 60), twitch_config.get("default_message"),
                      1 if twitch_config.get("mention_everyone") else 0, twitch_config.get("mention_role")))
            else:
                print(f"⚠️ {twitch_config_file} 格式不符，預期為字典")
        except json.JSONDecodeError as e:
            print(f"⚠️ {twitch_config_file} 解析錯誤: {e}")

    # Twitch Streamers 資料
    twitch_data_file = "data/twitch_data.json"
    if os.path.exists(twitch_data_file):
        try:
            with open(twitch_data_file, "r", encoding="utf-8") as f:
                twitch_data = json.load(f)
            if isinstance(twitch_data, dict):
                for username, data in twitch_data.items():
                    if username not in ["enabled", "client_id", "client_secret", "notification_channel", "check_interval", "default_message", "mention_everyone", "mention_role"]:
                        cursor.execute("""
                            INSERT OR REPLACE INTO twitch_streamers (username, guild_id, discord_role, custom_message, is_live, stream_id, last_checked)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (username, 1130523145313456268, None, None,
                              1 if data.get("is_live") else 0, data.get("stream_id"), data.get("last_checked")))
            else:
                print(f"⚠️ {twitch_data_file} 格式不符，預期為字典")
        except json.JSONDecodeError as e:
            print(f"⚠️ {twitch_data_file} 解析錯誤: {e}")

# 執行創建與遷移
try:
    create_tables()
    migrate_data()
    db.commit()
    print(f"✅ 資料庫 {DB_FILE} 創建並遷移成功！")
except Exception as e:
    print(f"❌ 創建或遷移資料庫時發生錯誤: {e}")
    db.rollback()

# 關閉資料庫連線
db.close()