import logging
import os
import json
from typing import Dict, Any
from datetime import datetime

import discord
from discord import app_commands, ui, Interaction, Embed
from discord.ext import commands

# ファイルマネージャーをインポート
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from file_manager import FileManager
from config import get_channel_id, extract_channel_id

logger = logging.getLogger(__name__)

class UnlikeModal(ui.Modal, title="🚫 いいねを削除"):
    """いいねを削除する投稿IDを入力するモーダル"""
    
    def __init__(self, file_manager: FileManager):
        super().__init__(timeout=300)
        self.file_manager = file_manager
        
        self.post_id_input = ui.TextInput(
            label="📝 投稿ID",
            placeholder="いいねを削除する投稿のIDを入力...",
            required=True,
            style=discord.TextStyle.short,
            max_length=10
        )
        
        self.add_item(self.post_id_input)
    
    async def on_submit(self, interaction: Interaction) -> None:
        """いいね削除実行"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            post_id = int(self.post_id_input.value.strip())
            user_id = str(interaction.user.id)
            
            # 投稿の存在確認
            post = self.file_manager.get_post(post_id)
            if not post:
                await interaction.followup.send(
                    "❌ **投稿が見つかりません**\n\n"
                    f"投稿ID: {post_id} の投稿が存在しません。",
                    ephemeral=True
                )
                return
            
            # ユーザーのいいねを検索
            logger.info(f"いいね削除試行: 投稿ID={post_id}, ユーザーID={user_id}")
            
            # file_managerを使っていいねを検索
            like_data = self.file_manager.get_like_by_user_and_post(post_id, user_id)
            
            if not like_data:
                logger.warning(f"いいねが見つかりませんでした: 投稿ID={post_id}, ユーザーID={user_id}")
                await interaction.followup.send(
                    "❌ **いいねが見つかりません**\n\n"
                    f"投稿ID: {post_id} にあなたのいいねが見つかりません。",
                    ephemeral=True
                )
                return
            
            logger.info(f"いいねが見つかりました: {like_data}")
            
            # いいねファイルを削除
            success = self.file_manager.delete_like(post_id, user_id)
            
            if not success:
                logger.error(f"いいねの削除に失敗しました: 投稿ID={post_id}, ユーザーID={user_id}")
                await interaction.followup.send(
                    "❌ **エラーが発生しました**\n\n"
                    "いいねの削除に失敗しました。",
                    ephemeral=True
                )
                return
            
            # Discordメッセージを削除
            message_id = like_data.get('message_id')
            channel_id = like_data.get('channel_id')
            forwarded_message_id = like_data.get('forwarded_message_id')
            
            if message_id and channel_id:
                # いいねチャンネルのメッセージを削除
                likes_channel = interaction.guild.get_channel(int(channel_id))
                if likes_channel:
                    # いいねメッセージを削除
                    try:
                        like_message = await likes_channel.fetch_message(int(message_id))
                        await like_message.delete()
                        logger.info(f"いいねメッセージを削除しました: メッセージID={message_id}")
                    except (discord.NotFound, discord.Forbidden):
                        logger.warning(f"いいねメッセージの削除に失敗しました: {message_id}")
                    
                    # 転送メッセージも削除
                    if forwarded_message_id:
                        try:
                            forwarded_message = await likes_channel.fetch_message(int(forwarded_message_id))
                            await forwarded_message.delete()
                            logger.info(f"転送メッセージを削除しました: メッセージID={forwarded_message_id}")
                        except (discord.NotFound, discord.Forbidden):
                            logger.warning(f"転送メッセージの削除に失敗しました: {forwarded_message_id}")
            
            await interaction.followup.send(
                f"✅ いいねを削除しました！\n\n"
                f"投稿ID: {post_id}\n"
                f"投稿者: {post.get('display_name', '名無し')}\n"
                f"内容: {post.get('content', '')[:100]}{'...' if len(post.get('content', '')) > 100 else ''}",
                ephemeral=True
            )
            
        except ValueError:
            await interaction.followup.send(
                "❌ **エラーが発生しました**\n\n"
                "投稿IDは数字で入力してください。",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"いいね削除中にエラーが発生しました: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ **エラーが発生しました**\n\n"
                "いいねの削除中にエラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )

class Unlike(commands.Cog):
    """いいね削除機能を提供するCog"""
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.file_manager = FileManager()
        logger.info("Unlike cog が初期化されました")
    
    @app_commands.command(name='unlike', description='❌ いいねを削除する')
    async def unlike_command(self, interaction: Interaction) -> None:
        """いいね削除コマンド"""
        try:
            await interaction.response.send_modal(UnlikeModal(self.file_manager))
        except Exception as e:
            logger.error(f"いいね削除モーダル表示中にエラーが発生しました: {e}", exc_info=True)
            await interaction.response.send_message(
                "❌ **エラーが発生しました**\n\n"
                "モーダルの表示中にエラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )

async def setup(bot: commands.Bot) -> None:
    """Cogをセットアップ"""
    try:
        await bot.add_cog(Unlike(bot))
        logger.info("Unlike cog がセットアップされました")
    except Exception as e:
        logger.error(f"Unlike cog セットアップ中にエラーが発生しました: {e}", exc_info=True)
        raise
