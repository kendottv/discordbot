import discord
from discord.ext import commands
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import io
import asyncio
from datetime import datetime
import json

# 設置中文字體
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 儲存投票資料
polls = {}

class PollView(discord.ui.View):
    def __init__(self, poll_id):
        super().__init__(timeout=None)
        self.poll_id = poll_id
        
        # 動態添加投票按鈕
        poll = polls.get(poll_id)
        if poll:
            emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
            
            for i, option in enumerate(poll['options']):
                button = VoteButton(poll_id, i, option['text'], emojis[i])
                self.add_item(button)
    
    @discord.ui.button(label='查看結果圖表', style=discord.ButtonStyle.success, emoji='📈')
    async def show_results(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        poll = polls.get(self.poll_id)
        if not poll:
            await interaction.followup.send("❌ 找不到該投票！", ephemeral=True)
            return
        
        try:
            chart_buffer = await create_vote_chart(poll)
            file = discord.File(chart_buffer, filename='poll_result.png')
            await interaction.followup.send(file=file, ephemeral=True)
        except Exception as e:
            print(f"創建圖表時出錯: {e}")
            await interaction.followup.send("❌ 創建圖表時出錯！", ephemeral=True)
    
    @discord.ui.button(label='結束投票', style=discord.ButtonStyle.danger, emoji='🔒')
    async def close_poll(self, interaction: discord.Interaction, button: discord.ui.Button):
        poll = polls.get(self.poll_id)
        if not poll:
            await interaction.response.send_message("❌ 找不到該投票！", ephemeral=True)
            return
        
        if interaction.user.id != poll['creator_id']:
            await interaction.response.send_message("❌ 只有投票創建者可以結束投票！", ephemeral=True)
            return
        
        poll['active'] = False
        
        embed = create_poll_embed(poll)
        embed.title = "🔒 投票已結束"
        embed.color = discord.Color.red()
        
        try:
            chart_buffer = await create_vote_chart(poll)
            file = discord.File(chart_buffer, filename='final_result.png')
            await interaction.response.edit_message(embed=embed, view=None, attachments=[file])
        except Exception as e:
            print(f"創建最終圖表時出錯: {e}")
            await interaction.response.edit_message(embed=embed, view=None)

class VoteButton(discord.ui.Button):
    def __init__(self, poll_id, option_index, option_text, emoji):
        super().__init__(
            label=option_text,
            style=discord.ButtonStyle.primary,
            emoji=emoji,
            custom_id=f"vote_{poll_id}_{option_index}"
        )
        self.poll_id = poll_id
        self.option_index = option_index
    
    async def callback(self, interaction: discord.Interaction):
        poll = polls.get(self.poll_id)
        if not poll:
            await interaction.response.send_message("❌ 投票已不存在！", ephemeral=True)
            return
        
        if not poll['active']:
            await interaction.response.send_message("❌ 投票已結束！", ephemeral=True)
            return
        
        user_id = interaction.user.id
        if user_id in poll['voters']:
            await interaction.response.send_message("❌ 您已經投過票了！", ephemeral=True)
            return
        
        # 記錄投票
        poll['options'][self.option_index]['votes'] += 1
        poll['voters'].add(user_id)
        
        # 更新嵌入消息
        embed = create_poll_embed(poll)
        await interaction.response.edit_message(embed=embed, view=self.view)
        
        # 發送確認消息
        await interaction.followup.send(
            f"✅ 投票成功！您選擇了: {poll['options'][self.option_index]['text']}", 
            ephemeral=True
        )

def create_poll_embed(poll):
    embed = discord.Embed(
        title=f"📊 {poll['question']}", 
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
    
    for i, option in enumerate(poll['options']):
        embed.add_field(
            name=f"{emojis[i]} {option['text']}", 
            value=f"投票數: {option['votes']}", 
            inline=True
        )
    
    embed.set_footer(text=f"投票 ID: {poll['id']} | 創建者: {poll['creator']}")
    return embed

async def create_vote_chart(poll):
    # 創建圖表
    fig, ax = plt.subplots(figsize=(12, 8))
    fig.patch.set_facecolor('#2C2F33')
    ax.set_facecolor('#2C2F33')
    
    # 獲取數據
    options = [opt['text'] for opt in poll['options']]
    votes = [opt['votes'] for opt in poll['options']]
    total_votes = sum(votes)
    
    if total_votes == 0:
        # 如果沒有投票，顯示空圖表
        ax.text(0.5, 0.5, '尚無投票', ha='center', va='center', 
                transform=ax.transAxes, color='white', fontsize=20)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xticks([])
        ax.set_yticks([])
    else:
        # 創建橫向長條圖
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', 
                  '#DDA0DD', '#98D8C8', '#F7DC6F', '#AED6F1', '#F8C471']
        
        bars = ax.barh(range(len(options)), votes, color=colors[:len(options)])
        
        # 設置標籤
        ax.set_yticks(range(len(options)))
        ax.set_yticklabels(options, color='white')
        ax.set_xlabel('投票數', color='white')
        
        # 在長條上顯示數值和百分比
        for i, (bar, vote) in enumerate(zip(bars, votes)):
            width = bar.get_width()
            percentage = (vote / total_votes) * 100 if total_votes > 0 else 0
            ax.text(width + max(votes) * 0.01, bar.get_y() + bar.get_height()/2,
                   f'{vote} ({percentage:.1f}%)', 
                   va='center', color='white', fontweight='bold')
        
        # 設置刻度顏色
        ax.tick_params(colors='white')
        ax.spines['bottom'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
    
    # 設置標題
    plt.title(poll['question'], color='white', fontsize=16, pad=20)
    plt.figtext(0.5, 0.02, f'總投票數: {total_votes}', ha='center', color='#99AAB5')
    
    # 調整佈局
    plt.tight_layout()
    
    # 保存到 BytesIO
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', facecolor='#2C2F33', dpi=150)
    buffer.seek(0)
    plt.close()
    
    return buffer

class Vote(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        print(f'投票系統已載入')
    
    @discord.app_commands.command(name="createpoll", description="創建一個新的投票")
    @discord.app_commands.describe(
        question="投票問題",
        options="投票選項 (用 | 分隔，最多10個)"
    )
    async def create_poll(self, interaction: discord.Interaction, question: str, options: str):
        options_list = [opt.strip() for opt in options.split('|') if opt.strip()]
        
        if len(options_list) < 2:
            await interaction.response.send_message("❌ 至少需要2個選項！", ephemeral=True)
            return
        
        if len(options_list) > 10:
            await interaction.response.send_message("❌ 最多只能有10個選項！", ephemeral=True)
            return
        
        poll_id = str(int(datetime.now().timestamp()))
        poll = {
            'id': poll_id,
            'question': question,
            'options': [{'text': opt, 'votes': 0} for opt in options_list],
            'voters': set(),
            'creator': interaction.user.display_name,
            'creator_id': interaction.user.id,
            'active': True
        }
        
        polls[poll_id] = poll
        
        embed = create_poll_embed(poll)
        view = PollView(poll_id)
        
        await interaction.response.send_message(embed=embed, view=view)
    
    @discord.app_commands.command(name="pollresult", description="查看投票結果圖表")
    @discord.app_commands.describe(poll_id="投票 ID")
    async def poll_result(self, interaction: discord.Interaction, poll_id: str):
        poll = polls.get(poll_id)
        if not poll:
            await interaction.response.send_message("❌ 找不到該投票！", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            chart_buffer = await create_vote_chart(poll)
            file = discord.File(chart_buffer, filename='poll_result.png')
            await interaction.followup.send(file=file)
        except Exception as e:
            print(f"創建圖表時出錯: {e}")
            await interaction.followup.send("❌ 創建圖表時出錯！", ephemeral=True)
    
    @discord.app_commands.command(name="listpolls", description="列出所有活躍的投票")
    async def list_polls(self, interaction: discord.Interaction):
        active_polls = [poll for poll in polls.values() if poll['active']]
        
        if not active_polls:
            await interaction.response.send_message("目前沒有活躍的投票。", ephemeral=True)
            return
        
        embed = discord.Embed(title="📋 活躍投票列表", color=discord.Color.green())
        
        for poll in active_polls:
            total_votes = sum(opt['votes'] for opt in poll['options'])
            embed.add_field(
                name=f"ID: {poll['id']}", 
                value=f"問題: {poll['question']}\n總投票數: {total_votes}\n創建者: {poll['creator']}", 
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.app_commands.command(name="deletepoll", description="刪除投票 (僅創建者)")
    @discord.app_commands.describe(poll_id="投票 ID")
    async def delete_poll(self, interaction: discord.Interaction, poll_id: str):
        poll = polls.get(poll_id)
        if not poll:
            await interaction.response.send_message("❌ 找不到該投票！", ephemeral=True)
            return
        
        if interaction.user.id != poll['creator_id']:
            await interaction.response.send_message("❌ 只有投票創建者可以刪除投票！", ephemeral=True)
            return
        
        del polls[poll_id]
        await interaction.response.send_message(f"✅ 投票 {poll_id} 已被刪除！", ephemeral=True)
    
    # 傳統命令支援 (可選)
    @commands.command(name="poll")
    async def poll_command(self, ctx, question: str, *, options: str):
        """創建投票的傳統命令格式"""
        options_list = [opt.strip() for opt in options.split('|') if opt.strip()]
        
        if len(options_list) < 2:
            await ctx.send("❌ 至少需要2個選項！")
            return
        
        if len(options_list) > 10:
            await ctx.send("❌ 最多只能有10個選項！")
            return
        
        poll_id = str(int(datetime.now().timestamp()))
        poll = {
            'id': poll_id,
            'question': question,
            'options': [{'text': opt, 'votes': 0} for opt in options_list],
            'voters': set(),
            'creator': ctx.author.display_name,
            'creator_id': ctx.author.id,
            'active': True
        }
        
        polls[poll_id] = poll
        
        embed = create_poll_embed(poll)
        view = PollView(poll_id)
        
        await ctx.send(embed=embed, view=view)

# 必須的 setup 函數
async def setup(bot):
    await bot.add_cog(Vote(bot))