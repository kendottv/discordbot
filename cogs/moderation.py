import discord
from discord.ext import commands
from discord.ui import Button, View

class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="addrole")
    @commands.has_permissions(manage_roles=True)
    async def add_role(self, ctx, *, role_name):
        """創建自定義身份組（僅限管理員）"""
        guild = ctx.guild
        existing_role = discord.utils.get(guild.roles, name=role_name)
        if existing_role:
            await ctx.send(f"❌ 身份組 {role_name} 已存在！")
            return
        await guild.create_role(name=role_name)
        await ctx.send(f"✅ 已創建身份組 {role_name}！")

    @commands.command(name="listroles")
    @commands.has_permissions(manage_roles=True)
    async def list_roles(self, ctx):
        """列出伺服器中的所有身份組（僅限管理員）"""
        roles = [role.name for role in ctx.guild.roles if role.name != "@everyone"]
        if not roles:
            await ctx.send("❌ 目前無其他身份組。")
            return
        await ctx.send(f"📋 當前身份組列表：\n{', '.join(roles)}")

    @commands.command(name="assignrole")
    @commands.has_permissions(manage_roles=True)
    async def assign_role(self, ctx, member: discord.Member, *, role_name):
        """為指定成員分配身份組（僅限管理員）"""
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if not role:
            await ctx.send(f"❌ 身份組 {role_name} 不存在！")
            return
        if role in member.roles:
            await ctx.send(f"❌ {member.name} 已有 {role_name} 身份組！")
            return
        await member.add_roles(role)
        await ctx.send(f"✅ 已為 {member.name} 分配 {role_name} 身份組！")

    @commands.command(name="rolebutton")
    @commands.has_permissions(manage_roles=True)
    async def role_button(self, ctx, *, role_name):
        """創建可點擊獲得身份組的按鈕（僅限管理員）"""
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if not role:
            await ctx.send(f"❌ 身份組 {role_name} 不存在！")
            return
        view = RoleAssignView(role)
        await ctx.send(f"點擊以下按鈕獲取 {role_name} 身份組：", view=view)

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason=None):
        """封禁成員（僅限管理員）"""
        await member.ban(reason=reason)
        await ctx.send(f"✅ 已封禁 {member.name}，原因: {reason}")

    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        """剔除成員（僅限管理員）"""
        await member.kick(reason=reason)
        await ctx.send(f"✅ 已踢出 {member.name}，原因: {reason}")

    @commands.command(name="clear")
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int):
        """刪除指定數量的訊息（僅限管理員）"""
        if amount > 100:
            await ctx.send("❌ 清除數量不能超過 100 條！")
            return
        await ctx.channel.purge(limit=amount + 1)  # +1 包含命令本身
        await ctx.send(f"✅ 已清除 {amount} 條訊息。")

class RoleAssignView(View):
    def __init__(self, role):
        super().__init__(timeout=None)
        self.role = role
        self.add_item(Button(label=f"獲取 {role.name}", custom_id=f"assign_{role.id}", style=discord.ButtonStyle.primary))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True  # 允許所有使用者互動，可根據需求添加限制

    @discord.ui.button(label="獲取角色", custom_id="assign_role", style=discord.ButtonStyle.primary)
    async def assign_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        if isinstance(interaction.data, dict) and "custom_id" in interaction.data:
            role_id = int(interaction.data["custom_id"].split("_")[1])
            role = interaction.guild.get_role(role_id)
            if role and role not in interaction.user.roles:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(f"✅ 已為你分配 {role.name} 身份組！", ephemeral=True)
            else:
                await interaction.response.send_message("❌ 你已有此身份組或角色無效！", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        await interaction.response.send_message("❌ 發生錯誤，請聯繫管理員！", ephemeral=True)

@commands.Cog.listener()
async def on_ready(self):
    print("✅ Moderation Cog 已載入")

async def setup(bot):
    await bot.add_cog(ModerationCog(bot))