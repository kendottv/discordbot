import os
import discord
from discord.ext import commands, tasks
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
import sqlite3

# 載入環境變數
load_dotenv()

class YTNotificationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv("YT_API_KEY")
        if not self.api_key:
            print("❌ 缺少 YT_API_KEY，YouTube 通知功能將無法工作！")
        
        self.db = sqlite3.connect("bot_data.db", check_same_thread=False)
        self.cursor = self.db.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS yt_config (
                guild_id INTEGER PRIMARY KEY,
                discord_channel_id INTEGER,
                channel_ids TEXT
            )
        """)
        self.db.commit()
        
        self.last_video_ids = {}  # 儲存每個頻道的最新影片 ID
        self.channel_names = {}  # 儲存頻道名稱快取
        self.check_new_videos.start()

    def get_yt_config(self, guild_id):
        """獲取 YouTube 通知設定"""
        self.cursor.execute("SELECT * FROM yt_config WHERE guild_id = ?", (guild_id,))
        result = self.cursor.fetchone()
        if result:
            return {
                "discord_channel_id": result[1],
                "channel_ids": eval(result[2]) if result[2] else []
            }
        return None

    def save_yt_config(self, guild_id, data):
        """儲存 YouTube 通知設定"""
        self.cursor.execute("""
            INSERT OR REPLACE INTO yt_config (guild_id, discord_channel_id, channel_ids)
            VALUES (?, ?, ?)
        """, (guild_id, data["discord_channel_id"], str(data["channel_ids"])))
        self.db.commit()

    async def get_channel_name(self, channel_id):
        """取得頻道名稱並快取"""
        if channel_id in self.channel_names:
            return self.channel_names[channel_id]
        
        try:
            youtube = build("youtube", "v3", developerKey=self.api_key)
            request = youtube.channels().list(
                part="snippet",
                id=channel_id,
                fields="items(snippet(title))"
            )
            response = request.execute()
            
            if "items" in response and response["items"]:
                channel_name = response["items"][0]["snippet"]["title"]
                self.channel_names[channel_id] = channel_name
                return channel_name
            else:
                return f"頻道 {channel_id}"
        except Exception as e:
            print(f"取得頻道名稱失敗: {e}")
            return f"頻道 {channel_id}"

    @tasks.loop(minutes=5)  # 每 5 分鐘檢查一次，可根據需求調整
    async def check_new_videos(self):
        if not self.api_key:
            print("❌ 缺少 YT_API_KEY，YouTube 通知功能將無法工作！")
            return
        
        youtube = build("youtube", "v3", developerKey=self.api_key)
        guild_ids = [row[0] for row in self.cursor.execute("SELECT guild_id FROM yt_config")]
        for guild_id in guild_ids:
            data = self.get_yt_config(guild_id)
            discord_channel_id = data.get("discord_channel_id")
            channel_ids = data.get("channel_ids", [])
            if not discord_channel_id or not channel_ids:
                print(f"❌ 伺服器 {guild_id} 缺少通知頻道或追蹤頻道，跳過檢查")
                continue

            try:
                for channel_id in channel_ids:
                    # 取得頻道最新影片
                    request = youtube.search().list(
                        part="snippet",
                        channelId=channel_id,
                        maxResults=1,
                        order="date",
                        type="video",
                        fields="items(id/videoId,snippet(publishedAt,title,channelTitle,thumbnails/high/url))"
                    )
                    response = request.execute()

                    if "items" in response and response["items"]:
                        item = response["items"][0]
                        video_id = item["id"]["videoId"]
                        title = item["snippet"]["title"]
                        published_at = item["snippet"]["publishedAt"]
                        channel_name = item["snippet"]["channelTitle"]
                        thumbnail_url = item["snippet"]["thumbnails"]["high"]["url"]

                        # 檢查是否為新影片
                        if video_id != self.last_video_ids.get(channel_id):
                            # 首次運行時，只記錄不發送通知
                            if channel_id not in self.last_video_ids:
                                print(f"初始化頻道 {channel_name} 的最新影片: {title}")
                                self.last_video_ids[channel_id] = video_id
                                continue
                            
                            # 檢查影片是否真的是最近發布的（避免舊影片被誤判為新影片）
                            try:
                                published_time = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                                time_diff = datetime.now(published_time.tzinfo) - published_time
                                
                                # 只有在 24 小時內發布的影片才算新影片
                                if time_diff.days > 1:
                                    print(f"影片 {title} 發布超過 24 小時，跳過通知")
                                    self.last_video_ids[channel_id] = video_id
                                    continue
                                    
                            except Exception as e:
                                print(f"時間解析錯誤: {e}")
                                # 如果時間解析失敗，還是繼續處理
                            
                            channel = self.bot.get_channel(int(discord_channel_id))
                            if channel:
                                # 解析發布時間
                                try:
                                    published_time = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                                    time_str = published_time.strftime("%Y-%m-%d %H:%M:%S")
                                except:
                                    time_str = published_at

                                # 創建類似 Twitch 的 embed
                                embed = discord.Embed(
                                    color=0xFF0000  # YouTube 紅色
                                )
                                
                                # 設置標題和描述
                                embed.add_field(
                                    name="🔴 新影片發布！",
                                    value=f"**頻道**: {channel_name}\n**標題**: {title}\n**發布時間**: {time_str}",
                                    inline=False
                                )
                                
                                # 添加縮圖
                                embed.set_image(url=thumbnail_url)
                                
                                # 設置時間戳
                                embed.timestamp = datetime.now()
                                
                                # 發送訊息
                                await channel.send(
                                    f"🔔 **{channel_name}** 發布了新影片！\n"
                                    f"**{title}**\n"
                                    f"https://www.youtube.com/watch?v={video_id}",
                                    embed=embed
                                )
                                
                                print(f"✅ 已發送 {channel_name} 的新影片通知: {title}")
                                
                            self.last_video_ids[channel_id] = video_id
                    else:
                        print(f"未找到頻道 {channel_id} 的影片資料")
            except HttpError as e:
                print(f"API 錯誤 (頻道 {channel_id}): {e}")
            except Exception as e:
                print(f"發生錯誤 (頻道 {channel_id}): {e}")

    @check_new_videos.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    @commands.command(name="setytchannels")
    @commands.has_permissions(administrator=True)
    async def set_yt_channels(self, ctx, channel: discord.TextChannel, *channel_ids: str):
        """設定 YouTube 通知頻道及追蹤的頻道列表
        使用方式：!setytchannels #頻道 頻道ID1 頻道ID2 ...
        """
        if not channel_ids:
            await ctx.send("❌ 請提供至少一個 YouTube 頻道 ID！")
            return

        guild_id = ctx.guild.id
        
        # 驗證頻道ID並取得名稱
        valid_channels = []
        channel_names = []
        
        for channel_id in channel_ids:
            channel_name = await self.get_channel_name(channel_id.strip())
            if channel_name != f"頻道 {channel_id}":
                valid_channels.append(channel_id.strip())
                channel_names.append(channel_name)
            else:
                await ctx.send(f"⚠️ 頻道 ID `{channel_id}` 可能無效，請確認後再試")
                return
        
        self.save_yt_config(guild_id, {
            "discord_channel_id": channel.id,
            "channel_ids": valid_channels
        })
        
        channel_list = '\n'.join([f"• {name}" for name in channel_names])
        await ctx.send(
            f"✅ 已為 **{ctx.guild.name}** 設定 YouTube 通知頻道：{channel.mention}\n"
            f"**追蹤頻道列表：**\n{channel_list}"
        )

    @commands.command(name="listytchannels")
    @commands.has_permissions(administrator=True)
    async def list_yt_channels(self, ctx):
        """列出目前追蹤的 YouTube 頻道"""
        guild_id = ctx.guild.id
        
        if not self.get_yt_config(guild_id):
            await ctx.send("❌ 此伺服器尚未設定 YouTube 通知！")
            return
        
        data = self.get_yt_config(guild_id)
        channel_ids = data.get("channel_ids", [])
        discord_channel_id = data.get("discord_channel_id")
        
        if not channel_ids:
            await ctx.send("❌ 沒有追蹤任何 YouTube 頻道！")
            return
        
        discord_channel = self.bot.get_channel(int(discord_channel_id))
        channel_mention = discord_channel.mention if discord_channel else "頻道已刪除"
        
        channel_list = []
        for channel_id in channel_ids:
            channel_name = await self.get_channel_name(channel_id)
            channel_list.append(f"• {channel_name} (`{channel_id}`)")
        
        embed = discord.Embed(
            title="📺 YouTube 通知設定",
            description=f"**通知頻道**: {channel_mention}\n\n**追蹤頻道列表**:\n" + '\n'.join(channel_list),
            color=0xFF0000
        )
        
        await ctx.send(embed=embed)

    def cog_unload(self):
        self.check_new_videos.cancel()

    def __del__(self):
        """銷毀實例時關閉資料庫連線"""
        self.db.close()

async def setup(bot):
    await bot.add_cog(YTNotificationCog(bot))