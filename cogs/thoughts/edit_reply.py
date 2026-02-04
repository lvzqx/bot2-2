"""
リプライ編集メインCog
"""

import discord
from discord import app_commands, ui, Interaction
from discord.ext import commands
import logging
from typing import List, Dict, Any

# マネージャーをインポート
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from managers.reply_manager import ReplyManager

# UIとユーティリティをインポート
from .edit_reply_modal import ReplyEditModal, ReplyEditSelectView
from .edit_reply_utils import update_reply_embed, update_reply_data

logger = logging.getLogger(__name__)

class EditReply(commands.Cog):
    """リプライを編集用Cog"""
    
    def __init__(self, bot):
        self.bot = bot
        self.reply_manager = ReplyManager()
    
    @app_commands.command(name='edit_reply', description='💬 リプライを編集')
    async def edit_reply(self, interaction: discord.Interaction):
        """編集するリプライを選択するコマンド"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # ユーザーのリプライを取得
            replies = self.reply_manager.get_user_replies(str(interaction.user.id))
            
            if not replies:
                await interaction.followup.send(
                    "❌ **リプライが見つかりません**\n\n"
                    "編集できるリプライがありません。",
                    ephemeral=True
                )
                return
            
            # 作成日時でソート
            replies.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            # 選択ビューを表示
            view = ReplyEditSelectView(replies, self)
            embed = discord.Embed(
                title="💬 編集するリプライを選択",
                description="編集したいリプライを選択してください",
                color=discord.Color.green()
            )
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"edit_replyコマンド実行中にエラーが発生しました: {e}")
            await interaction.followup.send(
                "❌ **エラーが発生しました**\n\n"
                "リプライの取得に失敗しました。",
                ephemeral=True
            )
    
    async def update_reply(
        self,
        interaction: discord.Interaction,
        reply_id: int,
        message: str
    ) -> bool:
        """リプライを更新する"""
        try:
            # リプライデータを更新
            data_success = await update_reply_data(
                reply_id=reply_id,
                message=message,
                reply_manager=self.reply_manager
            )
            
            if not data_success:
                return False
            
            # Discordメッセージを更新
            from managers.message_ref_manager import MessageRefManager
            message_ref_manager = MessageRefManager()
            
            message_ref_data = message_ref_manager.get_message_ref(reply_id)
            if message_ref_data:
                message_id = message_ref_data.get('message_id')
                channel_id = message_ref_data.get('channel_id')
                
                embed_success = await update_reply_embed(
                    interaction=interaction,
                    message_id=message_id,
                    channel_id=channel_id,
                    message=message,
                    reply_id=reply_id,
                    message_ref_manager=message_ref_manager
                )
                
                if not embed_success:
                    logger.warning(f"⚠️ Discordメッセージの更新に失敗しましたが、データは更新されています: reply_id={reply_id}")
            else:
                logger.warning(f"⚠️ メッセージ参照が見つかりません: reply_id={reply_id}")
            
            # GitHubに保存する処理
            from utils.github_sync import sync_to_github
            await sync_to_github("edit reply", interaction.user.name, reply_id)
            
            return True
            
        except Exception as e:
            logger.error(f"リプライ更新中にエラーが発生しました: {e}")
            return False

async def setup(bot: commands.Bot) -> None:
    """Cogをセットアップする"""
    await bot.add_cog(EditReply(bot))
