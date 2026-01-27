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

class LikeModal(ui.Modal, title="❤️ いいねする投稿"):
    """いいねする投稿IDを入力するモーダル"""
    
    def __init__(self):
        super().__init__(timeout=300)
        self.file_manager = FileManager()
        
        self.post_id_input = ui.TextInput(
            label="📝 投稿ID",
            placeholder="いいねする投稿のIDを入力...",
            required=True,
            style=discord.TextStyle.short,
            max_length=10
        )
        self.add_item(self.post_id_input)
    
    async def on_submit(self, interaction: Interaction) -> None:
        """いいね実行"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            post_id = int(self.post_id_input.value.strip())
            
            # 投稿情報を取得
            post = self.file_manager.get_post(post_id)
            
            if not post:
                await interaction.followup.send(
                    "投稿が見つかりませんでした。\n\n"
                    f"投稿ID: {post_id}\n"
                    "※正しい投稿IDを入力してください。",
                    ephemeral=True
                )
                return
            
            # いいねを保存
            like_id = self.file_manager.save_like(
                post_id=post_id,
                user_id=str(interaction.user.id),
                display_name=interaction.user.display_name
            )
            
            # いいねチャンネルに転送
            likes_channel_id = get_channel_id('likes')
            likes_channel = interaction.guild.get_channel(likes_channel_id)
            
            if likes_channel:
                # 元の投稿メッセージを取得して転送
                message_ref_file = os.path.join("data", f"message_ref_{post_id}.json")
                if os.path.exists(message_ref_file):
                    try:
                        with open(message_ref_file, 'r', encoding='utf-8') as f:
                            message_ref_data = json.load(f)
                            message_id = message_ref_data.get('message_id')
                            channel_id = message_ref_data.get('channel_id')
                        
                        if message_id and channel_id:
                            # 元の投稿メッセージを取得
                            original_channel = interaction.guild.get_channel(int(channel_id))
                            if original_channel:
                                original_message = await original_channel.fetch_message(int(message_id))
                                
                                # 元の投稿を転送
                                await original_message.forward(likes_channel)
                                
                                # いいねしたことを投稿
                                like_message = await likes_channel.send(f"❤️ いいね：{interaction.user.display_name}")
                                
                                # いいねファイルにメッセージIDを保存
                                self.file_manager.update_like_message_id(like_id, str(like_message.id), str(likes_channel.id))
                            else:
                                # チャンネルが見つからない場合は従来通り
                                like_embed = discord.Embed(
                                    title=f"❤️ いいね：{interaction.user.display_name}",
                                    description=f"**投稿ID: {post_id}**\n\n{post.get('content', '')}",
                                    color=discord.Color.red()
                                )
                                like_embed.add_field(name="投稿者", value=post.get('display_name', '名無し'), inline=True)
                                like_embed.set_footer(text=f"いいねID: {like_id}")
                                like_message = await likes_channel.send(embed=like_embed)
                                self.file_manager.update_like_message_id(like_id, str(like_message.id), str(likes_channel.id))
                        else:
                            # メッセージ参照がない場合は従来通り
                            like_embed = discord.Embed(
                                title=f"❤️ いいね：{interaction.user.display_name}",
                                description=f"**投稿ID: {post_id}**\n\n{post.get('content', '')}",
                                color=discord.Color.red()
                            )
                            like_embed.add_field(name="投稿者", value=post.get('display_name', '名無し'), inline=True)
                            like_embed.set_footer(text=f"いいねID: {like_id}")
                            like_message = await likes_channel.send(embed=like_embed)
                            self.file_manager.update_like_message_id(like_id, str(like_message.id), str(likes_channel.id))
                    except (json.JSONDecodeError, FileNotFoundError, discord.NotFound, discord.Forbidden):
                        # エラーの場合は従来通り
                        like_embed = discord.Embed(
                            title=f"❤️ いいね：{interaction.user.display_name}",
                            description=f"**投稿ID: {post_id}**\n\n{post.get('content', '')}",
                            color=discord.Color.red()
                        )
                        like_embed.add_field(name="投稿者", value=post.get('display_name', '名無し'), inline=True)
                        like_embed.set_footer(text=f"いいねID: {like_id}")
                        like_message = await likes_channel.send(embed=like_embed)
                        self.file_manager.update_like_message_id(like_id, str(like_message.id), str(likes_channel.id))
                else:
                    # メッセージ参照ファイルがない場合は従来通り
                    like_embed = discord.Embed(
                        title=f"❤️ いいね：{interaction.user.display_name}",
                        description=f"**投稿ID: {post_id}**\n\n{post.get('content', '')}",
                        color=discord.Color.red()
                    )
                    like_embed.add_field(name="投稿者", value=post.get('display_name', '名無し'), inline=True)
                    like_embed.set_footer(text=f"いいねID: {like_id}")
                    like_message = await likes_channel.send(embed=like_embed)
                    self.file_manager.update_like_message_id(like_id, str(like_message.id), str(likes_channel.id))
            
            # 専用チャンネルへの転送のみで完了
            await interaction.followup.send(
                f"✅ いいねしました！\n\n"
                f"投稿ID: {post_id}\n"
                f"いいねID: {like_id}\n"
                f"投稿者: {post.get('display_name', '名無し')}\n"
                f"内容: {post.get('content', '')[:100]}{'...' if len(post.get('content', '')) > 100 else ''}",
                ephemeral=True
            )
            
            logger.info(f"いいねが作成されました: 投稿ID={post_id}, いいねID={like_id}, ユーザーID={interaction.user.id}")
            
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
        logger.info("Like cog が初期化されました")
    
    @app_commands.command(name='like', description='❤️ 投稿にいいねする')
    async def like_command(self, interaction: Interaction) -> None:
        """いいねコマンド"""
        try:
            await interaction.response.send_modal(LikeModal())
        except Exception as e:
            logger.error(f"いいねモーダル表示中にエラーが発生しました: {e}", exc_info=True)
            await interaction.response.send_message(
                "❌ **エラーが発生しました**\n\n"
                "モーダルの表示中にエラーが発生しました。もう一度お試しください。",
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
