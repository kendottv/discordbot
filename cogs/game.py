import discord
from discord.ext import commands
import os
import random
import logging
import requests
import aiohttp
import asyncio
from datetime import datetime, timedelta
import sqlite3

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = sqlite3.connect("bot_data.db", check_same_thread=False)
        self.cursor = self.db.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_scores (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                score INTEGER DEFAULT 0
            )
        """)
        self.db.commit()
        self.active_game = False
        self.target_number = None
        self.max_guesses = 5
        self.current_player = None
        self.guesses_left = 0
        self.reddit_token = None
        self.token_expires_at = None
        self.current_command = None

    def get_score(self, user_id):
        self.cursor.execute("SELECT score FROM game_scores WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        return result[0] if result else 0

    def save_score(self, user_id, score):
        username = str(self.bot.get_user(user_id) or "Unknown")
        self.cursor.execute("INSERT OR REPLACE INTO game_scores (user_id, username, score) VALUES (?, ?, ?)",
                           (user_id, username, score))
        self.db.commit()

    async def get_reddit_token(self, max_attempts=3, attempt=1):
        logger.debug(f"嘗試獲取 Reddit Token，次數: {attempt}/{max_attempts}")
        if self.reddit_token and self.token_expires_at and datetime.now() < self.token_expires_at:
            logger.debug("使用現有 Reddit Token")
            return True
        
        client_id = os.getenv("REDDIT_CLIENT_ID")
        client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        
        if not client_id or not client_secret:
            logger.error(f"Reddit Client ID 或 Client Secret 未設定: Client_ID={client_id}, Client_Secret={'*' * len(client_secret) if client_secret else 'None'}")
            return False

        url = "https://www.reddit.com/api/v1/access_token"
        auth = aiohttp.BasicAuth(client_id, client_secret)
        data = {"grant_type": "client_credentials"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data, auth=auth) as response:
                    response_text = await response.text()
                    logger.debug(f"Reddit Token 請求狀態: {response.status}, URL: {url}")
                    
                    if response.status == 200:
                        data = await response.json()
                        self.reddit_token = data["access_token"]
                        expires_in = data.get("expires_in", 3600)
                        self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)
                        logger.info("✅ 成功獲取新 Reddit Token")
                        return True
                    else:
                        logger.error(f"❌ Reddit Token 請求失敗: {response.status}, 回應: {response_text}")
                        if attempt < max_attempts:
                            logger.warning(f"第 {attempt} 次嘗試失敗，{max_attempts - attempt} 次機會剩餘")
                            await asyncio.sleep(2)  # 增加等待時間
                            return await self.get_reddit_token(max_attempts, attempt + 1)
                        return False
        except Exception as e:
            logger.error(f"❌ 獲取 Reddit Token 時發生錯誤: {e}")
            if attempt < max_attempts:
                logger.warning(f"第 {attempt} 次嘗試失敗，{max_attempts - attempt} 次機會剩餘")
                await asyncio.sleep(2)
                return await self.get_reddit_token(max_attempts, attempt + 1)
            return False

    async def fetch_meme_from_source(self, source="reddit"):
        """獲取迷因的核心方法 - 重命名避免衝突"""
        if source == "reddit":
            return await self._fetch_reddit_meme()
        elif source == "memeapi":
            return await self._fetch_memeapi_meme()
        else:
            logger.error(f"不支援的來源: {source}")
            return None

    async def _fetch_reddit_meme(self):
        """從 Reddit 獲取迷因"""
        success = await self.get_reddit_token()
        if not success:
            logger.error("Reddit Token 獲取失敗")
            return None

        # 嘗試多個 subreddit
        subreddits = ["memes", "dankmemes", "wholesomememes", "meme"]
        
        for subreddit in subreddits:
            url = f"https://oauth.reddit.com/r/{subreddit}/hot"
            headers = {
                "Authorization": f"Bearer {self.reddit_token}",
                "User-Agent": "DiscordBot/1.0 by YourUsername"
            }
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers) as response:
                        logger.debug(f"Reddit API 回應狀態: {response.status}, URL: {url}")
                        
                        if response.status == 200:
                            data = await response.json()
                            posts = []
                            
                            # 過濾出圖片貼文
                            for post in data.get("data", {}).get("children", []):
                                post_data = post.get("data", {})
                                # 檢查是否為圖片
                                if (post_data.get("post_hint") == "image" or 
                                    post_data.get("url", "").lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))):
                                    posts.append(post_data)
                            
                            if posts:
                                post = random.choice(posts)
                                logger.info(f"Reddit 獲取迷因: {post['title']} - {post['url']}")
                                return {
                                    "title": post["title"],
                                    "url": post["url"],
                                    "source": f"r/{subreddit}"
                                }
                        else:
                            logger.warning(f"Reddit API 錯誤: {response.status}")
                            
            except Exception as e:
                logger.error(f"Reddit API 錯誤 ({subreddit}): {e}")
                continue
        
        logger.warning("所有 Reddit subreddit 都無法獲取迷因")
        return None

    async def _fetch_memeapi_meme(self):
        """從 meme-api 獲取迷因"""
        url = "https://meme-api.com/gimme"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.debug(f"meme-api 回應: {data}")
                        
                        if data.get("success") and data.get("url"):
                            logger.info(f"meme-api 獲取迷因: {data.get('title')} - {data['url']}")
                            return {
                                "title": data.get("title", "隨機迷因"),
                                "url": data["url"],
                                "source": "meme-api"
                            }
                        else:
                            logger.warning("meme-api 回應無效")
                            return None
                    else:
                        logger.error(f"meme-api 錯誤: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"meme-api.com 錯誤: {e}")
            return None

    @commands.group(name="game", invoke_without_command=True)
    async def game(self, ctx):
        await ctx.send("使用 !game start 開始遊戲，!game guess <數字> 猜測，!game end 結束，!meme <source> 獲取迷因！(source: reddit/memeapi, 預設 reddit)")

    @game.command(name="start")
    async def start_game(self, ctx):
        if self.active_game:
            await ctx.send("❌ 遊戲已在進行中，請先結束當前遊戲。")
            return
        
        self.active_game = True
        self.target_number = random.randint(1, 100)
        self.current_player = ctx.author.id
        self.guesses_left = self.max_guesses
        await ctx.send(f"✅ 遊戲開始！請猜一個 1-100 之間的數字，你有 {self.guesses_left} 次機會。")

    @game.command(name="guess")
    async def guess_number(self, ctx, number: int):
        if not self.active_game or self.current_player != ctx.author.id:
            await ctx.send("❌ 遊戲未開始或你不是當前玩家。")
            return
        
        self.guesses_left -= 1
        
        if number == self.target_number:
            score = self.max_guesses - self.guesses_left + 1
            current_score = self.get_score(ctx.author.id)
            new_score = max(current_score, score)
            self.save_score(ctx.author.id, new_score)
            await ctx.send(f"✅ 恭喜 {ctx.author.name} 猜對了！得分：{score}，最高分：{new_score}")
            self.active_game = False
        elif number < self.target_number:
            await ctx.send(f"⬆️ 太小了！剩餘 {self.guesses_left} 次機會。")
        else:
            await ctx.send(f"⬇️ 太大了！剩餘 {self.guesses_left} 次機會。")
        
        if self.guesses_left <= 0:
            await ctx.send(f"❌ 機會用盡，數字是 {self.target_number}。遊戲結束。")
            self.active_game = False

    @game.command(name="end")
    async def end_game(self, ctx):
        if not self.active_game or self.current_player != ctx.author.id:
            await ctx.send("❌ 無遊戲進行或你無權結束。")
            return
        
        await ctx.send(f"✅ 遊戲結束，數字是 {self.target_number}。")
        self.active_game = False

    @game.command(name="leaderboard")
    async def show_leaderboard(self, ctx):
        self.cursor.execute("SELECT user_id, username, score FROM game_scores ORDER BY score DESC LIMIT 10")
        scores = self.cursor.fetchall()
        if not scores:
            await ctx.send("❌ 目前無得分記錄。")
            return
        
        embed = discord.Embed(title="🏆 得分排行", color=discord.Color.gold())
        for user_id, username, score in scores:
            try:
                user = await self.bot.fetch_user(user_id)
                embed.add_field(name=user.name, value=f"{score} 分", inline=False)
            except:
                embed.add_field(name=f"未知用戶 ({username})", value=f"{score} 分", inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name="meme")
    async def meme_command(self, ctx, source: str = "reddit"):
        """獲取迷因命令 - 重命名避免衝突"""
        try:
            logger.info(f"處理 !meme 指令，來源: {source}")
            
            # 清理輸入
            source = source.lower().strip()
            if source not in ["reddit", "memeapi"]:
                await ctx.send("❌ 無效來源，請使用 'reddit' 或 'memeapi'。")
                return
            
            # 發送正在處理的訊息
            processing_msg = await ctx.send("🔄 正在獲取迷因...")
            
            # 獲取迷因
            meme = await self.fetch_meme_from_source(source)
            
            if meme and meme.get("url"):
                logger.info(f"成功獲取迷因: {meme['title']} - {meme['url']}")
                
                embed = discord.Embed(
                    title=meme["title"][:256],  # Discord 標題限制
                    color=discord.Color.green()
                )
                embed.set_image(url=meme["url"])
                embed.set_footer(text=f"來源: {meme.get('source', source)}")
                
                await processing_msg.edit(content="", embed=embed)
            else:
                logger.warning(f"無法獲取 {source} 迷因")
                await processing_msg.edit(content=f"❌ 無法從 {source} 獲取迷因，請稍後再試。")
                
        except Exception as e:
            logger.error(f"執行 !meme 時發生錯誤: {e}")
            await ctx.send(f"❌ 獲取迷因時發生錯誤: {str(e)}")

    def __del__(self):
        self.db.close()

async def setup(bot):
    await bot.add_cog(Game(bot))
    logger.info("✅ Game Cog 已載入")