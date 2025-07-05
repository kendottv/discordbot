import discord
from discord.ext import commands

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ping")
    async def ping(self, ctx):
        """回傳延遲時間"""
        await ctx.send(f'Ping! 延遲：{round(self.bot.latency * 1000)}ms')

    @commands.command(name="myhelp")
    async def myhelp(self, ctx):
        """顯示幫助訊息"""
        embed = discord.Embed(title="📌 幫助資訊", color=discord.Color.blue(), timestamp=discord.utils.utcnow())
        
        # 來自 Game Cog
        embed.add_field(
            name="來自 Game Cog",
            value="""
!game - 顯示遊戲模組的幫助訊息。
!game start - 啟動猜數字遊戲。
!game guess <number> - 猜測遊戲中的目標數字。
!game end - 結束當前遊戲。
!game leaderboard - 查看猜數字遊戲的得分排行榜。
!meme <source> - 獲取迷因圖片（來源可選 reddit 或 memeapi）。
            """,
            inline=False
        )

        # 來自 General Cog
        embed.add_field(
            name="來自 General Cog",
            value="""
!ping - 測試機器人延遲。
!myhelp - 顯示此幫助訊息。
!userinfo [@用戶] - 顯示使用者資訊。
!serverinfo - 顯示伺服器資訊。
            """,
            inline=False
        )

        # 來自 Level Cog
        embed.add_field(
            name="來自 Level Cog",
            value="""
!level / !lvl / !等級 - 查看自己的等級資訊。
!leaderboard / !lb / !排行榜 - 查看等級排行榜。
            """,
            inline=False
        )

        # 來自 Vote Cog
        embed.add_field(
            name="來自 Vote Cog",
            value="""
/createpoll - 創建一個新的投票（Slash Command）。
!poll - 創建投票的傳統命令格式。 (!poll "你喜歡哪種飲料?" 咖啡|茶|水)
/pollresult - 查看投票結果圖表（Slash Command）。
/listpolls - 列出所有活躍的投票（Slash Command）。
/deletepoll - 刪除投票（僅限創建者，Slash Command）。
            """,
            inline=False
        )

        # 來自 WeatherCog
        embed.add_field(
            name="來自 WeatherCog",
            value="""
!getweather [city] - 獲取指定城市的當前天氣（預設 Taipei）。
            """,
            inline=False
        )

        embed.set_footer(text=f"指令前綴: {ctx.prefix} | 由 {self.bot.user.name} 提供")
        await ctx.send(embed=embed)

    @commands.command(name="userinfo")
    async def userinfo(self, ctx, member: discord.Member = None):
        """顯示指定用戶的資訊（預設為自己）"""
        member = member or ctx.author
        embed = discord.Embed(title="👤 使用者資訊", color=discord.Color.blue())
        
        # 修正頭像處理
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        else:
            embed.set_thumbnail(url=member.default_avatar.url)
            
        embed.add_field(name="名稱", value=member.name, inline=True)
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(name="加入時間", value=member.joined_at.strftime("%Y/%m/%d %H:%M:%S"), inline=False)
        embed.add_field(name="身份組數", value=len(member.roles)-1, inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="serverinfo")
    async def serverinfo(self, ctx):
        """顯示伺服器的基本資訊"""
        guild = ctx.guild
        embed = discord.Embed(title="🏠 伺服器資訊", color=discord.Color.green())
        
        # 修正伺服器圖示處理
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
            
        embed.add_field(name="伺服器名稱", value=guild.name, inline=True)
        embed.add_field(name="擁有者", value=guild.owner, inline=True)
        embed.add_field(name="成員數", value=guild.member_count, inline=True)
        embed.add_field(name="創建日期", value=guild.created_at.strftime("%Y/%m/%d %H:%M:%S"), inline=False)
        await ctx.send(embed=embed)

# 新版 discord.py 的 setup 函數
async def setup(bot):
    await bot.add_cog(General(bot))
    print("✅ General Cog 已載入")