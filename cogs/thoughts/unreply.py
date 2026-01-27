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

class UnreplyModal(ui.Modal, title="🗑️ リプライを削除"):
    """リプライを削除するリプライIDを入力するモーダル"""
    
    def __init__(self):
        super().__init__(timeout=300)
        self.file_manager = FileManager()
        
        self.reply_id_input = ui.TextInput(
            label="💬 リプライID",
            placeholder="削除するリプライのIDを入力...",
            required=True,
            style=discord.TextStyle.short,
            max_length=10
        )
        
        self.add_item(self.reply_id_input)
    
    async def on_submit(self, interaction: Interaction) -> None:
        """リプライ削除実行"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            reply_id = self.reply_id_input.value.strip()
            user_id = str(interaction.user.id)
            
            logger.info(f"リプライ削除試行: リプライID={reply_id}, ユーザーID={user_id}")
            
            # リプライファイルを検索
            replies_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                     'data', 'replies')
            
            logger.info(f"リプライディレクトリ: {replies_dir}")
            
            reply_found = False
            reply_file_path = None
            reply_data = None
            
            if os.path.exists(replies_dir):
                logger.info(f"リプライディレクトリが存在します")
                files = os.listdir(replies_dir)
                logger.info(f"リプライファイル一覧: {files}")
                
                for filename in files:
                    if filename.endswith('.json'):
                        reply_file_path = os.path.join(replies_dir, filename)
                        try:
                            with open(reply_file_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            
                            logger.info(f"ファイル {filename} のデータ: {data}")
                            
                            # リプライIDとユーザーが一致するか確認
                            if (data.get('id') == reply_id and 
                                data.get('user_id') == user_id):
                                reply_found = True
                                reply_data = data
                                logger.info(f"リプライが見つかりました: {reply_file_path}")
                                break
                        except (json.JSONDecodeError, FileNotFoundError) as e:
                            logger.error(f"ファイル読み込みエラー {filename}: {e}")
                            continue
            else:
                logger.warning(f"リプライディレクトリが存在しません: {replies_dir}")
            
            if not reply_found:
                logger.warning(f"リプライが見つかりませんでした: リプライID={reply_id}, ユーザーID={user_id}")
                await interaction.followup.send(
                    "❌ **リプライが見つかりません**\n\n"
                    f"リプライID: {reply_id} のリプライが見つからないか、あなたのリプライではありません。",
                    ephemeral=True
                )
                return
            
            # リプライファイルを削除
            if reply_file_path and os.path.exists(reply_file_path):
                # ファイルからメッセージIDを取得して削除
                try:
                    with open(reply_file_path, 'r', encoding='utf-8') as f:
                        reply_data = json.load(f)
                        message_id = reply_data.get('message_id')
                        channel_id = reply_data.get('channel_id')
                    
                    if message_id and channel_id:
                        # リプライチャンネルのメッセージを削除
                        replies_channel = interaction.guild.get_channel(int(channel_id))
                        if replies_channel:
                            try:
                                reply_message = await replies_channel.fetch_message(int(message_id))
                                await reply_message.delete()
                                logger.info(f"リプライメッセージを削除しました: メッセージID={message_id}")
                            except (discord.NotFound, discord.Forbidden):
                                logger.warning(f"リプライメッセージの削除に失敗しました: {message_id}")
                except (json.JSONDecodeError, FileNotFoundError):
                    pass
                
                # ファイルを削除
                os.remove(reply_file_path)
                logger.info(f"リプライを削除しました: リプライID={reply_id}, ユーザーID={user_id}")
            else:
                logger.error(f"リプライファイルが見つかりません: {reply_file_path}")
                await interaction.followup.send(
                    "❌ **エラーが発生しました**\n\n"
                    "リプライファイルが見つかりません。",
                    ephemeral=True
                )
                return
            
            await interaction.followup.send(
                f"✅ リプライを削除しました！\n\n"
                f"リプライID: {reply_id}\n"
                f"内容: {reply_data.get('content', '')[:100]}{'...' if len(reply_data.get('content', '')) > 100 else ''}",
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"リプライ削除中にエラーが発生しました: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ **エラーが発生しました**\n\n"
                "リプライの削除中にエラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )

class Unreply(commands.Cog):
    """リプライ削除機能を提供するCog"""
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        logger.info("Unreply cog が初期化されました")
    
    @app_commands.command(name='unreply', description='🗑️ リプライを削除する')
    async def unreply_command(self, interaction: Interaction) -> None:
        """リプライ削除コマンド"""
        try:
            await interaction.response.send_modal(UnreplyModal())
        except Exception as e:
            logger.error(f"リプライ削除モーダル表示中にエラーが発生しました: {e}", exc_info=True)
            await interaction.response.send_message(
                "❌ **エラーが発生しました**\n\n"
                "モーダルの表示中にエラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )

async def setup(bot: commands.Bot) -> None:
    """Cogをセットアップ"""
    try:
        await bot.add_cog(Unreply(bot))
        logger.info("Unreply cog がセットアップされました")
    except Exception as e:
        logger.error(f"Unreply cog セットアップ中にエラーが発生しました: {e}", exc_info=True)
        raise
