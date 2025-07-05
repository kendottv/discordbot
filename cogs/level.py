import discord
from discord.ext import commands
import json
import os
import random
import math
from datetime import datetime, timedelta

class Level(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = "data/level_data.json"
        self.config_file = "config/level_config.json"
        self.user_data = self.load_user_data()
        self.config = self.load_config()
        self.cooldowns = {}  # 防止刷經驗

    def load_user_data(self):
        """載入使用者等級資料"""
        os.makedirs("data", exist_ok=True)
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_user_data(self):
        """儲存使用者等級資料"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.user_data, f, ensure_ascii=False, indent=2)

    def load_config(self):
        """載入等級系統設定"""
        os.makedirs("config", exist_ok=True)
        default_config = {
            "enabled": True,
            "xp_per_message": [15, 25],  # 每則訊息獲得的經驗範圍
            "cooldown_seconds": 60,      # 獲得經驗的冷卻時間（秒）
            "level_up_channel": None,    # 升級通知頻道
            "level_up_message": "🎉 恭喜 {member} 升級到 **等級 {level}**！",
            "level_roles": {},           # 等級角色獎勵 {"等級": "角色ID"}
            "blacklist_channels": []     # 不計算經驗的頻道
        }
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            for key, value in default_config.items():
                if key not in config:
                    config[key] = value
            return config
        except FileNotFoundError:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            return default_config

    def save_config(self):
        """儲存等級系統設定"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def get_level_from_xp(self, xp):
        """根據經驗值計算等級"""
        # 使用公式：等級 = sqrt(經驗值 / 100)
        return int(math.sqrt(xp / 100))

    def get_xp_for_level(self, level):
        """計算達到指定等級需要的經驗值"""
        return level * level * 100

    def get_user_data(self, user_id):
        """獲取使用者資料"""
        user_id = str(user_id)
        if user_id not in self.user_data:
            self.user_data[user_id] = {
                "xp": 0,
                "level": 0,
                "total_messages": 0,
                "last_message": None
            }
        return self.user_data[user_id]

    @commands.Cog.listener()
    async def on_message(self, message):
        """訊息事件 - 計算經驗值"""
        # 忽略機器人訊息
        if message.author.bot:
            return
        
        # 檢查系統是否啟用
        if not self.config["enabled"]:
            return
        
        # 檢查是否在黑名單頻道
        if message.channel.id in self.config["blacklist_channels"]:
            return
        
        # 檢查冷卻時間
        user_id = str(message.author.id)
        now = datetime.now()
        
        if user_id in self.cooldowns:
            time_diff = (now - self.cooldowns[user_id]).total_seconds()
            if time_diff < self.config["cooldown_seconds"]:
                return
        
        # 更新冷卻時間
        self.cooldowns[user_id] = now
        
        # 獲取使用者資料
        user_data = self.get_user_data(message.author.id)
        
        # 計算獲得的經驗值
        xp_gain = random.randint(self.config["xp_per_message"][0], self.config["xp_per_message"][1])
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
        self.save_user_data()

    async def handle_level_up(self, member, guild, new_level):
        """處理升級事件"""
        # 發送升級通知
        if self.config["level_up_channel"]:
            try:
                channel = guild.get_channel(self.config["level_up_channel"])
                if channel:
                    embed = discord.Embed(
                        title="🎉 等級提升！",
                        description=self.config["level_up_message"].format(
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
        if str(new_level) in self.config["level_roles"]:
            try:
                role_id = self.config["level_roles"][str(new_level)]
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
        
        # 排序使用者資料
        sorted_users = sorted(
            [(user_id, data) for user_id, data in self.user_data.items()],
            key=lambda x: x[1]["xp"],
            reverse=True
        )
        
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
        for i, (user_id, data) in enumerate(page_users, start + 1):
            try:
                user = self.bot.get_user(int(user_id))
                if user:
                    # 排名圖示
                    rank_icon = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🔹"
                    description += f"{rank_icon} **#{i}** {user.display_name}\n"
                    description += f"   等級 {data['level']} | {data['xp']:,} XP\n\n"
            except:
                continue
        
        embed.description = description
        embed.set_footer(text=f"第 {page} 頁 | 總共 {len(sorted_users)} 位使用者")
        
        await ctx.send(embed=embed)

    @commands.group(name="levelconfig", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def level_config(self, ctx):
        """等級系統設定"""
        embed = discord.Embed(title="⚙️ 等級系統設定", color=discord.Color.blue())
        
        # 顯示目前設定
        channel = ctx.guild.get_channel(self.config["level_up_channel"]) if self.config["level_up_channel"] else None
        
        embed.add_field(name="系統狀態", value="✅ 啟用" if self.config["enabled"] else "❌ 停用", inline=True)
        embed.add_field(name="升級通知頻道", value=channel.mention if channel else "未設定", inline=True)
        embed.add_field(name="經驗值範圍", value=f"{self.config['xp_per_message'][0]}-{self.config['xp_per_message'][1]} XP", inline=True)
        embed.add_field(name="冷卻時間", value=f"{self.config['cooldown_seconds']} 秒", inline=True)
        embed.add_field(name="黑名單頻道", value=f"{len(self.config['blacklist_channels'])} 個", inline=True)
        embed.add_field(name="等級角色", value=f"{len(self.config['level_roles'])} 個", inline=True)
        
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
        self.config["enabled"] = not self.config["enabled"]
        self.save_config()
        
        status = "✅ 啟用" if self.config["enabled"] else "❌ 停用"
        await ctx.send(f"等級系統已{status}")

    @level_config.command(name="channel")
    @commands.has_permissions(manage_guild=True)
    async def set_level_channel(self, ctx, channel: discord.TextChannel = None):
        """設定升級通知頻道"""
        if channel is None:
            self.config["level_up_channel"] = None
            await ctx.send("❌ 已取消設定升級通知頻道")
        else:
            self.config["level_up_channel"] = channel.id
            await ctx.send(f"✅ 已設定升級通知頻道為：{channel.mention}")
        
        self.save_config()

    @level_config.command(name="xp")
    @commands.has_permissions(manage_guild=True)
    async def set_xp_range(self, ctx, min_xp: int, max_xp: int):
        """設定經驗值範圍"""
        if min_xp > max_xp or min_xp < 1:
            await ctx.send("❌ 經驗值範圍設定錯誤")
            return
        
        self.config["xp_per_message"] = [min_xp, max_xp]
        self.save_config()
        
        await ctx.send(f"✅ 已設定經驗值範圍為：{min_xp}-{max_xp} XP")

    @level_config.command(name="cooldown")
    @commands.has_permissions(manage_guild=True)
    async def set_cooldown(self, ctx, seconds: int):
        """設定冷卻時間"""
        if seconds < 0:
            await ctx.send("❌ 冷卻時間不能為負數")
            return
        
        self.config["cooldown_seconds"] = seconds
        self.save_config()
        
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
        
        self.save_user_data()
        
        # 檢查是否升級
        if new_level > old_level:
            await self.handle_level_up(member, ctx.guild, new_level)
        
        action = "給予" if amount > 0 else "扣除"
        await ctx.send(f"✅ 已{action} {member.display_name} {abs(amount)} 經驗值")

async def setup(bot):
    await bot.add_cog(Level(bot))
    print("✅ Level Cog 已載入")