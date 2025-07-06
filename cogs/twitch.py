import discord
from discord.ext import commands, tasks
import json
import os
import sqlite3
import aiohttp
import asyncio
from datetime import datetime, timedelta
import logging

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Twitch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_file = "bot_data.db"
        self.guild_id = 1130523145313456268  # 你的伺服器 ID
        self.config = self.load_config()
        self.twitch_token = None
        self.token_expires_at = None
        self.headers = {}
        self.stream_data = {}
        
        # 確保所有追蹤的實況主在資料庫中有記錄
        self.ensure_streamers_in_db()
        
        # 啟動定時檢查
        if self.config.get("enabled", False):
            self.check_streams.start()

    def get_db_connection(self):
        """取得資料庫連線"""
        return sqlite3.connect(self.db_file)

    def load_config(self):
        """從資料庫載入 Twitch 設定"""
        try:
            with self.get_db_connection() as db:
                cursor = db.cursor()
                cursor.execute("""
                    SELECT enabled, client_id, client_secret, notification_channel, 
                           check_interval, default_message, mention_everyone, mention_role
                    FROM twitch_config WHERE guild_id = ?
                """, (self.guild_id,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        "enabled": bool(result[0]),
                        "client_id": result[1] or "",
                        "client_secret": result[2] or "",
                        "notification_channel": result[3],
                        "check_interval": result[4] or 60,
                        "default_message": result[5] or "🔴 **{streamer}** 正在直播！\n\n**{title}**\n分類：{category}\n觀看人數：{viewers}\n\n🎮 立即觀看：https://twitch.tv/{username}",
                        "mention_everyone": bool(result[6]),
                        "mention_role": result[7]
                    }
                else:
                    # 如果沒有設定，創建預設值
                    default_config = {
                        "enabled": False,
                        "client_id": "",
                        "client_secret": "",
                        "notification_channel": None,
                        "check_interval": 60,
                        "default_message": "🔴 **{streamer}** 正在直播！\n\n**{title}**\n分類：{category}\n觀看人數：{viewers}\n\n🎮 立即觀看：https://twitch.tv/{username}",
                        "mention_everyone": False,
                        "mention_role": None
                    }
                    self.save_config(default_config)
                    return default_config
        except Exception as e:
            logger.error(f"載入設定時發生錯誤: {e}")
            return {
                "enabled": False,
                "client_id": "",
                "client_secret": "",
                "notification_channel": None,
                "check_interval": 60,
                "default_message": "🔴 **{streamer}** 正在直播！\n\n**{title}**\n分類：{category}\n觀看人數：{viewers}\n\n🎮 立即觀看：https://twitch.tv/{username}",
                "mention_everyone": False,
                "mention_role": None
            }

    def save_config(self, config=None):
        """儲存 Twitch 設定到資料庫"""
        if config is None:
            config = self.config
        
        try:
            with self.get_db_connection() as db:
                cursor = db.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO twitch_config 
                    (guild_id, enabled, client_id, client_secret, notification_channel, 
                     check_interval, default_message, mention_everyone, mention_role)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.guild_id,
                    1 if config.get("enabled") else 0,
                    config.get("client_id"),
                    config.get("client_secret"),
                    config.get("notification_channel"),
                    config.get("check_interval", 60),
                    config.get("default_message"),
                    1 if config.get("mention_everyone") else 0,
                    config.get("mention_role")
                ))
                db.commit()
        except Exception as e:
            logger.error(f"儲存設定時發生錯誤: {e}")

    def get_streamers(self):
        """從資料庫取得所有實況主"""
        try:
            with self.get_db_connection() as db:
                cursor = db.cursor()
                cursor.execute("""
                    SELECT username, discord_role, custom_message, is_live, stream_id, last_checked
                    FROM twitch_streamers WHERE guild_id = ?
                """, (self.guild_id,))
                
                streamers = {}
                for row in cursor.fetchall():
                    streamers[row[0]] = {
                        "discord_role": row[1],
                        "custom_message": row[2],
                        "is_live": bool(row[3]),
                        "stream_id": row[4],
                        "last_checked": row[5]
                    }
                return streamers
        except Exception as e:
            logger.error(f"取得實況主列表時發生錯誤: {e}")
            return {}

    def get_streamer_data(self, username):
        """取得特定實況主的資料"""
        try:
            with self.get_db_connection() as db:
                cursor = db.cursor()
                cursor.execute("""
                    SELECT discord_role, custom_message, is_live, stream_id, last_checked
                    FROM twitch_streamers WHERE username = ? AND guild_id = ?
                """, (username, self.guild_id))
                
                result = cursor.fetchone()
                if result:
                    return {
                        "discord_role": result[0],
                        "custom_message": result[1],
                        "is_live": bool(result[2]),
                        "stream_id": result[3],
                        "last_checked": result[4]
                    }
                return None
        except Exception as e:
            logger.error(f"取得實況主 {username} 資料時發生錯誤: {e}")
            return None

    def update_streamer_data(self, username, is_live=None, stream_id=None, last_checked=None):
        """更新實況主資料"""
        try:
            with self.get_db_connection() as db:
                cursor = db.cursor()
                
                # 先檢查是否存在
                cursor.execute("""
                    SELECT username FROM twitch_streamers WHERE username = ? AND guild_id = ?
                """, (username, self.guild_id))
                
                if cursor.fetchone():
                    # 更新現有記錄
                    updates = []
                    values = []
                    
                    if is_live is not None:
                        updates.append("is_live = ?")
                        values.append(1 if is_live else 0)
                    
                    if stream_id is not None:
                        updates.append("stream_id = ?")
                        values.append(stream_id)
                    
                    if last_checked is not None:
                        updates.append("last_checked = ?")
                        values.append(last_checked)
                    
                    if updates:
                        values.extend([username, self.guild_id])
                        cursor.execute(f"""
                            UPDATE twitch_streamers 
                            SET {', '.join(updates)}
                            WHERE username = ? AND guild_id = ?
                        """, values)
                else:
                    # 創建新記錄
                    cursor.execute("""
                        INSERT INTO twitch_streamers 
                        (username, guild_id, discord_role, custom_message, is_live, stream_id, last_checked)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        username, self.guild_id, None, None,
                        1 if is_live else 0, stream_id, last_checked
                    ))
                
                db.commit()
        except Exception as e:
            logger.error(f"更新實況主 {username} 資料時發生錯誤: {e}")

    def ensure_streamers_in_db(self):
        """確保所有追蹤的實況主在資料庫中有記錄"""
        streamers = self.get_streamers()
        for username in streamers.keys():
            if not self.get_streamer_data(username):
                self.update_streamer_data(username, False, None, datetime.now().isoformat())

    def is_token_valid(self):
        """檢查 Token 是否有效"""
        if not self.twitch_token or not self.token_expires_at:
            return False
        return datetime.now() < self.token_expires_at

    async def get_twitch_token(self):
        """獲取 Twitch API Token"""
        if not self.config.get("client_id") or not self.config.get("client_secret"):
            logger.error("Client ID 或 Client Secret 未設定")
            return False
        
        if self.is_token_valid():
            return True
        
        url = "https://id.twitch.tv/oauth2/token"
        data = {
            "client_id": self.config["client_id"],
            "client_secret": self.config["client_secret"],
            "grant_type": "client_credentials"
        }
        
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, data=data) as response:
                    response_text = await response.text()
                    logger.info(f"Token 請求狀態碼: {response.status}")
                    logger.info(f"Token 請求回應: {response_text}")
                    
                    if response.status == 200:
                        response_data = await response.json()
                        self.twitch_token = response_data.get("access_token")
                        expires_in = response_data.get("expires_in", 3600)
                        self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 600)
                        self.headers = {
                            "Client-ID": self.config["client_id"],
                            "Authorization": f"Bearer {self.twitch_token}"
                        }
                        logger.info("✅ 成功獲取 Twitch Token")
                        return True
                    else:
                        logger.error(f"❌ 無法獲取 Twitch Token: {response.status} - {response_text}")
                        return False
        except asyncio.TimeoutError:
            logger.error("❌ 獲取 Twitch Token 超時")
            return False
        except Exception as e:
            logger.error(f"❌ 獲取 Twitch Token 時發生錯誤: {e}")
            return False

    async def make_twitch_request(self, url, retries=3):
        """統一的 Twitch API 請求方法，包含重試機制"""
        for attempt in range(retries):
            if not await self.get_twitch_token():
                logger.error("無法獲取有效的 Twitch Token")
                return None
            
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, headers=self.headers) as response:
                        response_text = await response.text()
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 401:
                            logger.warning("Token 無效，嘗試重新獲取")
                            self.twitch_token = None
                            self.token_expires_at = None
                            if attempt < retries - 1:
                                await asyncio.sleep(1)
                                continue
                        else:
                            logger.error(f"API 請求失敗: {response.status} - {response_text}")
                            return None
            except asyncio.TimeoutError:
                logger.error(f"API 請求超時 (第 {attempt + 1} 次嘗試)")
                if attempt < retries - 1:
                    await asyncio.sleep(2)
                    continue
            except Exception as e:
                logger.error(f"API 請求錯誤: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(2)
                    continue
        
        return None

    async def get_user_id(self, username):
        """根據用戶名獲取 Twitch 用戶 ID"""
        url = f"https://api.twitch.tv/helix/users?login={username}"
        data = await self.make_twitch_request(url)
        return data.get("data", [{}])[0].get("id") if data else None

    async def get_stream_info(self, user_id):
        """獲取直播資訊"""
        url = f"https://api.twitch.tv/helix/streams?user_id={user_id}"
        data = await self.make_twitch_request(url)
        return data.get("data", [{}])[0] if data else None

    async def get_user_info(self, user_id):
        """獲取用戶詳細資訊"""
        url = f"https://api.twitch.tv/helix/users?id={user_id}"
        data = await self.make_twitch_request(url)
        return data.get("data", [{}])[0] if data else None

    @tasks.loop(seconds=60)
    async def check_streams(self):
        """定時檢查直播狀態"""
        if not self.config.get("enabled", False):
            return
        
        streamers = self.get_streamers()
        if not streamers:
            return
        
        self.check_streams.change_interval(seconds=self.config.get("check_interval", 60))
        logger.info(f"開始檢查 {len(streamers)} 位實況主的直播狀態")
        
        for username, settings in streamers.items():
            try:
                user_id = await self.get_user_id(username)
                if not user_id:
                    logger.warning(f"找不到用戶 {username} 的 ID")
                    self.update_streamer_data(username, False, None, datetime.now().isoformat())
                    continue
                
                stream_info = await self.get_stream_info(user_id)
                is_live = bool(stream_info)
                
                # 獲取之前的狀態
                was_live = settings.get("is_live", False)
                previous_stream_id = settings.get("stream_id")
                
                # 獲取當前直播的 ID
                current_stream_id = stream_info.get("id") if stream_info else None
                
                # 判斷是否需要發送通知
                should_notify = False
                if is_live:
                    if not was_live:
                        # 從離線變為直播
                        logger.info(f"🔴 {username} 開始直播 (Stream ID: {current_stream_id})")
                        should_notify = True
                    elif was_live and current_stream_id != previous_stream_id:
                        # 直播 ID 改變，表示開始了新的直播
                        logger.info(f"🔴 {username} 開始新的直播 (Stream ID: {current_stream_id})")
                        should_notify = True
                    elif was_live and current_stream_id == previous_stream_id:
                        # 持續直播中
                        logger.debug(f"🔴 {username} 持續直播中 (Stream ID: {current_stream_id})")
                else:
                    if was_live:
                        logger.info(f"⚫ {username} 結束直播")
                
                # 更新資料庫
                self.update_streamer_data(username, is_live, current_stream_id, datetime.now().isoformat())
                
                # 發送通知
                if should_notify:
                    await self.send_live_notification(username, stream_info, settings)
                
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"檢查 {username} 直播狀態時發生錯誤: {e}")
                self.update_streamer_data(username, False, None, datetime.now().isoformat())

    async def send_live_notification(self, username, stream_info, settings):
        """發送直播通知"""
        if not self.config.get("notification_channel"):
            logger.warning("未設定通知頻道")
            return
        
        channel = self.bot.get_channel(self.config["notification_channel"])
        if not channel:
            logger.error(f"找不到通知頻道: {self.config['notification_channel']}")
            return
        
        user_info = await self.get_user_info(stream_info.get("user_id")) if stream_info else None
        if not user_info:
            logger.warning(f"無法獲取 {username} 的用戶資訊")
            return
        
        message_template = settings.get("custom_message", self.config.get("default_message"))
        if message_template is None:
            logger.warning(f"訊息模板無效，使用預設值: {username}")
            message_template = "🔴 **{streamer}** 正在直播！"
        
        try:
            message = message_template.format(
                streamer=stream_info.get("user_name", username),
                username=stream_info.get("user_login", username),
                title=stream_info.get("title", "無標題"),
                category=stream_info.get("game_name", "未設定"),
                viewers=stream_info.get("viewer_count", 0),
                url=f"https://twitch.tv/{stream_info.get('user_login', username)}"
            )
        except KeyError as e:
            logger.error(f"格式化訊息時發生錯誤: 缺少鍵 {e}")
            message = f"🔴 **{username}** 正在直播！（資料不完整）"
        
        embed = discord.Embed(
            title=f"🔴 {stream_info.get('user_name', username)} 正在直播！",
            description=stream_info.get("title", "無標題"),
            color=discord.Color.purple(),
            url=f"https://twitch.tv/{stream_info.get('user_login', username)}"
        )
        
        if stream_info and stream_info.get("thumbnail_url"):
            thumbnail_url = stream_info["thumbnail_url"].replace("{width}", "1920").replace("{height}", "1080")
            embed.set_image(url=thumbnail_url)
        
        if user_info and user_info.get("profile_image_url"):
            embed.set_author(
                name=stream_info.get("user_name", username),
                icon_url=user_info["profile_image_url"],
                url=f"https://twitch.tv/{stream_info.get('user_login', username)}"
            )
        
        embed.add_field(name="🎮 分類", value=stream_info.get("game_name", "未設定"), inline=True)
        embed.add_field(name="👥 觀看人數", value=f"{stream_info.get('viewer_count', 0):,}", inline=True)
        
        try:
            started_at = datetime.fromisoformat(stream_info.get("started_at", datetime.now().isoformat()).replace("Z", "+00:00"))
            timestamp = int(started_at.timestamp())
            embed.add_field(name="🕐 開始時間", value=f"<t:{timestamp}:R>", inline=True)
        except (ValueError, TypeError) as e:
            logger.error(f"處理開始時間時發生錯誤: {e}")
            embed.add_field(name="🕐 開始時間", value="剛剛", inline=True)
        
        embed.set_footer(text="Twitch 直播通知")
        
        mentions = []
        if self.config.get("mention_everyone", False):
            mentions.append("@everyone")
        elif self.config.get("mention_role"):
            role = channel.guild.get_role(self.config["mention_role"])
            if role:
                mentions.append(role.mention)
        
        if settings.get("discord_role"):
            role = channel.guild.get_role(settings["discord_role"])
            if role:
                mentions.append(role.mention)
        
        mention_text = " ".join(mentions) if mentions else ""
        
        try:
            await channel.send(content=mention_text, embed=embed)
            logger.info(f"✅ 已發送 {username} 的直播通知")
        except discord.Forbidden:
            logger.error(f"無權發送訊息或提及 @everyone，請檢查 bot 權限")
        except Exception as e:
            logger.error(f"發送直播通知時發生錯誤: {e}")

    @check_streams.before_loop
    async def before_check_streams(self):
        """等待機器人準備就緒"""
        await self.bot.wait_until_ready()

    @check_streams.error
    async def check_streams_error(self, error):
        """處理定時任務錯誤"""
        logger.error(f"定時檢查任務發生錯誤: {error}")

    @commands.group(name="twitch", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def twitch(self, ctx):
        """Twitch 直播通知系統"""
        embed = discord.Embed(title="📺 Twitch 直播通知系統", color=discord.Color.purple())
        
        channel = ctx.guild.get_channel(self.config.get("notification_channel")) if self.config.get("notification_channel") else None
        role = ctx.guild.get_role(self.config.get("mention_role")) if self.config.get("mention_role") else None
        
        embed.add_field(name="系統狀態", value="✅ 啟用" if self.config.get("enabled", False) else "❌ 停用", inline=True)
        embed.add_field(name="API 狀態", value="✅ 正常" if self.is_token_valid() else "❌ 需要設定", inline=True)
        embed.add_field(name="通知頻道", value=channel.mention if channel else "未設定", inline=True)
        embed.add_field(name="檢查間隔", value=f"{self.config.get('check_interval', 60)} 秒", inline=True)
        
        streamers = self.get_streamers()
        embed.add_field(name="追蹤實況主", value=f"{len(streamers)} 位", inline=True)
        embed.add_field(name="提及角色", value=role.mention if role else "未設定", inline=True)
        embed.add_field(name="提及所有人", value="✅ 開啟" if self.config.get("mention_everyone", False) else "❌ 關閉", inline=True)
        
        if streamers:
            streamer_list = []
            for username, data in streamers.items():
                status = "🔴" if data.get("is_live", False) else "⚫"
                streamer_list.append(f"{status} {username}")
            
            embed.add_field(name="實況主列表", value="\n".join(streamer_list[:10]), inline=False)
            if len(streamers) > 10:
                embed.add_field(name="", value=f"... 還有 {len(streamers) - 10} 位", inline=False)
        
        embed.add_field(name="可用指令", value="""
        `!twitch setup` - 設定 API 金鑰
        `!twitch channel <#頻道>` - 設定通知頻道
        `!twitch add <用戶名>` - 添加實況主
        `!twitch remove <用戶名>` - 移除實況主
        `!twitch list` - 查看所有實況主
        `!twitch test <用戶名>` - 測試通知
        `!twitch toggle` - 開關系統
        `!twitch debug` - 顯示除錯資訊
        """, inline=False)
        
        await ctx.send(embed=embed)

    @twitch.command(name="setup")
    @commands.has_permissions(manage_guild=True)
    async def setup_twitch(self, ctx):
        """設定 Twitch API"""
        embed = discord.Embed(
            title="🔧 Twitch API 設定",
            description="""
            要使用 Twitch 直播通知功能，你需要：
            
            1. 前往 https://dev.twitch.tv/console/apps
            2. 建立新應用程式
            3. 取得 Client ID 和 Client Secret
            4. 使用以下指令設定：
            
            `!twitch setkey <Client_ID> <Client_Secret>`
            
            **注意：** 請在私人頻道執行設定指令，避免洩露 API 金鑰！
            """,
            color=discord.Color.purple()
        )
        
        await ctx.send(embed=embed)

    @twitch.command(name="setkey")
    @commands.has_permissions(manage_guild=True)
    async def set_api_key(self, ctx, client_id: str, client_secret: str):
        """設定 API 金鑰"""
        try:
            await ctx.message.delete()
        except:
            pass
        
        self.config["client_id"] = client_id
        self.config["client_secret"] = client_secret
        self.save_config()
        
        if await self.get_twitch_token():
            await ctx.send("✅ API 金鑰設定成功！", delete_after=10)
        else:
            await ctx.send("❌ API 金鑰設定失敗，請檢查金鑰是否正確", delete_after=10)

    @twitch.command(name="channel")
    @commands.has_permissions(manage_guild=True)
    async def set_notification_channel(self, ctx, channel: discord.TextChannel):
        """設定通知頻道"""
        self.config["notification_channel"] = channel.id
        self.save_config()
        
        await ctx.send(f"✅ 已設定通知頻道為：{channel.mention}")

    @twitch.command(name="add")
    @commands.has_permissions(manage_guild=True)
    async def add_streamer(self, ctx, username: str, role: discord.Role = None):
        """添加實況主"""
        username = username.lower()
        
        user_id = await self.get_user_id(username)
        if not user_id:
            await ctx.send(f"❌ 找不到 Twitch 用戶：{username}")
            return
        
        try:
            with self.get_db_connection() as db:
                cursor = db.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO twitch_streamers 
                    (username, guild_id, discord_role, custom_message, is_live, stream_id, last_checked)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    username, self.guild_id, role.id if role else None, None,
                    0, None, datetime.now().isoformat()
                ))
                db.commit()
        except Exception as e:
            logger.error(f"添加實況主時發生錯誤: {e}")
            await ctx.send(f"❌ 添加實況主時發生錯誤")
            return
        
        role_text = f"，提及角色：{role.mention}" if role else ""
        await ctx.send(f"✅ 已添加實況主：{username}{role_text}")


    @twitch.command(name="remove")
    @commands.has_permissions(manage_guild=True)
    async def remove_streamer(self, ctx, username: str):
        """移除實況主"""
        username = username.lower()
    
        try:
            with self.get_db_connection() as db:
                cursor = db.cursor()
                cursor.execute("""
                    DELETE FROM twitch_streamers
                    WHERE username = ? AND guild_id = ?
             """, (username, self.guild_id))
                db.commit()
        
            await ctx.send(f"✅ 已移除實況主：{username}")
        except Exception as e:
            logger.error(f"移除實況主時發生錯誤: {e}")
            await ctx.send(f"❌ 無法移除實況主：{username}")


    @twitch.command(name="list")
    @commands.has_permissions(manage_guild=True)
    async def list_streamers(self, ctx):
        """查看所有實況主"""
        try:
            with self.get_db_connection() as db:
                cursor = db.cursor()
                cursor.execute("""
                    SELECT username, discord_role, is_live
                    FROM twitch_streamers
                    WHERE guild_id = ?
                """, (self.guild_id,))
                streamers = cursor.fetchall()

            if not streamers:
                await ctx.send("❌ 尚未添加任何實況主")
                return

            embed = discord.Embed(title="📺 追蹤的實況主", color=discord.Color.purple())

            for username, role_id, is_live in streamers:
                status = "🔴 直播中" if is_live else "⚫ 離線"

                role = ctx.guild.get_role(role_id) if role_id else None
                role_text = f"\n角色：{role.mention}" if role else ""

                embed.add_field(name=username, value=f"{status}{role_text}", inline=True)

            await ctx.send(embed=embed)
    
        except Exception as e:
            logger.error(f"列出實況主錯誤：{e}")
            await ctx.send("❌ 列出實況主時發生錯誤")
            
        for username in streamers.keys():
            # 使用當前檢查的狀態
            is_currently_live = self.stream_data.get(username, {}).get("is_live", False)
            status = "🔴 直播中" if is_currently_live else "⚫ 離線"
            role = ctx.guild.get_role(streamers[username].get("discord_role")) if streamers[username].get("discord_role") else None
            role_text = f"\n角色：{role.mention}" if role else ""
            embed.add_field(name=username, value=f"{status}{role_text}", inline=True)
        
        await ctx.send(embed=embed)

    @twitch.command(name="test")
    @commands.has_permissions(manage_guild=True)
    async def test_notification(self, ctx, username: str):
        """測試通知"""
        username = username.lower()

        try:
            with self.get_db_connection() as db:
                cursor = db.cursor()
                cursor.execute("""
                    SELECT channel_id, discord_role FROM twitch_streamers
                    WHERE username = ? AND guild_id = ?
                """, (username, self.guild_id))
                row = cursor.fetchone()

            if not row:
                await ctx.send(f"❌ 尚未追蹤實況主：{username}")
                return

            channel_id, discord_role = row

            user_id = await self.get_user_id(username)
            if not user_id:
                await ctx.send(f"❌ 找不到 Twitch 用戶：{username}")
                return

            stream_info = await self.get_stream_info(user_id)
            if not stream_info:
                await ctx.send(f"❌ {username} 目前沒有直播")
                return

            settings = {
                "channel_id": channel_id,
                "discord_role": discord_role
            }

            await self.send_live_notification(username, stream_info, settings)
            await ctx.send(f"✅ 已發送 {username} 的測試通知")

        except Exception as e:
            logger.error(f"測試通知錯誤：{e}")
            await ctx.send("❌ 發送通知時發生錯誤")


    @twitch.command(name="toggle")
    @commands.has_permissions(manage_guild=True)
    async def toggle_system(self, ctx):
        """開關系統"""
        self.config["enabled"] = not self.config.get("enabled", False)
        self.save_config()
        
        if self.config["enabled"]:
            if not self.check_streams.is_running():
                self.check_streams.start()
            await ctx.send("✅ Twitch 通知系統已啟用")
        else:
            if self.check_streams.is_running():
                self.check_streams.stop()
            await ctx.send("❌ Twitch 通知系統已停用")

    @twitch.command(name="debug")
    @commands.has_permissions(manage_guild=True)
    async def debug_info(self, ctx):
        """顯示除錯資訊"""
        embed = discord.Embed(title="🔍 除錯資訊", color=discord.Color.orange())
        
        api_status = "✅ 正常" if self.is_token_valid() else "❌ 無效"
        embed.add_field(name="API Token 狀態", value=api_status, inline=True)
        
        expires_text = f"<t:{int(self.token_expires_at.timestamp())}:R>" if self.token_expires_at else "未設定"
        embed.add_field(name="Token 過期時間", value=expires_text, inline=True)
        
        embed.add_field(name="Client ID", value="✅ 已設定" if self.config.get("client_id") else "❌ 未設定", inline=True)
        embed.add_field(name="Client Secret", value="✅ 已設定" if self.config.get("client_secret") else "❌ 未設定", inline=True)
        
        task_status = "✅ 運行中" if self.check_streams.is_running() else "❌ 已停止"
        embed.add_field(name="定時任務", value=task_status, inline=True)
        
        await ctx.send(embed=embed)

    def cog_unload(self):
        """卸載 Cog 時停止任務"""
        if self.check_streams.is_running():
            self.check_streams.stop()

async def setup(bot):
    await bot.add_cog(Twitch(bot))
    logger.info("✅ Twitch Cog 已載入")