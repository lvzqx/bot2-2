"""
投稿機能 - リファクタリング版
"""

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
from config import get_channel_id, DEFAULT_AVATAR

# 新しいモジュールをインポート
from .post_thread import PostThreadManager
from .post_message import PostMessageManager

# ロガーの設定
logger = logging.getLogger(__name__)

class Post(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.post_manager = PostManager()
        self.message_ref_manager = MessageRefManager()
        self.thread_manager = PostThreadManager(bot)
        self.message_manager = PostMessageManager(bot)
        logger.info("Post cog が初期化されました")

    class PostModal(ui.Modal, title='新規投稿'):
        def __init__(self, cog) -> None:
            super().__init__(timeout=None)
            self.cog = cog
            self.is_public = True
            
            self.message = ui.TextInput(
                label='📝 投稿内容',
                placeholder='ここに投稿内容を入力...',
                required=True,
                style=discord.TextStyle.paragraph,
                max_length=2000
            )
            
            self.category = ui.TextInput(
                label='📁 カテゴリー',
                placeholder='カテゴリーを入力（任意）',
                required=False,
                style=discord.TextStyle.short,
                max_length=50
            )
            
            self.image_url = ui.TextInput(
                label='🖼️ 画像URL',
                placeholder='画像URLを入力（任意）',
                required=False,
                style=discord.TextStyle.short,
                max_length=500
            )
            
            self.is_anonymous = ui.TextInput(
                label='👤 匿名投稿',
                placeholder='匿名にする場合は「匿名」と入力',
                required=False,
                style=discord.TextStyle.short,
                max_length=10
            )
            
            self.display_name = ui.TextInput(
                label='🏷️ 表示名',
                placeholder='表示名を入力（任意）',
                required=False,
                style=discord.TextStyle.short,
                max_length=50
            )
            
            self.add_item(self.message)
            self.add_item(self.category)
            self.add_item(self.image_url)
            self.add_item(self.is_anonymous)
            self.add_item(self.display_name)
        
        async def on_submit(self, interaction: Interaction) -> None:
            """フォーム送信時の処理"""
            try:
                await interaction.response.defer(ephemeral=True)
                
                # フォームデータを取得
                message = self.message.value.strip()
                category = self.category.value.strip() if self.category.value else None
                image_url = self.image_url.value.strip() if self.image_url.value else None
                is_anonymous = self.is_anonymous.value.strip().lower() == '匿名'
                display_name = self.display_name.value.strip() if self.display_name.value else None
                
                # 入力検証
                is_valid, error_message = self.cog.message_manager.validate_message_content(message)
                if not is_valid:
                    await self.cog.message_manager.send_error_message(interaction, error_message)
                    return
                
                if image_url:
                    is_valid, error_message = self.cog.message_manager.validate_image_url(image_url)
                    if not is_valid:
                        await self.cog.message_manager.send_error_message(interaction, error_message)
                        return
                
                # 投稿を保存
                post_id = await self.cog.save_post(
                    interaction=interaction,
                    message=message,
                    category=category,
                    is_anonymous=is_anonymous,
                    is_private=not self.is_public,
                    display_name=display_name,
                    image_url=image_url
                )
                
                if post_id is None:
                    await self.cog.message_manager.send_error_message(interaction, "投稿の保存に失敗しました。")
                    return
                
                # メッセージを送信
                sent_message = await self.cog.send_post_message(
                    interaction=interaction,
                    post_id=post_id,
                    message=message,
                    category=category,
                    is_anonymous=is_anonymous,
                    image_url=image_url
                )
                
                if sent_message is None:
                    await self.cog.message_manager.send_error_message(
                        interaction, 
                        "メッセージ送信に失敗しました。もう一度お試しください。"
                    )
                    return
                
                # 成功メッセージを送信
                await self.cog.message_manager.send_success_message(
                    interaction=interaction,
                    sent_message=sent_message,
                    post_id=post_id,
                    category=category,
                    is_anonymous=is_anonymous,
                    is_public=self.is_public
                )
                
                # GitHubに保存
                if self.is_public:
                    from utils.github_sync import sync_to_github
                    await sync_to_github("new post", interaction.user.name, post_id)
                
            except Exception as e:
                logger.error(f"フォーム送信中にエラーが発生しました: {e}", exc_info=True)
                error_message = f"❌ 投稿中にエラーが発生しました。\n詳細: {str(e)}\n\nエラータイプ: {type(e).__name__}"
                await interaction.followup.send(error_message, ephemeral=True)
    
    async def save_post(self, interaction: Interaction, message: str, category: Optional[str],
                       is_anonymous: bool, is_private: bool, display_name: Optional[str],
                       image_url: Optional[str]) -> Optional[int]:
        """投稿を保存する"""
        try:
            post_id = self.post_manager.save_post(
                user_id=str(interaction.user.id),
                content=message,
                category=category,
                is_anonymous=is_anonymous,
                is_private=is_private,
                display_name=display_name,
                message_id="temp",  # 仮の値
                channel_id="temp",  # 仮の値
                image_url=image_url
            )
            logger.info(f"投稿を保存しました: 投稿ID={post_id}")
            return post_id
        except Exception as e:
            logger.error(f"投稿保存エラー: {e}", exc_info=True)
            return None
    
    async def send_post_message(self, interaction: Interaction, post_id: int, message: str,
                              category: Optional[str], is_anonymous: bool, 
                              image_url: Optional[str]) -> Optional[discord.Message]:
        """投稿メッセージを送信する"""
        try:
            if self.PostModal.is_public:
                # 公開投稿
                sent_message = await self.message_manager.send_public_message(
                    interaction=interaction,
                    message=message,
                    category=category,
                    post_id=post_id,
                    is_anonymous=is_anonymous,
                    image_url=image_url
                )
            else:
                # 非公開投稿
                thread = await self.thread_manager.create_private_thread(
                    interaction=interaction,
                    user_id=str(interaction.user.id),
                    post_id=post_id
                )
                
                if thread is None:
                    return None
                
                sent_message = await self.message_manager.send_private_message(
                    interaction=interaction,
                    thread=thread,
                    message=message,
                    category=category,
                    post_id=post_id,
                    is_anonymous=is_anonymous,
                    image_url=image_url
                )
            
            # メッセージ参照を保存
            if sent_message:
                await self.message_manager.save_message_ref(
                    cog=self,
                    post_id=post_id,
                    sent_message=sent_message,
                    user_id=str(interaction.user.id)
                )
            
            return sent_message
            
        except Exception as e:
            logger.error(f"メッセージ送信エラー: {e}", exc_info=True)
            return None
    
    @app_commands.command(name="post", description="📝 新規投稿を作成")
    async def post_command(self, interaction: Interaction) -> None:
        """投稿コマンド"""
        try:
            modal = self.PostModal(self)
            await interaction.response.send_modal(modal)
        except Exception as e:
            logger.error(f"postコマンド実行中にエラーが発生しました: {e}")
            await interaction.response.send_message(
                "❌ **エラーが発生しました**\n\n"
                "モーダルの表示に失敗しました。",
                ephemeral=True
            )
    
    @app_commands.command(name="private_post", description="🔒 非公開投稿を作成")
    async def private_post_command(self, interaction: Interaction) -> None:
        """非公開投稿コマンド"""
        try:
            modal = self.PostModal(self)
            modal.is_public = False
            await interaction.response.send_modal(modal)
        except Exception as e:
            logger.error(f"private_postコマンド実行中にエラーが発生しました: {e}")
            await interaction.response.send_message(
                "❌ **エラーが発生しました**\n\n"
                "モーダルの表示に失敗しました。",
                ephemeral=True
            )

async def setup(bot: commands.Bot) -> None:
    """Cogをセットアップする"""
    await bot.add_cog(Post(bot))
    logger.info("Post cog がセットアップされました")
