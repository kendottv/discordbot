import discord
from discord.ext import commands, tasks
import asyncio
import aiohttp
import json
import os
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv
import sqlite3

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

class WeatherCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.weather_api_key = os.getenv("WEATHER_API_KEY")
        if not self.weather_api_key:
            logger.error("⚠️ 警告：WEATHER_API_KEY 未設定，無法獲取天氣資料！")
        else:
            logger.info(f"API Key 載入: {self.weather_api_key[:5]}...")
        
        self.db = sqlite3.connect("bot_data.db", check_same_thread=False)
        self.cursor = self.db.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS weather_channels (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER,
                cities TEXT
            )
        """)
        self.db.commit()
        
        self.active_votes = {}  # 儲存投票訊息 ID 與選項
        self.daily_weather_update.start()

    def get_weather_channels(self, guild_id):
        """獲取天氣頻道設定"""
        self.cursor.execute("SELECT * FROM weather_channels WHERE guild_id = ?", (guild_id,))
        result = self.cursor.fetchone()
        if result:
            return {
                "channel_id": result[1],
                "cities": eval(result[2]) if result[2] else ["Taipei"]
            }
        return None

    def save_weather_channels(self, guild_id, data):
        """儲存天氣頻道設定"""
        self.cursor.execute("""
            INSERT OR REPLACE INTO weather_channels (guild_id, channel_id, cities)
            VALUES (?, ?, ?)
        """, (guild_id, data["channel_id"], str(data["cities"])))
        self.db.commit()

    async def fetch_current_weather(self, city="Taipei"):
        """獲取當前天氣資料"""
        if not self.weather_api_key:
            logger.error("API Key 未設定，無法請求天氣資料")
            return None
            
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"q": city, "appid": self.weather_api_key, "units": "metric", "lang": "zh_tw"}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    logger.debug(f"當前天氣請求URL: {response.url}")
                    logger.debug(f"狀態碼: {response.status}")
                    text = await response.text()
                    logger.debug(f"回應內容: {text}")
                    if response.status == 200:
                        data = json.loads(text)
                        return data
                    else:
                        logger.error(f"API請求失敗: {text}")
                        return None
        except Exception as e:
            logger.error(f"獲取當前天氣資料錯誤: {e}")
            return None

    async def fetch_daily_forecast(self, city="Taipei"):
        """獲取每日天氣預報（5天3小時間隔）"""
        if not self.weather_api_key:
            logger.error("API Key 未設定，無法請求天氣資料")
            return None
            
        url = "https://api.openweathermap.org/data/2.5/forecast"
        params = {"q": city, "appid": self.weather_api_key, "units": "metric", "lang": "zh_tw"}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    logger.debug(f"預報請求URL: {response.url}")
                    logger.debug(f"狀態碼: {response.status}")
                    text = await response.text()
                    if response.status == 200:
                        data = json.loads(text)
                        return data
                    else:
                        logger.error(f"預報API請求失敗: {text}")
                        return None
        except Exception as e:
            logger.error(f"獲取預報資料錯誤: {e}")
            return None

    def get_weather_icon(self, weather_icon):
        """獲取天氣圖示"""
        icon_map = {
            "01d": "☀️", "01n": "🌙", "02d": "⛅", "02n": "☁️",
            "03d": "☁️", "03n": "☁️", "04d": "☁️", "04n": "☁️",
            "09d": "🌧️", "09n": "🌧️", "10d": "🌦️", "10n": "🌧️",
            "11d": "⛈️", "11n": "⛈️", "13d": "❄️", "13n": "❄️",
            "50d": "🌫️", "50n": "🌫️"
        }
        return icon_map.get(weather_icon, "🌤️")

    def format_combined_weather_message(self, current_data, forecast_data, city="Taipei", is_daily=False):
        """格式化綜合天氣訊息（當前天氣 + 今日預報）"""
        if not current_data or current_data.get("cod") != 200:
            error_msg = current_data.get("message", "未知錯誤") if current_data else "無回應"
            logger.error(f"當前天氣資料無效: {error_msg}")
            return f"❌ 無法獲取 {city} 的天氣資料: " + error_msg
        
        try:
            # 當前天氣資訊
            current_weather = current_data["weather"][0]["description"]
            current_temp = round(current_data["main"]["temp"], 1)
            current_feels_like = round(current_data["main"]["feels_like"], 1)
            current_humidity = current_data["main"]["humidity"]
            current_pressure = current_data["main"]["pressure"]
            current_visibility = current_data.get("visibility", 0) / 1000  # 轉換為公里
            current_icon = self.get_weather_icon(current_data["weather"][0]["icon"])
            
            # 風速和風向
            wind_speed = current_data.get("wind", {}).get("speed", 0) * 3.6  # 轉換為 km/h
            wind_deg = current_data.get("wind", {}).get("deg", 0)
            wind_direction = self.get_wind_direction(wind_deg)
            
            # 日出日落時間
            sunrise = datetime.fromtimestamp(current_data["sys"]["sunrise"]).strftime("%H:%M")
            sunset = datetime.fromtimestamp(current_data["sys"]["sunset"]).strftime("%H:%M")
            
            prefix = "🌅 今日天氣更新" if is_daily else "🌤️ 即時天氣"
            
            # 建立主要的嵌入訊息
            embed = discord.Embed(
                title=f"{current_icon} {city} - {prefix}",
                description=f"**{current_weather}**",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            # 當前天氣詳細資訊
            embed.add_field(name="🌡️ 溫度", value=f"{current_temp}°C", inline=True)
            embed.add_field(name="🤲 體感溫度", value=f"{current_feels_like}°C", inline=True)
            embed.add_field(name="💧 濕度", value=f"{current_humidity}%", inline=True)
            embed.add_field(name="🌬️ 風速", value=f"{wind_speed:.1f} km/h {wind_direction}", inline=True)
            embed.add_field(name="🔻 氣壓", value=f"{current_pressure} hPa", inline=True)
            embed.add_field(name="👁️ 能見度", value=f"{current_visibility:.1f} km", inline=True)
            embed.add_field(name="🌅 日出", value=sunrise, inline=True)
            embed.add_field(name="🌇 日落", value=sunset, inline=True)
            embed.add_field(name="⏰ 更新時間", value=f"<t:{int(current_data['dt'])}:R>", inline=True)
            
            # 如果有預報資料，添加今日預報
            if forecast_data and forecast_data.get("cod") == "200":
                today_forecast = self.get_today_forecast(forecast_data)
                if today_forecast:
                    forecast_text = []
                    for item in today_forecast[:4]:  # 顯示今日接下來4個時段
                        time_str = datetime.fromtimestamp(item["dt"]).strftime("%H:%M")
                        temp = round(item["main"]["temp"], 1)
                        desc = item["weather"][0]["description"]
                        icon = self.get_weather_icon(item["weather"][0]["icon"])
                        forecast_text.append(f"{time_str} {icon} {temp}°C {desc}")
                    
                    if forecast_text:
                        embed.add_field(
                            name="📅 今日預報",
                            value="\n".join(forecast_text),
                            inline=False
                        )
            
            return embed
            
        except KeyError as e:
            logger.error(f"天氣資料格式錯誤: {e}, 資料: {current_data}")
            return f"❌ {city} 天氣資料格式錯誤"
        except Exception as e:
            logger.error(f"格式化天氣訊息失敗: {e}")
            return f"❌ 格式化 {city} 天氣資料失敗"

    def get_wind_direction(self, degrees):
        """根據風向角度返回方向"""
        directions = ["北", "東北", "東", "東南", "南", "西南", "西", "西北"]
        index = round(degrees / 45) % 8
        return directions[index]

    def get_today_forecast(self, forecast_data):
        """從預報資料中提取今日的預報"""
        today = datetime.now().date()
        today_forecast = []
        
        for item in forecast_data["list"]:
            forecast_date = datetime.fromtimestamp(item["dt"]).date()
            if forecast_date == today:
                today_forecast.append(item)
        
        return today_forecast

    async def fetch_weather_data(self, city="Taipei"):
        """向後兼容的方法，現在調用新的 fetch_current_weather"""
        return await self.fetch_current_weather(city)

    def format_weather_message(self, data, city="Taipei", is_daily=False):
        """向後兼容的方法，使用舊的簡單格式"""
        if not data or data.get("cod") != 200:
            error_msg = data.get("message", "未知錯誤") if data else "無回應"
            logger.error(f"天氣資料無效: {error_msg}")
            return "❌ 無法獲取天氣資料: " + error_msg
        
        try:
            weather_desc = data["weather"][0]["description"]
            temp = round(data["main"]["temp"], 1)
            feels_like = round(data["main"]["feels_like"], 1)
            humidity = data["main"]["humidity"]
            weather_icon = data["weather"][0]["icon"]
            icon = self.get_weather_icon(weather_icon)
            
            prefix = "🌅 今日天氣更新" if is_daily else "🌤️ 當前天氣"
            
            embed = discord.Embed(
                title=f"{icon} {city} - {prefix}",
                description=weather_desc,
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            embed.add_field(name="🌡️ 溫度", value=f"{temp}°C", inline=True)
            embed.add_field(name="🤲 體感溫度", value=f"{feels_like}°C", inline=True)
            embed.add_field(name="💧 濕度", value=f"{humidity}%", inline=True)
            
            return embed
        except KeyError as e:
            logger.error(f"天氣資料格式錯誤: {e}, 資料: {data}")
            return "❌ 天氣資料格式錯誤"
        except Exception as e:
            logger.error(f"格式化天氣訊息失敗: {e}")
            return "❌ 格式化天氣資料失敗"

    @tasks.loop(time=datetime.strptime("00:00", "%H:%M").time())
    async def daily_weather_update(self):
        await self.bot.wait_until_ready()
        guild_ids = [row[0] for row in self.cursor.execute("SELECT guild_id FROM weather_channels")]
        if not guild_ids:
            logger.info("沒有設定天氣頻道，跳過自動更新")
            return
        
        logger.info("開始執行每日天氣更新...")
        for guild_id in guild_ids:
            try:
                channel_data = self.get_weather_channels(guild_id)
                channel_id = channel_data.get("channel_id")
                cities = channel_data.get("cities", ["Taipei"])
                channel = self.bot.get_channel(int(channel_id))
                if not channel:
                    logger.warning(f"找不到頻道 {channel_id}")
                    continue
                
                for city in cities:
                    # 獲取當前天氣和預報資料
                    current_weather = await self.fetch_current_weather(city)
                    forecast_data = await self.fetch_daily_forecast(city)
                    
                    if current_weather:
                        # 使用新的綜合格式
                        embed = self.format_combined_weather_message(
                            current_weather, forecast_data, city, is_daily=True
                        )
                        if isinstance(embed, discord.Embed):
                            await channel.send(embed=embed)
                            temp = current_weather["main"]["temp"]
                            if temp < 10:  # 溫度提醒條件
                                await channel.send(f"❄️ 提醒：{city} 溫度 {temp}°C 低於 10°C，請注意保暖！")
                        else:
                            await channel.send(embed)
                    else:
                        await channel.send(f"❌ 無法獲取 {city} 的天氣資料")
            except Exception as e:
                logger.error(f"發送天氣更新失敗 (Guild: {guild_id}): {e}")
        logger.info("每日天氣更新完成")

    @daily_weather_update.before_loop
    async def before_daily_update(self):
        await self.bot.wait_until_ready()
        logger.info("天氣更新任務已啟動，將在每日00:00執行")

    @commands.command(name="setweatherchannel")
    @commands.has_permissions(administrator=True)
    async def set_weather_channel(self, ctx, channel: discord.TextChannel, *, cities: str):
        """設定天氣預報頻道和多個城市（用逗號分隔，例如 Taipei,Tokyo）
        使用方式：!setweatherchannel #頻道 Taipei,Tokyo
        """
        guild_id = ctx.guild.id
        city_list = [city.strip() for city in cities.split(",")]
        self.save_weather_channels(guild_id, {"channel_id": channel.id, "cities": city_list})
        await ctx.send(f"✅ 已為 {ctx.guild.name} 設定天氣預報：\n📍 頻道：{channel.mention}\n🏙️ 城市：{', '.join(city_list)}")

    @commands.command(name="getweather")
    async def get_weather(self, ctx, *, city: str = None):
        """獲取天氣資料（現在包含當前天氣和今日預報）"""
        guild_id = ctx.guild.id
        if city:
            query_city = city.strip()
        elif self.get_weather_channels(guild_id):
            query_city = self.get_weather_channels(guild_id).get("cities", ["Taipei"])[0]
        else:
            query_city = "Taipei"
        
        if self.get_weather_channels(guild_id):
            weather_channel_id = self.get_weather_channels(guild_id).get("channel_id")
            if weather_channel_id and ctx.channel.id != weather_channel_id:
                weather_channel = self.bot.get_channel(weather_channel_id)
                if weather_channel:
                    await ctx.send(f"❌ 請在 {weather_channel.mention} 頻道中使用此命令")
                    return
        
        # 獲取當前天氣和預報資料
        current_weather = await self.fetch_current_weather(query_city)
        forecast_data = await self.fetch_daily_forecast(query_city)
        
        if current_weather:
            # 使用新的綜合格式
            embed = self.format_combined_weather_message(
                current_weather, forecast_data, query_city, is_daily=False
            )
            if isinstance(embed, discord.Embed):
                await ctx.send(embed=embed)
                temp = current_weather["main"]["temp"]
                if temp < 10:
                    await ctx.send(f"❄️ 提醒：{query_city} 溫度 {temp}°C 低於 10°C，請注意保暖！")
            else:
                await ctx.send(embed)
        else:
            await ctx.send(f"❌ 無法獲取 {query_city} 的天氣資料，請檢查城市名稱或API Key")

    @commands.command(name="createvote")
    @commands.has_permissions(administrator=True)
    async def create_vote(self, ctx, question: str, *options: str):
        """創建投票（最多5個選項，用空格分隔）
        使用方式：!createvote "今天去哪玩？" 台北 東京 京都
        """
        if len(options) < 2 or len(options) > 5:
            await ctx.send("❌ 投票需2-5個選項！")
            return

        view = discord.ui.View()
        vote_data = {"options": {str(i): {"label": opt, "votes": []} for i, opt in enumerate(options)}, "total": 0}

        for i, option in enumerate(options):
            button = discord.ui.Button(label=option, style=discord.ButtonStyle.primary, custom_id=str(i))
            async def button_callback(interaction):
                user_id = interaction.user.id
                vote_id = interaction.data["custom_id"]
                if user_id in vote_data["options"][vote_id]["votes"]:
                    await interaction.response.send_message("❌ 你已投票！", ephemeral=True)
                    return
                vote_data["options"][vote_id]["votes"].append(user_id)
                vote_data["total"] += 1
                await interaction.response.send_message(f"✅ 你為 '{option}' 投票！", ephemeral=True)
                await self.update_vote_message(ctx, message)

            button.callback = button_callback
            view.add_item(button)

        message = await ctx.send(f"**{question}**\n投票中...", view=view)
        self.active_votes[message.id] = {"message": message, "data": vote_data}
        logger.info(f"創建投票: {question}, 選項: {', '.join(options)}")

    async def update_vote_message(self, ctx, message):
        """更新投票訊息顯示結果"""
        vote_data = self.active_votes.get(message.id, {}).get("data")
        if not vote_data:
            return

        embed = discord.Embed(title="投票結果", color=discord.Color.green())
        for i in vote_data["options"]:
            count = len(vote_data["options"][i]["votes"])
            percentage = (count / vote_data["total"] * 100) if vote_data["total"] > 0 else 0
            embed.add_field(name=f"選項 {int(i)+1}: {vote_data['options'][i]['label']}", 
                          value=f"票數: {count} ({percentage:.1f}%)", inline=False)
        await message.edit(content=f"**投票結果**\n總票數: {vote_data['total']}", embed=embed)
        logger.info(f"更新投票結果: 總票數 {vote_data['total']}")

    @commands.command(name="showvote")
    async def show_vote(self, ctx, message_id: int):
        """顯示投票結果
        使用方式：!showvote 訊息ID
        """
        if message_id not in self.active_votes:
            await ctx.send("❌ 無效的投票ID！")
            return
        await self.update_vote_message(ctx, self.active_votes[message_id]["message"])

    @commands.command(name="refreshweather")
    @commands.has_permissions(administrator=True)
    async def refresh_weather(self, ctx):
        """手動刷新天氣資料（包含當前天氣和今日預報）"""
        guild_id = ctx.guild.id
        if not self.get_weather_channels(guild_id):
            await ctx.send("❌ 請先使用 `!setweatherchannel` 設定天氣頻道")
            return
        
        channel_data = self.get_weather_channels(guild_id)
        channel_id = channel_data.get("channel_id")
        cities = channel_data.get("cities", ["Taipei"])
        
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            await ctx.send("❌ 天氣頻道未正確設定或已被刪除")
            return
        
        await ctx.send("🔄 正在刷新天氣資料...")
        
        for city in cities:
            # 獲取當前天氣和預報資料
            current_weather = await self.fetch_current_weather(city)
            forecast_data = await self.fetch_daily_forecast(city)
            
            if current_weather:
                # 使用新的綜合格式
                embed = self.format_combined_weather_message(
                    current_weather, forecast_data, city, is_daily=True
                )
                if isinstance(embed, discord.Embed):
                    await channel.send(embed=embed)
                    temp = current_weather["main"]["temp"]
                    if temp < 10:
                        await channel.send(f"❄️ 提醒：{city} 溫度 {temp}°C 低於 10°C，請注意保暖！")
                else:
                    await channel.send(embed)
            else:
                await channel.send(f"❌ 無法獲取 {city} 的天氣資料")
        
        await ctx.send("✅ 天氣資料刷新完成！")

    @commands.command(name="weatherinfo")
    async def weather_info(self, ctx):
        guild_id = ctx.guild.id
        if not self.get_weather_channels(guild_id):
            await ctx.send("❌ 此伺服器尚未設定天氣頻道")
            return
        
        channel_data = self.get_weather_channels(guild_id)
        channel_id = channel_data.get("channel_id")
        cities = channel_data.get("cities", ["Taipei"])
        
        channel = self.bot.get_channel(int(channel_id))
        if channel:
            embed = discord.Embed(title="🌤️ 天氣設定資訊", color=discord.Color.blue())
            embed.add_field(name="📍 頻道", value=channel.mention, inline=False)
            embed.add_field(name="🏙️ 城市", value=", ".join(cities), inline=False)
            embed.add_field(name="⏰ 更新時間", value="每日 00:00", inline=False)
            embed.add_field(name="📊 資料內容", value="當前天氣 + 今日預報", inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ 設定的天氣頻道已被刪除，請重新設定")

    @commands.command(name="removeweather")
    @commands.has_permissions(administrator=True)
    async def remove_weather(self, ctx):
        guild_id = ctx.guild.id
        if self.get_weather_channels(guild_id):
            self.cursor.execute("DELETE FROM weather_channels WHERE guild_id = ?", (guild_id,))
            self.db.commit()
            await ctx.send("✅ 已移除此伺服器的天氣設定")
        else:
            await ctx.send("❌ 此伺服器沒有設定天氣功能")

    def cog_unload(self):
        self.daily_weather_update.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info("✅ Enhanced Weather Cog 已載入")
        logger.info(f"已設定 {len([row[0] for row in self.cursor.execute('SELECT guild_id FROM weather_channels')])} 個伺服器的天氣頻道")

    def __del__(self):
        """銷毀實例時關閉資料庫連線"""
        if hasattr(self, 'db'):
            self.db.close()

async def setup(bot):
    await bot.add_cog(WeatherCog(bot))