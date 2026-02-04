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
from managers.like_manager import LikeManager
from managers.post_manager import PostManager
from config import get_channel_id, extract_channel_id

logger = logging.getLogger(__name__)

class UnlikeModal(ui.Modal, title="🚫 いいねを削除"):
    """いいねを削除する投稿IDを入力するモーダル"""
    
    def __init__(self, like_manager: LikeManager, post_manager: PostManager):
        super().__init__(timeout=None)
        self.like_manager = like_manager
        self.post_manager = post_manager
        
        self.post_id_input = ui.TextInput(
            label="📝 投稿ID",
            placeholder="いいねを削除する投稿のIDを入力...",
            required=True,
            style=discord.TextStyle.short,
            max_length=252
        )
        
        self.add_item(self.post_id_input)
    
    async def on_submit(self, interaction: Interaction) -> None:
        """いいね削除実行"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            post_id = int(self.post_id_input.value.strip())
            user_id = str(interaction.user.id)
            
            # 投稿の存在確認
            post = self.post_manager.get_post(post_id, str(interaction.user.id))
            if not post:
                await interaction.followup.send(
                    "❌ **投稿が見つかりません**\n\n"
                    f"投稿ID: {post_id} の投稿が存在しません。",
                    ephemeral=True
                )
                return
            
            # ユーザーのいいねを検索
            logger.info(f"いいね削除試行: 投稿ID={post_id}, ユーザーID={user_id}")
            
            # like_managerを使っていいねを検索
            like_data = self.like_manager.get_like_by_user_and_post(post_id, user_id)
            
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
            success = self.like_manager.delete_like(post_id, user_id)
            
            if not success:
                logger.error(f"いいねの削除に失敗しました: 投稿ID={post_id}, ユーザーID={user_id}")
                await interaction.followup.send(
                    "❌ **エラーが発生しました**\n\n"
                    "いいねの削除に失敗しました。",
                    ephemeral=True
                )
                return
            
            # Discordメッセージを確実に削除
            message_id = like_data.get('message_id')
            channel_id = like_data.get('channel_id')
            forwarded_message_id = like_data.get('forwarded_message_id')
            
            # まず成功メッセージを送信（タイムアウト防止）
            await interaction.followup.send(
                f"✅ いいねを削除しました！\n\n"
                f"投稿ID: {post_id}\n"
                f"投稿者: {post.get('display_name', '名無し')}\n"
                f"内容: {post.get('content', '')[:100]}{'...' if len(post.get('content', '')) > 100 else ''}",
                ephemeral=True
            )
            
            # Discordメッセージを確実に削除
            if message_id and channel_id:
                try:
                    likes_channel = interaction.guild.get_channel(int(channel_id))
                    if likes_channel:
                        deleted_count = 0
                        
                        # いいねメッセージを削除
                        try:
                            like_message = await likes_channel.fetch_message(int(message_id))
                            await like_message.delete()
                            deleted_count += 1
                            logger.info(f"✅ いいねメッセージを削除しました: メッセージID={message_id}")
                        except discord.NotFound:
                            logger.warning(f"⚠️ いいねメッセージが見つかりません: メッセージID={message_id}")
                        except discord.Forbidden:
                            logger.error(f"❌ いいねメッセージの削除権限がありません: メッセージID={message_id}")
                        except Exception as e:
                            logger.error(f"❌ いいねメッセージ削除エラー: {e}")
                        
                        # 転送メッセージも削除
                        if forwarded_message_id:
                            try:
                                forwarded_message = await likes_channel.fetch_message(int(forwarded_message_id))
                                await forwarded_message.delete()
                                deleted_count += 1
                                logger.info(f"✅ 転送メッセージを削除しました: メッセージID={forwarded_message_id}")
                            except discord.NotFound:
                                logger.warning(f"⚠️ 転送メッセージが見つかりません: メッセージID={forwarded_message_id}")
                            except discord.Forbidden:
                                logger.error(f"❌ 転送メッセージの削除権限がありません: メッセージID={forwarded_message_id}")
                            except Exception as e:
                                logger.error(f"❌ 転送メッセージ削除エラー: {e}")
                        
                        logger.info(f"📊 いいね削除結果: {deleted_count}個のメッセージを削除しました")
                    else:
                        logger.error(f"❌ likesチャンネルが見つかりません: channel_id={channel_id}")
                except Exception as e:
                    logger.error(f"❌ Discordメッセージ削除処理エラー: {e}")
            else:
                logger.warning(f"⚠️ メッセージIDまたはチャンネルIDがありません: message_id={message_id}, channel_id={channel_id}")
            
            logger.info(f"✅ いいね削除完了: 投稿ID={post_id}, ユーザーID={user_id}")
            
            # GitHubに保存する処理
            from utils.github_sync import sync_to_github
            await sync_to_github("unlike", interaction.user.name, post_id)
            
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
        self.like_manager = LikeManager()
        self.post_manager = PostManager()
        logger.info("Unlike cog が初期化されました")
    
    @app_commands.command(name='unlike', description='❌ いいねを削除する')
    async def unlike_command(self, interaction: Interaction) -> None:
        """いいね削除コマンド"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # ユーザーのいいねを取得
            user_id = str(interaction.user.id)
            likes = self.like_manager.get_likes_by_user(user_id)
            
            if not likes:
                await interaction.followup.send(
                    "❌ **いいねが見つかりません**\n\n"
                    "削除できるいいねがありません。",
                    ephemeral=True
                )
                return
            
            # 投稿情報を付加
            for like in likes:
                post = self.post_manager.get_post(like['post_id'], user_id)
                if post:
                    like['post_content'] = post.get('content', '内容不明')
                else:
                    like['post_content'] = '投稿が見つかりません'
            
            # 作成日時でソート
            likes.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            # 選択ビューを表示
            from .unlike_select import UnlikeSelectView
            view = UnlikeSelectView(likes, self)
            embed = discord.Embed(
                title="❌ 削除するいいねを選択",
                description="削除したいいいねを選択してください",
                color=discord.Color.red()
            )
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"いいね削除選択UI表示中にエラーが発生しました: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ **エラーが発生しました**\n\n"
                "いいねの選択に失敗しました。もう一度お試しください。",
                ephemeral=True
            )
    
    async def process_unlike(self, interaction: Interaction, like_data: Dict[str, Any]) -> None:
        """いいね削除処理を実行"""
        try:
            # interaction.response.defer()は呼ばない（セレクトメニューで既にレスポンス済み）
            
            like_id = like_data['id']
            post_id = like_data['post_id']
            user_id = str(interaction.user.id)
            
            # いいねを削除
            success = self.like_manager.delete_like(post_id, user_id)
            
            if not success:
                await interaction.followup.send(
                    "❌ **エラーが発生しました**\n\n"
                    "いいねの削除に失敗しました。",
                    ephemeral=True
                )
                return
            
            # Discordメッセージを確実に削除
            message_id = like_data.get('message_id')
            channel_id = like_data.get('channel_id')
            forwarded_message_id = like_data.get('forwarded_message_id')
            
            if message_id and channel_id:
                try:
                    likes_channel = interaction.guild.get_channel(int(channel_id))
                    if likes_channel:
                        deleted_count = 0
                        
                        # いいねメッセージを削除
                        try:
                            like_message = await likes_channel.fetch_message(int(message_id))
                            await like_message.delete()
                            deleted_count += 1
                            logger.info(f"✅ いいねメッセージを削除しました: メッセージID={message_id}")
                        except discord.NotFound:
                            logger.warning(f"⚠️ いいねメッセージが見つかりません: メッセージID={message_id}")
                        except discord.Forbidden:
                            logger.error(f"❌ いいねメッセージの削除権限がありません: メッセージID={message_id}")
                        except Exception as e:
                            logger.error(f"❌ いいねメッセージ削除エラー: {e}")
                        
                        # 転送メッセージも削除
                        if forwarded_message_id:
                            try:
                                forwarded_message = await likes_channel.fetch_message(int(forwarded_message_id))
                                await forwarded_message.delete()
                                deleted_count += 1
                                logger.info(f"✅ 転送メッセージを削除しました: メッセージID={forwarded_message_id}")
                            except discord.NotFound:
                                logger.warning(f"⚠️ 転送メッセージが見つかりません: メッセージID={forwarded_message_id}")
                            except discord.Forbidden:
                                logger.error(f"❌ 転送メッセージの削除権限がありません: メッセージID={forwarded_message_id}")
                            except Exception as e:
                                logger.error(f"❌ 転送メッセージ削除エラー: {e}")
                        
                        logger.info(f"📊 いいね削除結果: {deleted_count}個のメッセージを削除しました")
                    else:
                        logger.error(f"❌ likesチャンネルが見つかりません: channel_id={channel_id}")
                except Exception as e:
                    logger.error(f"❌ Discordメッセージ削除処理エラー: {e}")
            
            # 成功メッセージ
            await interaction.followup.send(
                f"✅ いいねを削除しました！\n\n"
                f"いいねID: {like_id}\n"
                f"投稿ID: {post_id}\n"
                f"内容: {like_data.get('post_content', '')[:100]}{'...' if len(like_data.get('post_content', '')) > 100 else ''}",
                ephemeral=True
            )
            
            # GitHubに保存する処理
            from utils.github_sync import sync_to_github
            await sync_to_github("unlike", interaction.user.name, post_id)
            
        except Exception as e:
            logger.error(f"いいね削除処理中にエラーが発生しました: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ **エラーが発生しました**\n\n"
                "いいねの削除中にエラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )

async def setup(bot: commands.Bot) -> None:
    """Cogをセットアップする"""
    await bot.add_cog(Unlike(bot))
