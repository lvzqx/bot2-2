"""
編集メインCog
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
from managers.post_manager import PostManager

# UIとユーティリティをインポート
from .edit_modal import PostEditModal, PostEditSelectView
from .edit_utils import update_post_embed, update_post_data

logger = logging.getLogger(__name__)

class Edit(commands.Cog):
    """投稿を編集用Cog"""
    
    def __init__(self, bot):
        self.bot = bot
        self.post_manager = PostManager()
    
    @app_commands.command(name='edit', description='📝 投稿を編集')
    async def edit(self, interaction: discord.Interaction):
        """編集する投稿を選択するコマンド"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # ユーザーの投稿を取得
            posts = self.post_manager.search_posts(user_id=str(interaction.user.id))
            
            if not posts:
                await interaction.followup.send(
                    "❌ **投稿が見つかりません**\n\n"
                    "編集できる投稿がありません。",
                    ephemeral=True
                )
                return
            
            # 作成日時でソート
            posts.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            # 選択ビューを表示
            view = PostEditSelectView(posts, self)
            embed = discord.Embed(
                title="📝 編集する投稿を選択",
                description="編集したい投稿を選択してください",
                color=discord.Color.orange()
            )
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"editコマンド実行中にエラーが発生しました: {e}")
            await interaction.followup.send(
                "❌ **エラーが発生しました**\n\n"
                "投稿の取得に失敗しました。",
                ephemeral=True
            )
    
    async def update_post(
        self,
        interaction: discord.Interaction,
        post_id: int,
        message: str,
        category: str,
        image_url: str
    ) -> bool:
        """投稿を更新する"""
        try:
            # 投稿データを更新
            data_success = await update_post_data(
                post_id=post_id,
                message=message,
                category=category,
                image_url=image_url,
                post_manager=self.post_manager
            )
            
            if not data_success:
                return False
            
            # Discordメッセージを更新
            from managers.message_ref_manager import MessageRefManager
            message_ref_manager = MessageRefManager()
            
            message_ref_data = message_ref_manager.get_message_ref(post_id)
            if message_ref_data:
                message_id = message_ref_data.get('message_id')
                channel_id = message_ref_data.get('channel_id')
                
                embed_success = await update_post_embed(
                    interaction=interaction,
                    message_id=message_id,
                    channel_id=channel_id,
                    message=message,
                    category=category,
                    image_url=image_url,
                    post_id=post_id,
                    message_ref_manager=message_ref_manager
                )
                
                if not embed_success:
                    logger.warning(f"⚠️ Discordメッセージの更新に失敗しましたが、データは更新されています: post_id={post_id}")
            else:
                logger.warning(f"⚠️ メッセージ参照が見つかりません: post_id={post_id}")
            
            # GitHubに保存する処理
            from utils.github_sync import sync_to_github
            await sync_to_github("edit post", interaction.user.name, post_id)
            
            return True
            
        except Exception as e:
            logger.error(f"投稿更新中にエラーが発生しました: {e}")
            return False

async def setup(bot: commands.Bot) -> None:
    """Cogをセットアップする"""
    await bot.add_cog(Edit(bot))
