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
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from managers.like_manager import LikeManager
from config import get_channel_id, extract_channel_id

logger = logging.getLogger(__name__)

class LikeModal(ui.Modal, title="❤️ いいねする投稿"):
    """いいねする投稿IDを入力するモーダル"""
    
    def __init__(self, like_manager: LikeManager):
        super().__init__(timeout=None)
        self.like_manager = like_manager
        
        self.post_id_input = ui.TextInput(
            label="📝 投稿ID",
            placeholder="いいねする投稿のIDを入力...",
            required=True,
            style=discord.TextStyle.short,
            max_length=252
        )
        self.add_item(self.post_id_input)
    
    async def on_submit(self, interaction: Interaction) -> None:
        """いいね実行"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            post_id = int(self.post_id_input.value.strip())
            
            # 投稿情報を取得
            post = None  # 仮実装
            # TODO: PostManagerを追加して修正
            # post = self.like_manager.post_manager.get_post(post_id)
            
            if not post:
                await interaction.followup.send(
                    "投稿が見つかりませんでした。\n\n"
                    f"投稿ID: {post_id}\n"
                    "※正しい投稿IDを入力してください。",
                    ephemeral=True
                )
                return
            
            # いいねを保存
            like_id = self.like_manager.save_like(
                post_id=post_id,
                user_id=str(interaction.user.id),
                display_name=interaction.user.display_name
            )
            
            # まず成功メッセージを送信（速度改善）
            await interaction.followup.send(
                f"✅ いいねしました！\n\n"
                f"投稿ID: {post_id}\n"
                f"いいねID: {like_id}\n"
                f"投稿者: {post.get('display_name', '名無し')}\n"
                f"内容: {post.get('content', '')[:100]}{'...' if len(post.get('content', '')) > 100 else ''}",
                ephemeral=True
            )
            
            # Discordメッセージ処理をバックグラウンドで実行
            try:
                likes_channel_id = extract_channel_id(get_channel_id('likes'))
                likes_channel = interaction.guild.get_channel(likes_channel_id)
                
                if likes_channel:
                    # 元の投稿メッセージ参照を取得
                    message_ref_data = None  # 仮実装
                    # TODO: MessageRefManagerを追加して修正
                    # message_ref_data = self.like_manager.message_ref_manager.get_message_ref(post_id)
                    if message_ref_data:
                        message_id = message_ref_data.get('message_id')
                        channel_id = message_ref_data.get('channel_id')
                        
                        if message_id and channel_id:
                            try:
                                # 元の投稿メッセージを取得
                                original_channel = interaction.guild.get_channel(int(channel_id))
                                if original_channel:
                                    original_message = await original_channel.fetch_message(int(message_id))
                                    
                                    # 元の投稿を転送
                                    forwarded_message = await original_message.forward(likes_channel)
                                    
                                    # いいねしたことを投稿
                                    like_message = await likes_channel.send(f"❤️ いいね：{interaction.user.display_name}")
                                    
                                    # いいねファイルに両方のメッセージIDを保存
                                    # TODO: LikeManagerのupdate_like_message_idを追加して修正
                                    # self.like_manager.update_like_message_id(like_id, str(like_message.id), str(likes_channel.id), str(forwarded_message.id))
                                    logger.info(f"✅ いいねDiscordメッセージ処理完了: like_id={like_id}")
                                else:
                                    logger.warning(f"元のチャンネルが見つかりません: channel_id={channel_id}")
                            except discord.NotFound:
                                logger.warning(f"メッセージが見つかりません: message_id={message_id}")
                            except discord.Forbidden:
                                logger.warning(f"メッセージへのアクセス権限がありません: message_id={message_id}")
                            except Exception as e:
                                logger.error(f"メッセージ取得エラー: {e}")
                        else:
                            logger.warning(f"メッセージIDまたはチャンネルIDがありません: message_id={message_id}, channel_id={channel_id}")
                    else:
                        logger.warning(f"メッセージ参照が見つかりません: post_id={post_id}")
                else:
                    logger.warning(f"likesチャンネルが見つかりません: likes_channel_id={likes_channel_id}")
            except Exception as e:
                logger.error(f"いいねチャンネル転送エラー: {e}")
                # Discord転送エラーがあっても、いいね自体は保存されているので続行
            
            logger.info(f"✅ いいねが作成されました: 投稿ID={post_id}, いいねID={like_id}, ユーザーID={interaction.user.id}")
            
        except ValueError:
            await interaction.followup.send(
                "❌ **エラーが発生しました**\n\n"
                "投稿IDは数字で入力してください。",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"いいね作成中にエラーが発生しました: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ **エラーが発生しました**\n\n"
                "いいねの作成中にエラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )

class Like(commands.Cog):
    """いいね機能を提供するCog"""
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.like_manager = LikeManager()
        logger.info("Like cog が初期化されました")
    
    @app_commands.command(name='like', description='❤️ 投稿にいいねする')
    async def like_command(self, interaction: Interaction) -> None:
        """いいねコマンド"""
        try:
            await interaction.response.send_modal(LikeModal(self.like_manager))
        except Exception as e:
            logger.error(f"いいねモーダル表示中にエラーが発生しました: {e}", exc_info=True)
            await interaction.response.send_message(
                "❌ **エラーが発生しました**\n\n"
                "いいねモーダルの表示中にエラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )

async def setup(bot: commands.Bot) -> None:
    """Cogをセットアップ"""
    try:
        await bot.add_cog(Like(bot))
        logger.info("Like cog がセットアップされました")
    except Exception as e:
        logger.error(f"Like cog セットアップ中にエラーが発生しました: {e}", exc_info=True)
        raise
