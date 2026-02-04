"""ヘルプコマンドを提供するCog"""

import logging
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

# ロガーの設定
logger = logging.getLogger(__name__)

class Help(commands.Cog):
    """ヘルプコマンドを提供するCog"""
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        
    @app_commands.command(name="help")
    async def help_command(self, interaction: discord.Interaction):
        """❔利用可能なコマンドを表示します"""""
        try:
            # 埋め込みメッセージを作成
            embed = discord.Embed(
                title="🤖 利用可能なコマンド",
                description="以下のコマンドが利用できます。",
                color=discord.Color.blue()
            )
            
            # コマンド一覧を追加
            commands_list = []
            for cmd in self.bot.tree.get_commands():
                # helpコマンド自体は表示しない
                if cmd.name == "help":
                    continue
                    
                # コマンドがグループの場合はサブコマンドも表示
                if hasattr(cmd, 'commands'):
                    sub_commands = [f"`/{cmd.name} {sub.name}` - {sub.description}" 
                                  for sub in cmd.commands]
                    commands_list.append("\n".join(sub_commands))
                else:
                    commands_list.append(f"`/{cmd.name}` - {cmd.description}")
            
            if commands_list:
                embed.add_field(
                    name="📝 コマンド一覧",
                    value="\n".join(commands_list),
                    inline=False
                )
            
            # フッターを追加
            embed.set_footer(text="※ 各コマンドの詳細はスラッシュ(/)を入力して確認できます")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f'Help command error: {e}', exc_info=True)
            if not interaction.response.is_done():
                await interaction.followup.send(
                    "ヘルプの表示中にエラーが発生しました。", 
                    ephemeral=True
                )

async def setup(bot: commands.Bot) -> None:
    """Cogをセットアップする"""
    await bot.add_cog(Help(bot))
