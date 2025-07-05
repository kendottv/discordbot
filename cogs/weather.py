import discord
from discord.ext import commands, tasks
import asyncio
import aiohttp
import json
import os
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv

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

        self.data_file = "data/weather_data.json"
        self.weather_channels = self.load_weather_data()
        self.active_votes = {}  # 儲存投票訊息 ID 與選項
        self.daily_weather_update.start()

    def load_weather_data(self):
        os.makedirs("data", exist_ok=True)
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.info("天氣資料文件未找到，創建新文件")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"天氣資料解析失敗: {e}")
            return {}

    def save_weather_data(self):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.weather_channels, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"儲存天氣資料失敗: {e}")

    async def fetch_weather_data(self, city="Taipei"):
        if not self.weather_api_key:
            logger.error("API Key 未設定，無法請求天氣資料")
            return None
            
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"q": city, "appid": self.weather_api_key, "units": "metric", "lang": "zh_tw"}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    logger.debug(f"請求URL: {response.url}")
                    logger.debug(f"狀態碼: {response.status}")
                    text = await response.text()
                    logger.debug(f"回應內容: {text}")
                    if response.status == 200:
                        data = json.loads(text)
                        return data
                    else:
                        logger.error(f"API請求失敗: {text}")
                        return None
        except aiohttp.ClientConnectionError as e:
            logger.error(f"網路連線錯誤: {e}")
            return None
        except Exception as e:
            logger.error(f"獲取天氣資料錯誤: {e}")
            return None

    def format_weather_message(self, data, city="Taipei", is_daily=False):
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
            icon_map = {
                "01d": "☀️", "01n": "🌙", "02d": "⛅", "02n": "☁️",
                "03d": "☁️", "03n": "☁️", "04d": "☁️", "04n": "☁️",
                "09d": "🌧️", "09n": "🌧️", "10d": "🌦️", "10n": "🌧️",
                "11d": "⛈️", "11n": "⛈️", "13d": "❄️", "13n": "❄️",
                "50d": "🌫️", "50n": "🌫️"
            }
            icon = icon_map.get(weather_icon, "🌤️")
            
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
        if not self.weather_channels:
            logger.info("沒有設定天氣頻道，跳過自動更新")
            return
        
        logger.info("開始執行每日天氣更新...")
        for guild_id, channel_data in self.weather_channels.items():
            try:
                channel_id = channel_data.get("channel_id")
                cities = channel_data.get("cities", ["Taipei"])
                channel = self.bot.get_channel(int(channel_id))
                if not channel:
                    logger.warning(f"找不到頻道 {channel_id}")
                    continue
                
                for city in cities:
                    weather_data = await self.fetch_weather_data(city)
                    if weather_data:
                        embed = self.format_weather_message(weather_data, city, is_daily=True)
                        if isinstance(embed, discord.Embed):
                            await channel.send(embed=embed)
                            temp = weather_data["main"]["temp"]
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
        guild_id = str(ctx.guild.id)
        city_list = [city.strip() for city in cities.split(",")]
        self.weather_channels[guild_id] = {"channel_id": str(channel.id), "cities": city_list}
        self.save_weather_data()
        await ctx.send(f"✅ 已為 {ctx.guild.name} 設定天氣預報：\n📍 頻道：{channel.mention}\n🏙️ 城市：{', '.join(city_list)}")

    @commands.command(name="getweather")
    async def get_weather(self, ctx, *, city: str = None):
        guild_id = str(ctx.guild.id)
        if city:
            query_city = city.strip()
        elif guild_id in self.weather_channels:
            query_city = self.weather_channels[guild_id].get("cities", ["Taipei"])[0]
        else:
            query_city = "Taipei"
        
        if guild_id in self.weather_channels:
            weather_channel_id = self.weather_channels[guild_id].get("channel_id")
            if weather_channel_id and str(ctx.channel.id) != weather_channel_id:
                weather_channel = self.bot.get_channel(int(weather_channel_id))
                if weather_channel:
                    await ctx.send(f"❌ 請在 {weather_channel.mention} 頻道中使用此命令")
                    return
        
        weather_data = await self.fetch_weather_data(query_city)
        if weather_data:
            embed = self.format_weather_message(weather_data, query_city)
            if isinstance(embed, discord.Embed):
                await ctx.send(embed=embed)
                temp = weather_data["main"]["temp"]
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
        guild_id = str(ctx.guild.id)
        if guild_id not in self.weather_channels:
            await ctx.send("❌ 請先使用 `!setweatherchannel` 設定天氣頻道")
            return
        
        channel_data = self.weather_channels[guild_id]
        channel_id = channel_data.get("channel_id")
        cities = channel_data.get("cities", ["Taipei"])
        
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            await ctx.send("❌ 天氣頻道未正確設定或已被刪除")
            return
        
        for city in cities:
            weather_data = await self.fetch_weather_data(city)
            if weather_data:
                embed = self.format_weather_message(weather_data, city, is_daily=True)
                if isinstance(embed, discord.Embed):
                    await channel.send(embed=embed)
                    temp = weather_data["main"]["temp"]
                    if temp < 10:
                        await channel.send(f"❄️ 提醒：{city} 溫度 {temp}°C 低於 10°C，請注意保暖！")
                else:
                    await channel.send(embed)
            else:
                await ctx.send(f"❌ 無法獲取 {city} 的天氣資料")

    @commands.command(name="weatherinfo")
    async def weather_info(self, ctx):
        guild_id = str(ctx.guild.id)
        if guild_id not in self.weather_channels:
            await ctx.send("❌ 此伺服器尚未設定天氣頻道")
            return
        
        channel_data = self.weather_channels[guild_id]
        channel_id = channel_data.get("channel_id")
        cities = channel_data.get("cities", ["Taipei"])
        
        channel = self.bot.get_channel(int(channel_id))
        if channel:
            embed = discord.Embed(title="🌤️ 天氣設定資訊", color=discord.Color.blue())
            embed.add_field(name="📍 頻道", value=channel.mention, inline=False)
            embed.add_field(name="🏙️ 城市", value=", ".join(cities), inline=False)
            embed.add_field(name="⏰ 更新時間", value="每日 00:00", inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ 設定的天氣頻道已被刪除，請重新設定")

    @commands.command(name="removeweather")
    @commands.has_permissions(administrator=True)
    async def remove_weather(self, ctx):
        guild_id = str(ctx.guild.id)
        if guild_id in self.weather_channels:
            del self.weather_channels[guild_id]
            self.save_weather_data()
            await ctx.send("✅ 已移除此伺服器的天氣設定")
        else:
            await ctx.send("❌ 此伺服器沒有設定天氣功能")

    def cog_unload(self):
        self.daily_weather_update.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info("✅ Weather Cog 已載入")
        logger.info(f"已設定 {len(self.weather_channels)} 個伺服器的天氣頻道")

async def setup(bot):
    await bot.add_cog(WeatherCog(bot))