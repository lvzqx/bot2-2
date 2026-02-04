import logging
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any

import discord
from discord import app_commands, ui, Interaction, Embed
from discord.ext import commands

# マネージャーをインポート
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from managers.post_manager import PostManager
from managers.message_ref_manager import MessageRefManager
from config import get_channel_id, DEFAULT_AVATAR, extract_channel_id

# モーダルとユーティリティをインポート
from .post_modal import PostModal, PostSelectView
from .post_utils import create_public_post, create_private_post

# ロガーの設定
logger = logging.getLogger(__name__)

class Post(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.post_manager = PostManager()
        self.message_ref_manager = MessageRefManager()
        logger.info("Post cog が初期化されました")

    @app_commands.command(name="post", description="📝 新規投稿を作成")
    async def post_command(self, interaction: Interaction) -> None:
        """投稿コマンド"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # 投稿タイプ選択ビューを表示
            view = PostSelectView(self)
            embed = discord.Embed(
                title="📝 投稿タイプを選択",
                description="作成したい投稿のタイプを選択してください",
                color=discord.Color.blue()
            )
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"postコマンド実行中にエラーが発生しました: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ **エラーが発生しました**\n\n"
                "投稿の作成に失敗しました。",
                ephemeral=True
            )

    async def save_post(
        self,
        interaction: Interaction,
        message: str,
        category: Optional[str],
        image_url: Optional[str],
        is_anonymous: bool,
        is_public: bool,
        display_name: Optional[str]
    ) -> Optional[int]:
        """投稿を保存する"""
        try:
            # 投稿をデータベースに保存
            post_id = self.post_manager.save_post(
                user_id=str(interaction.user.id),
                content=message,
                category=category,
                is_anonymous=is_anonymous,
                is_private=not is_public,
                display_name=display_name,
                message_id="temp",  # 仮の値
                channel_id="temp"   # 仮の値
            )
            
            logger.info(f"投稿を保存しました: 投稿ID={post_id}")
            
            # 投稿タイプに応じて処理
            if is_public:
                success = await create_public_post(
                    interaction=interaction,
                    message=message,
                    category=category,
                    image_url=image_url,
                    is_anonymous=is_anonymous,
                    display_name=display_name,
                    post_id=post_id,
                    cog=self
                )
            else:
                success = await create_private_post(
                    interaction=interaction,
                    message=message,
                    category=category,
                    image_url=image_url,
                    is_anonymous=is_anonymous,
                    display_name=display_name,
                    post_id=post_id,
                    cog=self
                )
            
            if not success:
                # 投稿データを削除
                try:
                    self.post_manager.delete_post(post_id, str(interaction.user.id))
                    logger.info(f"失敗した投稿を削除しました: 投稿ID={post_id}")
                except Exception as delete_error:
                    logger.error(f"失敗した投稿の削除中にエラー: {delete_error}")
                return None
            
            # GitHubに保存する処理
            from utils.github_sync import sync_to_github
            await sync_to_github("create post", interaction.user.name, post_id)
            
            return post_id
            
        except Exception as e:
            logger.error(f"投稿保存中にエラーが発生しました: {e}", exc_info=True)
            await interaction.followup.send(
                f"❌ **投稿の保存中にエラーが発生しました**\n\n"
                f"詳細: {str(e)}",
                ephemeral=True
            )
            return None

async def setup(bot: commands.Bot) -> None:
    """Cogをセットアップする"""
    await bot.add_cog(Post(bot))
