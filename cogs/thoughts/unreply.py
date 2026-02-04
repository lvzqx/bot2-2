import logging
import os
import json
from typing import Dict, Any
from datetime import datetime

import discord
from discord import app_commands, ui, Interaction, Embed
from discord.ext import commands

# マネージャーをインポート
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from managers.reply_manager import ReplyManager
from config import get_channel_id, extract_channel_id

logger = logging.getLogger(__name__)

class UnreplyModal(ui.Modal, title="� リプライを削除"):
    """リプライを削除するリプライIDを入力するモーダル"""
    
    def __init__(self, reply_manager: ReplyManager):
        super().__init__(timeout=None)
        self.reply_manager = reply_manager
        
        self.reply_id_input = ui.TextInput(
            label="💬 リプライID",
            placeholder="削除するリプライのIDを入力...",
            required=True,
            style=discord.TextStyle.short,
            max_length=252
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
            logger.info(f"リプライ削除試行: リプライID={reply_id}, ユーザーID={user_id}")
            
            # reply_managerを使ってリプライを検索
            reply_data = self.reply_manager.get_reply_by_id_and_user(reply_id, user_id)
            
            if not reply_data:
                logger.warning(f"リプライが見つかりませんでした: リプライID={reply_id}, ユーザーID={user_id}")
                await interaction.followup.send(
                    "❌ **リプライが見つかりません**\n\n"
                    f"リプライID: {reply_id} にあなたのリプライが見つかりません。",
                    ephemeral=True
                )
                return
            
            logger.info(f"リプライが見つかりました: {reply_data}")
            
            # リプライファイルを削除
            success = self.reply_manager.delete_reply(reply_id, user_id)
            
            if not success:
                logger.error(f"リプライの削除に失敗しました: リプライID={reply_id}, ユーザーID={user_id}")
                await interaction.followup.send(
                    "❌ **エラーが発生しました**\n\n"
                    "リプライの削除に失敗しました。",
                    ephemeral=True
                )
                return
            
            # Discordメッセージを確実に削除
            message_id = reply_data.get('message_id')
            channel_id = reply_data.get('channel_id')
            forwarded_message_id = reply_data.get('forwarded_message_id')
            
            # まず成功メッセージを送信（タイムアウト防止）
            await interaction.followup.send(
                f"✅ リプライを削除しました！\n\n"
                f"リプライID: {reply_id}\n"
                f"内容: {reply_data.get('content', '')[:100]}{'...' if len(reply_data.get('content', '')) > 100 else ''}",
                ephemeral=True
            )
            
            # Discordメッセージを確実に削除
            if message_id and channel_id:
                try:
                    replies_channel = interaction.guild.get_channel(int(channel_id))
                    if replies_channel:
                        deleted_count = 0
                        
                        # リプライメッセージを削除
                        try:
                            reply_message = await replies_channel.fetch_message(int(message_id))
                            await reply_message.delete()
                            deleted_count += 1
                            logger.info(f"✅ リプライメッセージを削除しました: メッセージID={message_id}")
                        except discord.NotFound:
                            logger.warning(f"⚠️ リプライメッセージが見つかりません: メッセージID={message_id}")
                        except discord.Forbidden:
                            logger.error(f"❌ リプライメッセージの削除権限がありません: メッセージID={message_id}")
                        except Exception as e:
                            logger.error(f"❌ リプライメッセージ削除エラー: {e}")
                        
                        # 転送メッセージも削除
                        if forwarded_message_id:
                            try:
                                forwarded_message = await replies_channel.fetch_message(int(forwarded_message_id))
                                await forwarded_message.delete()
                                deleted_count += 1
                                logger.info(f"✅ 転送メッセージを削除しました: メッセージID={forwarded_message_id}")
                            except discord.NotFound:
                                logger.warning(f"⚠️ 転送メッセージが見つかりません: メッセージID={forwarded_message_id}")
                            except discord.Forbidden:
                                logger.error(f"❌ 転送メッセージの削除権限がありません: メッセージID={forwarded_message_id}")
                            except Exception as e:
                                logger.error(f"❌ 転送メッセージ削除エラー: {e}")
                        
                        logger.info(f"📊 リプライ削除結果: {deleted_count}個のメッセージを削除しました")
                    else:
                        logger.error(f"❌ repliesチャンネルが見つかりません: channel_id={channel_id}")
                except Exception as e:
                    logger.error(f"❌ Discordメッセージ削除処理エラー: {e}")
            else:
                logger.warning(f"⚠️ メッセージIDまたはチャンネルIDがありません: message_id={message_id}, channel_id={channel_id}")
            
            logger.info(f"✅ リプライ削除完了: リプライID={reply_id}, ユーザーID={user_id}")
            
            # GitHubに保存する処理
            from utils.github_sync import sync_to_github
            await sync_to_github("unreply", interaction.user.name, reply_id)
            
        except ValueError:
            await interaction.followup.send(
                "❌ **エラーが発生しました**\n\n"
                "リプライIDは数字で入力してください。",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"リプライ削除中にエラーが発生しました: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ **エラーが発生しました**\n\n"
                "リプライの削除に失敗しました。",
                ephemeral=True
            )

class Unreply(commands.Cog):
    """リプライ削除機能を提供するCog"""
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.reply_manager = ReplyManager()
        logger.info("Unreply cog が初期化されました")
    
    @app_commands.command(name='unreply', description='🗑️ リプライを削除する')
    async def unreply_command(self, interaction: Interaction) -> None:
        """リプライ削除コマンド"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # ユーザーのリプライを取得
            user_id = str(interaction.user.id)
            replies = self.reply_manager.get_replies_by_user(user_id)
            
            if not replies:
                await interaction.followup.send(
                    "❌ **リプライが見つかりません**\n\n"
                    "削除できるリプライがありません。",
                    ephemeral=True
                )
                return
            
            # 作成日時でソート
            replies.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            # 選択ビューを表示
            from .unreply_select import UnreplySelectView
            view = UnreplySelectView(replies, self)
            embed = discord.Embed(
                title="🗑️ 削除するリプライを選択",
                description="削除したいリプライを選択してください",
                color=discord.Color.orange()
            )
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"リプライ削除選択UI表示中にエラーが発生しました: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ **エラーが発生しました**\n\n"
                "リプライの選択に失敗しました。もう一度お試しください。",
                ephemeral=True
            )
    
    async def process_unreply(self, interaction: Interaction, reply_data: Dict[str, Any]) -> None:
        """リプライ削除処理を実行"""
        try:
            # interaction.response.defer()は呼ばない（セレクトメニューで既にレスポンス済み）
            
            reply_id = reply_data['id']
            post_id = reply_data['post_id']
            user_id = str(interaction.user.id)
            
            # リプライを削除
            success = self.reply_manager.delete_reply(reply_id, user_id)
            
            if not success:
                await interaction.followup.send(
                    "❌ **エラーが発生しました**\n\n"
                    "リプライの削除に失敗しました。",
                    ephemeral=True
                )
                return
            
            # Discordメッセージを確実に削除
            message_id = reply_data.get('message_id')
            channel_id = reply_data.get('channel_id')
            forwarded_message_id = reply_data.get('forwarded_message_id')
            
            if message_id and channel_id:
                try:
                    replies_channel = interaction.guild.get_channel(int(channel_id))
                    if replies_channel:
                        deleted_count = 0
                        
                        # リプライメッセージを削除
                        try:
                            reply_message = await replies_channel.fetch_message(int(message_id))
                            await reply_message.delete()
                            deleted_count += 1
                            logger.info(f"✅ リプライメッセージを削除しました: メッセージID={message_id}")
                        except discord.NotFound:
                            logger.warning(f"⚠️ リプライメッセージが見つかりません: メッセージID={message_id}")
                        except discord.Forbidden:
                            logger.error(f"❌ リプライメッセージの削除権限がありません: メッセージID={message_id}")
                        except Exception as e:
                            logger.error(f"❌ リプライメッセージ削除エラー: {e}")
                        
                        # 転送メッセージも削除
                        if forwarded_message_id:
                            try:
                                forwarded_message = await replies_channel.fetch_message(int(forwarded_message_id))
                                await forwarded_message.delete()
                                deleted_count += 1
                                logger.info(f"✅ 転送メッセージを削除しました: メッセージID={forwarded_message_id}")
                            except discord.NotFound:
                                logger.warning(f"⚠️ 転送メッセージが見つかりません: メッセージID={forwarded_message_id}")
                            except discord.Forbidden:
                                logger.error(f"❌ 転送メッセージの削除権限がありません: メッセージID={forwarded_message_id}")
                            except Exception as e:
                                logger.error(f"❌ 転送メッセージ削除エラー: {e}")
                        
                        logger.info(f"📊 リプライ削除結果: {deleted_count}個のメッセージを削除しました")
                    else:
                        logger.error(f"❌ repliesチャンネルが見つかりません: channel_id={channel_id}")
                except Exception as e:
                    logger.error(f"❌ Discordメッセージ削除処理エラー: {e}")
            
            # 成功メッセージ
            await interaction.followup.send(
                f"✅ リプライを削除しました！\n\n"
                f"リプライID: {reply_id}\n"
                f"投稿ID: {post_id}\n"
                f"内容: {reply_data.get('content', '')[:100]}{'...' if len(reply_data.get('content', '')) > 100 else ''}",
                ephemeral=True
            )
            
            # GitHubに保存する処理
            from utils.github_sync import sync_to_github
            await sync_to_github("unreply", interaction.user.name, reply_id)
            
        except Exception as e:
            logger.error(f"リプライ削除処理中にエラーが発生しました: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ **エラーが発生しました**\n\n"
                "リプライの削除中にエラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )

async def setup(bot: commands.Bot) -> None:
    """Cogをセットアップする"""
    await bot.add_cog(Unreply(bot))
