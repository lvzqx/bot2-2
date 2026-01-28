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
from managers.reply_manager import ReplyManager
from managers.post_manager import PostManager
from managers.message_ref_manager import MessageRefManager
from config import get_channel_id, extract_channel_id

logger = logging.getLogger(__name__)

class ReplyModal(ui.Modal, title="💬 リプライする投稿"):
    """リプライする投稿IDと内容を入力するモーダル"""
    
    def __init__(self, reply_manager: ReplyManager, post_manager: PostManager, message_ref_manager: MessageRefManager):
        super().__init__(timeout=None)
        self.reply_manager = reply_manager
        self.post_manager = post_manager
        self.message_ref_manager = message_ref_manager
        
        self.post_id_input = ui.TextInput(
            label="📝 投稿ID",
            placeholder="リプライする投稿のIDを入力...",
            required=True,
            style=discord.TextStyle.short,
            max_length=252
        )
        
        self.reply_input = ui.TextInput(
            label="💬 リプライ内容",
            placeholder="リプライの内容を入力...",
            required=True,
            style=discord.TextStyle.paragraph
        )
        
        self.add_item(self.post_id_input)
        self.add_item(self.reply_input)
    
    async def on_submit(self, interaction: Interaction) -> None:
        """リプライ実行"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            post_id = int(self.post_id_input.value.strip())
            reply_content = self.reply_input.value.strip()
            
            # 親投稿の存在確認
            parent_post = self.post_manager.get_post(post_id)
            
            if not parent_post:
                await interaction.followup.send(
                    "💬 指定された投稿が見つかりませんでした。",
                    ephemeral=True
                )
                return
            
            # リプライを保存
            reply_id = self.reply_manager.save_reply(
                post_id=post_id,
                user_id=str(interaction.user.id),
                content=reply_content,
                display_name=interaction.user.display_name
            )
            
            # まず成功メッセージを送信（速度改善）
            await interaction.followup.send(
                f"✅ リプライしました！\n\n"
                f"投稿ID: {post_id}\n"
                f"リプライID: {reply_id}\n"
                f"投稿者: {parent_post.get('display_name', '名無し')}\n"
                f"リプライ内容: {reply_content[:100]}{'...' if len(reply_content) > 100 else ''}",
                ephemeral=True
            )
            
            # Discordメッセージ処理をバックグラウンドで実行
            try:
                replies_channel_id = extract_channel_id(get_channel_id('replies'))
                replies_channel = interaction.guild.get_channel(replies_channel_id)
                
                if replies_channel:
                    # 元の投稿メッセージ参照を取得
                    message_ref_data = self.message_ref_manager.get_message_ref(post_id)
                    if message_ref_data:
                        message_id = message_ref_data.get('message_id')
                        channel_id = message_ref_data.get('channel_id')
                        
                        if message_id and channel_id:
                            try:
                                # 元の投稿メッセージを取得
                                original_channel = interaction.guild.get_channel(int(channel_id))
                                if original_channel:
                                    # 元の投稿メッセージを取得
                                    original_message = await original_channel.fetch_message(int(message_id))
                                    
                                    # 元の投稿を転送
                                    forwarded_message = await original_message.forward(replies_channel)
                                    
                                    # リプライを投稿
                                    reply_embed = discord.Embed(
                                        title=f"💬 リプライ：{interaction.user.display_name}",
                                        description=reply_content,
                                        color=discord.Color.green()
                                    )
                                    reply_embed.set_footer(text=f"リプライID: {reply_id}")
                                    reply_message = await replies_channel.send(embed=reply_embed)
                                    
                                    # リプライファイルに両方のメッセージIDを保存
                                    # TODO: ReplyManagerのupdate_reply_message_idメソッドを追加
                                    # self.reply_manager.update_reply_message_id(reply_id, str(reply_message.id), str(replies_channel.id), str(forwarded_message.id))
                                    logger.info(f"✅ リプライDiscordメッセージ処理完了: reply_id={reply_id}")
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
                    logger.warning(f"repliesチャンネルが見つかりません: replies_channel_id={replies_channel_id}")
            except Exception as e:
                logger.error(f"リプライチャンネル転送エラー: {e}")
                # Discord転送エラーがあっても、リプライ自体は保存されているので続行
            
            logger.info(f"✅ リプライが作成されました: 投稿ID={post_id}, リプライID={reply_id}, ユーザーID={interaction.user.id}")
            
        except ValueError:
            await interaction.followup.send(
                "❌ **エラーが発生しました**\n\n"
                "投稿IDは数字で入力してください。",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"リプライ作成中にエラーが発生しました: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ **エラーが発生しました**\n\n"
                "リプライの作成中にエラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )

class Reply(commands.Cog):
    """リプライ機能を提供するCog"""
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.reply_manager = ReplyManager()
        self.post_manager = PostManager()
        self.message_ref_manager = MessageRefManager()
        logger.info("Reply cog が初期化されました")
    
    @app_commands.command(name='reply', description='💬 投稿にリプライする')
    async def reply_command(self, interaction: Interaction) -> None:
        """リプライコマンド"""
        try:
            await interaction.response.send_modal(ReplyModal(self.reply_manager, self.post_manager, self.message_ref_manager))
        except Exception as e:
            logger.error(f"リプライモーダル表示中にエラーが発生しました: {e}", exc_info=True)
            await interaction.response.send_message(
                "❌ **エラーが発生しました**\n\n"
                "リプライモーダルの表示中にエラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )

async def setup(bot: commands.Bot) -> None:
    """Cogをセットアップ"""
    try:
        await bot.add_cog(Reply(bot))
        logger.info("Reply cog がセットアップされました")
    except Exception as e:
        logger.error(f"Reply cog セットアップ中にエラーが発生しました: {e}", exc_info=True)
        raise
