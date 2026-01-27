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

class UnlikeModal(ui.Modal, title="❌ いいねを削除"):
    """いいねを削除する投稿IDを入力するモーダル"""
    
    def __init__(self):
        super().__init__(timeout=300)
        self.file_manager = FileManager()
        
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
            likes_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                    'data', 'likes')
            
            logger.info(f"いいね削除試行: 投稿ID={post_id}, ユーザーID={user_id}")
            logger.info(f"いいねディレクトリ: {likes_dir}")
            
            like_found = False
            like_file_path = None
            
            if os.path.exists(likes_dir):
                logger.info(f"いいねディレクトリが存在します")
                files = os.listdir(likes_dir)
                logger.info(f"いいねファイル一覧: {files}")
                
                for filename in files:
                    if filename.startswith(f'{post_id}_') and filename.endswith('.json'):
                        like_file_path = os.path.join(likes_dir, filename)
                        try:
                            with open(like_file_path, 'r', encoding='utf-8') as f:
                                like_data = json.load(f)
                            
                            logger.info(f"ファイル {filename} のデータ: {like_data}")
                            
                            # いいねしたユーザーが一致するか確認
                            if like_data.get('user_id') == user_id:
                                like_found = True
                                logger.info(f"いいねが見つかりました: {like_file_path}")
                                break
                        except (json.JSONDecodeError, FileNotFoundError) as e:
                            logger.error(f"ファイル読み込みエラー {filename}: {e}")
                            continue
            else:
                logger.warning(f"いいねディレクトリが存在しません: {likes_dir}")
            
            if not like_found:
                logger.warning(f"いいねが見つかりませんでした: 投稿ID={post_id}, ユーザーID={user_id}")
                await interaction.followup.send(
                    "❌ **いいねが見つかりません**\n\n"
                    f"投稿ID: {post_id} にあなたのいいねが見つかりません。",
                    ephemeral=True
                )
                return
            
            # いいねファイルを削除
            if like_file_path and os.path.exists(like_file_path):
                # ファイルからメッセージIDを取得して削除
                try:
                    with open(like_file_path, 'r', encoding='utf-8') as f:
                        like_data = json.load(f)
                        message_id = like_data.get('message_id')
                        channel_id = like_data.get('channel_id')
                    
                    if message_id and channel_id:
                        # いいねチャンネルのメッセージを削除
                        likes_channel = interaction.guild.get_channel(int(channel_id))
                        if likes_channel:
                            try:
                                like_message = await likes_channel.fetch_message(int(message_id))
                                await like_message.delete()
                                logger.info(f"いいねメッセージを削除しました: メッセージID={message_id}")
                            except (discord.NotFound, discord.Forbidden):
                                logger.warning(f"いいねメッセージの削除に失敗しました: {message_id}")
                except (json.JSONDecodeError, FileNotFoundError):
                    pass
                
                # ファイルを削除
                os.remove(like_file_path)
                logger.info(f"いいねを削除しました: 投稿ID={post_id}, ユーザーID={user_id}")
            else:
                logger.error(f"いいねファイルが見つかりません: {like_file_path}")
                await interaction.followup.send(
                    "❌ **エラーが発生しました**\n\n"
                    "いいねファイルが見つかりません。",
                    ephemeral=True
                )
                return
            
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
        logger.info("Unlike cog が初期化されました")
    
    @app_commands.command(name='unlike', description='❌ いいねを削除する')
    async def unlike_command(self, interaction: Interaction) -> None:
        """いいね削除コマンド"""
        try:
            await interaction.response.send_modal(UnlikeModal())
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
