import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# 讀取 .env 中的變數
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("COMMAND_PREFIX", "!")

# 設定 Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # 為了 on_member_join 事件與會員資訊

# 建立 Bot 實例
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# 使用簡易 help 指令（自動列出所有 Cog 的指令）
from discord.ext.commands import MinimalHelpCommand
bot.help_command = MinimalHelpCommand()

# Bot 上線提示
@bot.event
async def on_ready():
    print(f"✅ {bot.user} 已上線！")
    print(f"🔹 指令前綴：{PREFIX}")
    print(f"🔹 已載入的 Cogs：{list(bot.cogs.keys())}")

# 錯誤處理（避免重複觸發）
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f"❌ 找不到指令：`{ctx.invoked_with}`")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ 你沒有執行此指令的權限")
    else:
        print(f"指令錯誤：{error}")
        # 避免回送訊息以防止循環
        if not hasattr(ctx, "error_handled"):
            ctx.error_handled = True
        else:
            return  # 若已處理過，中止

# 自動載入所有 cogs 下的模組
async def load_all_cogs():
    cogs_path = "./cogs"
    if not os.path.exists(cogs_path):
        print(f"⚠️ 找不到 cogs 資料夾：{cogs_path}")
        return
    
    for filename in os.listdir(cogs_path):
        if filename.endswith(".py") and not filename.startswith("_"):
            cog_name = f"cogs.{filename[:-3]}"
            try:
                await bot.load_extension(cog_name)
                print(f"🔹 成功載入模組：{filename} ({cog_name})")
            except Exception as e:
                print(f"⚠️ 載入 {filename} ({cog_name}) 時發生錯誤：{e}")

# 主程式
async def main():
    async with bot:
        await load_all_cogs()
        await bot.start(TOKEN)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())