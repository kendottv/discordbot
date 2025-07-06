import discord
from discord.ext import commands
import os
import random
import math
from datetime import datetime, timedelta
import sqlite3

class Level(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = sqlite3.connect("bot_data.db", check_same_thread=False)
        self.cursor = self.db.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS level_data (
                user_id INTEGER PRIMARY KEY,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 0,
                total_messages INTEGER DEFAULT 0,
                last_message TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS level_config (
                guild_id INTEGER PRIMARY KEY,
                enabled INTEGER DEFAULT 1,
                xp_per_message TEXT,
                cooldown_seconds INTEGER DEFAULT 60,
                level_up_channel INTEGER,
                level_up_message TEXT,
                level_roles TEXT,
                blacklist_channels TEXT
            )
        """)
        self.db.commit()
        self.cooldowns = {}  # 防止刷經驗

    def get_user_data(self, user_id):
        """獲取使用者資料"""
        self.cursor.execute("SELECT * FROM level_data WHERE user_id = ?", (user_id,))
        row = self.cursor.fetchone()
        if row:
            return {
                "xp": row[1],
                "level": row[2],
                "total_messages": row[3],
                "last_message": row[4]
            }
        return {"xp": 0, "level": 0, "total_messages": 0, "last_message": None}

    def save_user_data(self, user_id, data):
        """儲存使用者等級資料"""
        self.cursor.execute("""
            INSERT OR REPLACE INTO level_data (user_id, xp, level, total_messages, last_message)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, data["xp"], data["level"], data["total_messages"], data["last_message"]))
        self.db.commit()

    def get_level_config(self, guild_id):
        """獲取等級系統設定"""
        self.cursor.execute("SELECT * FROM level_config WHERE guild_id = ?", (guild_id,))
        result = self.cursor.fetchone()
        default_config = {
            "enabled": True,
            "xp_per_message": [15, 25],
            "cooldown_seconds": 60,
            "level_up_channel": None,
            "level_up_message": "🎉 恭喜 {member} 升級到 **等級 {level}**！",
            "level_roles": {},
            "blacklist_channels": []
        }
        if result:
            return {
                "enabled": bool(result[1]),
                "xp_per_message": eval(result[2]) if result[2] else default_config["xp_per_message"],
                "cooldown_seconds": result[3] if result[3] else default_config["cooldown_seconds"],
                "level_up_channel": result[4],
                "level_up_message": result[5] if result[5] else default_config["level_up_message"],
                "level_roles": eval(result[6]) if result[6] else default_config["level_roles"],
                "blacklist_channels": eval(result[7]) if result[7] else default_config["blacklist_channels"]
            }
        return default_config

    def save_level_config(self, guild_id, config):
        """儲存等級系統設定"""
        self.cursor.execute("""
            INSERT OR REPLACE INTO level_config (guild_id, enabled, xp_per_message, cooldown_seconds, level_up_channel, level_up_message, level_roles, blacklist_channels)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (guild_id, 1 if config.get("enabled") else 0, str(config.get("xp_per_message", [15, 25])),
              config.get("cooldown_seconds", 60), config.get("level_up_channel"),
              config.get("level_up_message", "🎉 恭喜 {member} 升級到 **等級 {level}**！"),
              str(config.get("level_roles", {})), str(config.get("blacklist_channels", []))))
        self.db.commit()

    def get_level_from_xp(self, xp):
        """根據經驗值計算等級"""
        return int(math.sqrt(xp / 100))

    def get_xp_for_level(self, level):
        """計算達到指定等級需要的經驗值"""
        return level * level * 100

    @commands.Cog.listener()
    async def on_message(self, message):
        """訊息事件 - 計算經驗值"""
        # 忽略機器人訊息
        if message.author.bot:
            return
        
        # 檢查系統是否啟用
        config = self.get_level_config(message.guild.id)
        if not config["enabled"]:
            return
        
        # 檢查是否在黑名單頻道
        if message.channel.id in config["blacklist_channels"]:
            return
        
        # 檢查冷卻時間
        user_id = message.author.id
        now = datetime.now()
        
        if user_id in self.cooldowns:
            time_diff = (now - self.cooldowns[user_id]).total_seconds()
            if time_diff < config["cooldown_seconds"]:
                return
        
        # 更新冷卻時間
        self.cooldowns[user_id] = now
        
        # 獲取使用者資料
        user_data = self.get_user_data(user_id)
        
        # 計算獲得的經驗值
        xp_gain = random.randint(config["xp_per_message"][0], config["xp_per_message"][1])
        old_level = user_data["level"]
        
        # 更新資料
        user_data["xp"] += xp_gain
        user_data["total_messages"] += 1
        user_data["last_message"] = now.isoformat()
        
        # 計算新等級
        new_level = self.get_level_from_xp(user_data["xp"])
        user_data["level"] = new_level
        
        # 檢查是否升級
        if new_level > old_level:
            await self.handle_level_up(message.author, message.guild, new_level)
        
        # 儲存資料
        self.save_user_data(user_id, user_data)

    async def handle_level_up(self, member, guild, new_level):
        """處理升級事件"""
        config = self.get_level_config(guild.id)
        # 發送升級通知
        if config["level_up_channel"]:
            try:
                channel = guild.get_channel(config["level_up_channel"])
                if channel:
                    embed = discord.Embed(
                        title="🎉 等級提升！",
                        description=config["level_up_message"].format(
                            member=member.mention,
                            level=new_level
                        ),
                        color=discord.Color.gold()
                    )
                    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
                    embed.add_field(name="新等級", value=f"等級 {new_level}", inline=True)
                    embed.add_field(name="下一等級需要", value=f"{self.get_xp_for_level(new_level + 1) - self.get_user_data(member.id)['xp']} XP", inline=True)
                    
                    await channel.send(embed=embed)
            except Exception as e:
                print(f"⚠️ 無法發送升級通知：{e}")
        
        # 檢查等級角色獎勵
        if str(new_level) in config["level_roles"]:
            try:
                role_id = config["level_roles"][str(new_level)]
                role = guild.get_role(role_id)
                if role:
                    await member.add_roles(role)
                    print(f"✅ 已為 {member.name} 添加等級 {new_level} 獎勵角色：{role.name}")
            except Exception as e:
                print(f"⚠️ 無法添加等級角色：{e}")

    @commands.command(name="level", aliases=["lvl", "等級"])
    async def check_level(self, ctx, member: discord.Member = None):
        """查看等級資訊"""
        member = member or ctx.author
        user_data = self.get_user_data(member.id)
        
        current_level = user_data["level"]
        current_xp = user_data["xp"]
        next_level_xp = self.get_xp_for_level(current_level + 1)
        current_level_xp = self.get_xp_for_level(current_level)
        
        # 計算進度條
        progress = (current_xp - current_level_xp) / (next_level_xp - current_level_xp)
        progress_bar = "█" * int(progress * 20) + "░" * (20 - int(progress * 20))
        
        embed = discord.Embed(
            title=f"📊 {member.display_name} 的等級資訊",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        
        embed.add_field(name="目前等級", value=f"**等級 {current_level}**", inline=True)
        embed.add_field(name="總經驗值", value=f"{current_xp:,} XP", inline=True)
        embed.add_field(name="總訊息數", value=f"{user_data['total_messages']:,}", inline=True)
        
        embed.add_field(name="升級進度", value=f"""
        {progress_bar}
        {current_xp - current_level_xp:,} / {next_level_xp - current_level_xp:,} XP
        ({progress:.1%})
        """, inline=False)
        
        embed.add_field(name="距離下一等級", value=f"{next_level_xp - current_xp:,} XP", inline=True)
        
        if user_data["last_message"]:
            last_msg = datetime.fromisoformat(user_data["last_message"])
            embed.add_field(name="最後活動", value=f"<t:{int(last_msg.timestamp())}:R>", inline=True)
        
        await ctx.send(embed=embed)

    @commands.command(name="leaderboard", aliases=["lb", "排行榜"])
    async def leaderboard(self, ctx, page: int = 1):
        """查看等級排行榜"""
        if page < 1:
            page = 1
        
        # 從資料庫獲取所有使用者資料
        self.cursor.execute("SELECT user_id, xp, level, total_messages FROM level_data ORDER BY xp DESC")
        sorted_users = self.cursor.fetchall()
        
        # 分頁
        per_page = 10
        start = (page - 1) * per_page
        end = start + per_page
        page_users = sorted_users[start:end]
        
        if not page_users:
            await ctx.send("❌ 這一頁沒有資料")
            return
        
        embed = discord.Embed(
            title="🏆 等級排行榜",
            color=discord.Color.gold()
        )
        
        description = ""
        for i, (user_id, xp, level, total_messages) in enumerate(page_users, start + 1):
            try:
                user = self.bot.get_user(user_id)
                if user:
                    # 排名圖示
                    rank_icon = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🔹"
                    description += f"{rank_icon} **#{i}** {user.display_name}\n"
                    description += f"   等級 {level} | {xp:,} XP\n\n"
            except:
                continue
        
        embed.description = description
        embed.set_footer(text=f"第 {page} 頁 | 總共 {len(sorted_users)} 位使用者")
        
        await ctx.send(embed=embed)

    @commands.group(name="levelconfig", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def level_config(self, ctx):
        """等級系統設定"""
        config = self.get_level_config(ctx.guild.id)
        embed = discord.Embed(title="⚙️ 等級系統設定", color=discord.Color.blue())
        
        # 顯示目前設定
        channel = ctx.guild.get_channel(config["level_up_channel"]) if config["level_up_channel"] else None
        
        embed.add_field(name="系統狀態", value="✅ 啟用" if config["enabled"] else "❌ 停用", inline=True)
        embed.add_field(name="升級通知頻道", value=channel.mention if channel else "未設定", inline=True)
        embed.add_field(name="經驗值範圍", value=f"{config['xp_per_message'][0]}-{config['xp_per_message'][1]} XP", inline=True)
        embed.add_field(name="冷卻時間", value=f"{config['cooldown_seconds']} 秒", inline=True)
        embed.add_field(name="黑名單頻道", value=f"{len(config['blacklist_channels'])} 個", inline=True)
        embed.add_field(name="等級角色", value=f"{len(config['level_roles'])} 個", inline=True)
        
        embed.add_field(name="可用指令", value="""
        `!levelconfig toggle` - 開關等級系統
        `!levelconfig channel <#頻道>` - 設定升級通知頻道
        `!levelconfig xp <最小值> <最大值>` - 設定經驗值範圍
        `!levelconfig cooldown <秒數>` - 設定冷卻時間
        `!levelconfig blacklist <#頻道>` - 添加/移除黑名單頻道
        `!levelconfig role <等級> <@角色>` - 設定等級角色
        """, inline=False)
        
        await ctx.send(embed=embed)

    @level_config.command(name="toggle")
    @commands.has_permissions(manage_guild=True)
    async def toggle_level_system(self, ctx):
        """開關等級系統"""
        config = self.get_level_config(ctx.guild.id)
        config["enabled"] = not config["enabled"]
        self.save_level_config(ctx.guild.id, config)
        
        status = "✅ 啟用" if config["enabled"] else "❌ 停用"
        await ctx.send(f"等級系統已{status}")

    @level_config.command(name="channel")
    @commands.has_permissions(manage_guild=True)
    async def set_level_channel(self, ctx, channel: discord.TextChannel = None):
        """設定升級通知頻道"""
        config = self.get_level_config(ctx.guild.id)
        if channel is None:
            config["level_up_channel"] = None
            await ctx.send("❌ 已取消設定升級通知頻道")
        else:
            config["level_up_channel"] = channel.id
            await ctx.send(f"✅ 已設定升級通知頻道為：{channel.mention}")
        
        self.save_level_config(ctx.guild.id, config)

    @level_config.command(name="xp")
    @commands.has_permissions(manage_guild=True)
    async def set_xp_range(self, ctx, min_xp: int, max_xp: int):
        """設定經驗值範圍"""
        config = self.get_level_config(ctx.guild.id)
        if min_xp > max_xp or min_xp < 1:
            await ctx.send("❌ 經驗值範圍設定錯誤")
            return
        
        config["xp_per_message"] = [min_xp, max_xp]
        self.save_level_config(ctx.guild.id, config)
        
        await ctx.send(f"✅ 已設定經驗值範圍為：{min_xp}-{max_xp} XP")

    @level_config.command(name="cooldown")
    @commands.has_permissions(manage_guild=True)
    async def set_cooldown(self, ctx, seconds: int):
        """設定冷卻時間"""
        config = self.get_level_config(ctx.guild.id)
        if seconds < 0:
            await ctx.send("❌ 冷卻時間不能為負數")
            return
        
        config["cooldown_seconds"] = seconds
        self.save_level_config(ctx.guild.id, config)
        
        await ctx.send(f"✅ 已設定冷卻時間為：{seconds} 秒")

    @commands.command(name="givexp")
    @commands.has_permissions(manage_guild=True)
    async def give_xp(self, ctx, member: discord.Member, amount: int):
        """給予經驗值（管理員指令）"""
        if amount == 0:
            await ctx.send("❌ 經驗值不能為0")
            return
        
        user_data = self.get_user_data(member.id)
        old_level = user_data["level"]
        
        user_data["xp"] += amount
        if user_data["xp"] < 0:
            user_data["xp"] = 0
        
        new_level = self.get_level_from_xp(user_data["xp"])
        user_data["level"] = new_level
        
        self.save_user_data(member.id, user_data)
        
        # 檢查是否升級
        if new_level > old_level:
            await self.handle_level_up(member, ctx.guild, new_level)
        
        action = "給予" if amount > 0 else "扣除"
        await ctx.send(f"✅ 已{action} {member.display_name} {abs(amount)} 經驗值")

    def __del__(self):
        self.db.close()

async def setup(bot):
    await bot.add_cog(Level(bot))
    print("✅ Level Cog 已載入")