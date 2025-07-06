import discord
from discord.ext import commands
from discord.ui import Button, View

class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 檢查是否為管理員的裝飾器
    def is_admin():
        def predicate(ctx):
            return ctx.author.guild_permissions.administrator
        return commands.check(predicate)

    @commands.command(name="addrole")
    @commands.has_permissions(administrator=True)  # 需要管理員權限
    async def add_role(self, ctx, *, role_name):
        """創建自定義身份組（僅限管理員）"""
        guild = ctx.guild
        existing_role = discord.utils.get(guild.roles, name=role_name)
        if existing_role:
            await ctx.send(f"❌ 身份組 {role_name} 已存在！")
            return
        try:
            await guild.create_role(name=role_name)
            await ctx.send(f"✅ 已創建身份組 {role_name}！")
        except discord.Forbidden:
            await ctx.send("❌ 機器人沒有足夠的權限創建身份組！")

    @commands.command(name="listroles")
    @commands.has_permissions(administrator=True)  # 需要管理員權限
    async def list_roles(self, ctx):
        """列出伺服器中的所有身份組（僅限管理員）"""
        roles = [role.name for role in ctx.guild.roles if role.name != "@everyone"]
        if not roles:
            await ctx.send("❌ 目前無其他身份組。")
            return
        await ctx.send(f"📋 當前身份組列表：\n{', '.join(roles)}")

    @commands.command(name="assignrole")
    @commands.has_permissions(administrator=True)  # 需要管理員權限
    async def assign_role(self, ctx, member: discord.Member, *, role_name):
        """為指定成員分配身份組（僅限管理員）"""
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if not role:
            await ctx.send(f"❌ 身份組 {role_name} 不存在！")
            return
        if role in member.roles:
            await ctx.send(f"❌ {member.name} 已有 {role_name} 身份組！")
            return
        try:
            await member.add_roles(role)
            await ctx.send(f"✅ 已為 {member.name} 分配 {role_name} 身份組！")
        except discord.Forbidden:
            await ctx.send("❌ 機器人沒有足夠的權限分配此身份組！")

    @commands.command(name="rolebutton")
    @commands.has_permissions(administrator=True)  # 需要管理員權限
    async def role_button(self, ctx, *, role_name):
        """創建可點擊獲得身份組的按鈕（僅限管理員）"""
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if not role:
            await ctx.send(f"❌ 身份組 {role_name} 不存在！")
            return
        view = RoleAssignView(role)
        await ctx.send(f"點擊以下按鈕獲取 {role_name} 身份組：", view=view)

    @commands.command(name="ban")
    @commands.has_permissions(administrator=True)  # 需要管理員權限
    async def ban(self, ctx, member: discord.Member, *, reason=None):
        """封禁成員（僅限管理員）"""
        if member.guild_permissions.administrator:
            await ctx.send("❌ 無法封禁管理員！")
            return
        try:
            await member.ban(reason=reason)
            await ctx.send(f"✅ 已封禁 {member.name}，原因: {reason}")
        except discord.Forbidden:
            await ctx.send("❌ 機器人沒有足夠的權限封禁此成員！")

    @commands.command(name="kick")
    @commands.has_permissions(administrator=True)  # 需要管理員權限
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        """剔除成員（僅限管理員）"""
        if member.guild_permissions.administrator:
            await ctx.send("❌ 無法踢出管理員！")
            return
        try:
            await member.kick(reason=reason)
            await ctx.send(f"✅ 已踢出 {member.name}，原因: {reason}")
        except discord.Forbidden:
            await ctx.send("❌ 機器人沒有足夠的權限踢出此成員！")

    @commands.command(name="clear")
    @commands.has_permissions(administrator=True)  # 需要管理員權限
    async def clear(self, ctx, amount: int):
        """刪除指定數量的訊息（僅限管理員）"""
        if amount > 100:
            await ctx.send("❌ 清除數量不能超過 100 條！")
            return
        try:
            await ctx.channel.purge(limit=amount + 1)  # +1 包含命令本身
            await ctx.send(f"✅ 已清除 {amount} 條訊息。")
        except discord.Forbidden:
            await ctx.send("❌ 機器人沒有足夠的權限刪除訊息！")

    # 處理權限不足的錯誤
    @add_role.error
    @list_roles.error
    @assign_role.error
    @role_button.error
    @ban.error
    @kick.error
    @clear.error
    async def permission_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ 你沒有使用此命令的權限！此命令僅限管理員使用。")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ 缺少必要參數！請檢查命令格式。")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ 參數格式錯誤！請檢查命令格式。")
        else:
            await ctx.send("❌ 發生未知錯誤！")

class RoleAssignView(View):
    def __init__(self, role):
        super().__init__(timeout=None)
        self.role = role

    @discord.ui.button(label="獲取角色", style=discord.ButtonStyle.primary)
    async def assign_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if self.role in interaction.user.roles:
                await interaction.response.send_message("❌ 你已有此身份組！", ephemeral=True)
                return
            
            await interaction.user.add_roles(self.role)
            await interaction.response.send_message(f"✅ 已為你分配 {self.role.name} 身份組！", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ 機器人沒有足夠的權限分配此身份組！", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message("❌ 發生錯誤，請聯繫管理員！", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        await interaction.response.send_message("❌ 發生錯誤，請聯繫管理員！", ephemeral=True)

@commands.Cog.listener()
async def on_ready(self):
    print("✅ Moderation Cog 已載入")

async def setup(bot):
    await bot.add_cog(ModerationCog(bot))