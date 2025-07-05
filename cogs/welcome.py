import discord
from discord.ext import commands
import json
import os

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_file = "config/welcome_config.json"
        self.config = self.load_config()

    def load_config(self):
        """載入歡迎設定"""
        # 確保設定資料夾存在
        os.makedirs("config", exist_ok=True)
        
        default_config = {
            "welcome_channel": None,
            "welcome_message": "🎉 歡迎 {member} 加入 **{server}**！\n希望你在這裡玩得開心！",
            "auto_role": None,
            "dm_welcome": False,
            "dm_message": "歡迎加入 {server}！請記得閱讀規則頻道。"
        }
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            # 確保所有預設值都存在
            for key, value in default_config.items():
                if key not in config:
                    config[key] = value
            return config
        except FileNotFoundError:
            # 如果檔案不存在，建立預設設定
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            return default_config

    def save_config(self):
        """儲存歡迎設定"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """新成員加入事件"""
        guild = member.guild
        
        # 自動給予角色
        if self.config["auto_role"]:
            try:
                role = guild.get_role(self.config["auto_role"])
                if role:
                    await member.add_roles(role)
                    print(f"✅ 已為 {member.name} 添加角色：{role.name}")
            except Exception as e:
                print(f"⚠️ 無法為 {member.name} 添加角色：{e}")

        # 發送歡迎訊息到指定頻道
        if self.config["welcome_channel"]:
            try:
                channel = guild.get_channel(self.config["welcome_channel"])
                if channel:
                    # 建立嵌入訊息
                    embed = discord.Embed(
                        title="🎉 新成員加入！",
                        description=self.config["welcome_message"].format(
                            member=member.mention, 
                            server=guild.name
                        ),
                        color=discord.Color.green()
                    )
                    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
                    embed.add_field(name="成員數", value=f"第 {guild.member_count} 位成員", inline=True)
                    embed.add_field(name="加入時間", value=member.joined_at.strftime("%Y/%m/%d %H:%M:%S"), inline=True)
                    embed.set_footer(text=f"ID: {member.id}")
                    
                    await channel.send(embed=embed)
            except Exception as e:
                print(f"⚠️ 無法發送歡迎訊息：{e}")

        # 發送私訊歡迎訊息
        if self.config["dm_welcome"]:
            try:
                await member.send(self.config["dm_message"].format(server=guild.name))
            except discord.Forbidden:
                print(f"⚠️ 無法發送私訊給 {member.name}（可能關閉了私訊）")

    @commands.group(name="welcome", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def welcome(self, ctx):
        """歡迎系統設定"""
        embed = discord.Embed(title="🎉 歡迎系統設定", color=discord.Color.blue())
        
        # 顯示目前設定
        channel = ctx.guild.get_channel(self.config["welcome_channel"]) if self.config["welcome_channel"] else None
        role = ctx.guild.get_role(self.config["auto_role"]) if self.config["auto_role"] else None
        
        embed.add_field(name="歡迎頻道", value=channel.mention if channel else "未設定", inline=True)
        embed.add_field(name="自動角色", value=role.mention if role else "未設定", inline=True)
        embed.add_field(name="私訊歡迎", value="✅ 開啟" if self.config["dm_welcome"] else "❌ 關閉", inline=True)
        embed.add_field(name="歡迎訊息", value=self.config["welcome_message"], inline=False)
        
        embed.add_field(name="可用指令", value="""
        `!welcome channel <#頻道>` - 設定歡迎頻道
        `!welcome role <@角色>` - 設定自動角色
        `!welcome message <訊息>` - 設定歡迎訊息
        `!welcome dm <on/off>` - 開啟/關閉私訊歡迎
        `!welcome test` - 測試歡迎訊息
        """, inline=False)
        
        await ctx.send(embed=embed)

    @welcome.command(name="channel")
    @commands.has_permissions(manage_guild=True)
    async def set_welcome_channel(self, ctx, channel: discord.TextChannel = None):
        """設定歡迎頻道"""
        if channel is None:
            self.config["welcome_channel"] = None
            await ctx.send("❌ 已取消設定歡迎頻道")
        else:
            self.config["welcome_channel"] = channel.id
            await ctx.send(f"✅ 已設定歡迎頻道為：{channel.mention}")
        
        self.save_config()

    @welcome.command(name="role")
    @commands.has_permissions(manage_guild=True)
    async def set_auto_role(self, ctx, role: discord.Role = None):
        """設定自動角色"""
        if role is None:
            self.config["auto_role"] = None
            await ctx.send("❌ 已取消設定自動角色")
        else:
            self.config["auto_role"] = role.id
            await ctx.send(f"✅ 已設定自動角色為：{role.mention}")
        
        self.save_config()

    @welcome.command(name="message")
    @commands.has_permissions(manage_guild=True)
    async def set_welcome_message(self, ctx, *, message):
        """設定歡迎訊息"""
        self.config["welcome_message"] = message
        self.save_config()
        
        embed = discord.Embed(title="✅ 歡迎訊息已更新", color=discord.Color.green())
        embed.add_field(name="新訊息", value=message, inline=False)
        embed.add_field(name="可用變數", value="`{member}` - 提及新成員\n`{server}` - 伺服器名稱", inline=False)
        
        await ctx.send(embed=embed)

    @welcome.command(name="dm")
    @commands.has_permissions(manage_guild=True)
    async def set_dm_welcome(self, ctx, status: str):
        """開啟/關閉私訊歡迎"""
        if status.lower() in ["on", "開啟", "true", "1"]:
            self.config["dm_welcome"] = True
            await ctx.send("✅ 已開啟私訊歡迎功能")
        elif status.lower() in ["off", "關閉", "false", "0"]:
            self.config["dm_welcome"] = False
            await ctx.send("❌ 已關閉私訊歡迎功能")
        else:
            await ctx.send("❌ 請使用 `on` 或 `off`")
            return
        
        self.save_config()

    @welcome.command(name="test")
    @commands.has_permissions(manage_guild=True)
    async def test_welcome(self, ctx):
        """測試歡迎訊息"""
        member = ctx.author
        guild = ctx.guild
        
        if not self.config["welcome_channel"]:
            await ctx.send("❌ 請先設定歡迎頻道")
            return
        
        channel = guild.get_channel(self.config["welcome_channel"])
        if not channel:
            await ctx.send("❌ 找不到設定的歡迎頻道")
            return
        
        # 建立測試嵌入訊息
        embed = discord.Embed(
            title="🧪 測試歡迎訊息",
            description=self.config["welcome_message"].format(
                member=member.mention, 
                server=guild.name
            ),
            color=discord.Color.orange()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.add_field(name="成員數", value=f"第 {guild.member_count} 位成員", inline=True)
        embed.add_field(name="加入時間", value="測試時間", inline=True)
        embed.set_footer(text=f"ID: {member.id} | 這是測試訊息")
        
        await channel.send(embed=embed)
        await ctx.send(f"✅ 測試訊息已發送到 {channel.mention}")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """成員離開事件（可選）"""
        if self.config["welcome_channel"]:
            try:
                channel = member.guild.get_channel(self.config["welcome_channel"])
                if channel:
                    embed = discord.Embed(
                        title="👋 成員離開",
                        description=f"{member.name} 離開了伺服器",
                        color=discord.Color.red()
                    )
                    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
                    embed.add_field(name="剩餘成員數", value=f"{member.guild.member_count} 位成員", inline=True)
                    embed.set_footer(text=f"ID: {member.id}")
                    
                    await channel.send(embed=embed)
            except Exception as e:
                print(f"⚠️ 無法發送離開訊息：{e}")

async def setup(bot):
    await bot.add_cog(Welcome(bot))
    print("✅ Welcome Cog 已載入")