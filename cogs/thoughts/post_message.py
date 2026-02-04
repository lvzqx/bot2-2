"""
メッセージ送信・Embed作成機能
"""

import discord
from discord import app_commands, Interaction
from discord.ext import commands
from discord import ui
import logging
import os
from typing import Optional, Dict, Any

from config import get_channel_id, extract_channel_id, DEFAULT_AVATAR
from managers.post_manager import PostManager

logger = logging.getLogger(__name__)

class PostMessageManager:
    """メッセージ送信管理クラス"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.post_manager = PostManager()
    
    def create_embed(self, message: str, category: Optional[str], post_id: int, 
                   is_anonymous: bool, user: discord.User, image_url: Optional[str] = None,
                   color: discord.Color = discord.Color.blue()) -> discord.Embed:
        """Embedを作成する"""
        embed = discord.Embed(
            description=message,
            color=color
        )
        
        # 投稿者情報を設定
        if is_anonymous:
            embed.set_author(name="匿名ユーザー", icon_url=DEFAULT_AVATAR)
        else:
            embed.set_author(name=str(user), icon_url=user.display_avatar.url)
        
        # 画像URLがあれば設定
        if image_url:
            embed.set_image(url=image_url)
        
        # フッターを設定
        footer_parts = []
        if category:
            footer_parts.append(f"カテゴリー: {category}")
        footer_parts.append(f"投稿ID: {post_id}")
        embed.set_footer(text=" | ".join(footer_parts))
        
        return embed
    
    async def send_public_message(self, interaction: Interaction, message: str, 
                                category: Optional[str], post_id: int, is_anonymous: bool,
                                image_url: Optional[str] = None) -> Optional[discord.Message]:
        """公開チャンネルにメッセージを送信する"""
        try:
            # 公開チャンネルを取得
            channel_url = get_channel_id('public')
            channel_id = extract_channel_id(channel_url)
            channel = interaction.guild.get_channel(channel_id)
            if not channel:
                raise ValueError("公開チャンネルが見つかりません")
            
            # Embedを作成
            embed = self.create_embed(
                message=message,
                category=category,
                post_id=post_id,
                is_anonymous=is_anonymous,
                user=interaction.user,
                image_url=image_url,
                color=discord.Color.blue()
            )
            
            # メッセージを送信
            sent_message = await channel.send(embed=embed)
            logger.info(f"✅ 公開メッセージ送信成功: メッセージID={sent_message.id}")
            
            return sent_message
            
        except Exception as e:
            logger.error(f"❌ 公開メッセージ送信エラー: {e}", exc_info=True)
            return None
    
    async def send_private_message(self, interaction: Interaction, thread: discord.Thread,
                                   message: str, category: Optional[str], post_id: int,
                                   is_anonymous: bool, image_url: Optional[str] = None) -> Optional[discord.Message]:
        """プライベートスレッドにメッセージを送信する"""
        try:
            # Embedを作成
            embed = self.create_embed(
                message=message,
                category=category,
                post_id=post_id,
                is_anonymous=is_anonymous,
                user=interaction.user,
                image_url=image_url,
                color=discord.Color.purple()
            )
            
            # メッセージを送信
            sent_message = await thread.send(embed=embed)
            logger.info(f"✅ 非公開メッセージ送信成功: メッセージID={sent_message.id}")
            
            return sent_message
            
        except Exception as e:
            logger.error(f"❌ 非公開メッセージ送信エラー: {e}", exc_info=True)
            return None
    
    async def send_success_message(self, interaction: Interaction, sent_message: discord.Message,
                                  post_id: int, category: Optional[str], is_anonymous: bool,
                                  is_public: bool = True):
        """成功メッセージを送信する"""
        try:
            if is_public:
                embed = discord.Embed(
                    title="✅ 投稿が完了しました！",
                    description=f"[メッセージにジャンプ]({sent_message.jump_url})",
                    color=discord.Color.green()
                )
                embed.add_field(name="ID", value=f"`{post_id}`", inline=True)
                if category:
                    embed.add_field(name="カテゴリ", value=f"`{category}`", inline=True)
                embed.add_field(name="表示名", value=f"`{'匿名' if is_anonymous else '表示'}`", inline=True)
                
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                # 非公開投稿の場合は既に送信済みなので何もしない
                pass
                
        except Exception as e:
            logger.error(f"❌ 成功メッセージ送信エラー: {e}")
    
    async def send_error_message(self, interaction: Interaction, error_message: str):
        """エラーメッセージを送信する"""
        try:
            await interaction.followup.send(
                f"❌ {error_message}",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"❌ エラーメッセージ送信エラー: {e}")
    
    async def save_message_ref(self, cog, post_id: int, sent_message: discord.Message, 
                               user_id: str):
        """メッセージ参照を保存する"""
        try:
            cog.message_ref_manager.save_message_ref(
                post_id, 
                str(sent_message.id), 
                str(sent_message.channel.id), 
                user_id
            )
            logger.info(f"メッセージ参照を保存しました: 投稿ID={post_id}")
            
            # 投稿データのmessage_idとchannel_idを更新
            try:
                from managers.post_manager import PostManager
                post_cog = PostManager()
                post_cog.update_post_message_ref(post_id, str(sent_message.id), str(sent_message.channel.id))
            except Exception as e:
                logger.warning(f"投稿のmessage_ref更新中にエラー: {e}")
                
        except Exception as e:
            logger.error(f"❌ メッセージ参照保存エラー: {e}")
    
    def validate_message_content(self, content: str) -> tuple[bool, str]:
        """メッセージ内容を検証する"""
        if not content or not content.strip():
            return False, "メッセージ内容を入力してください。"
        
        if len(content) > 2000:
            return False, "メッセージは2000文字以内で入力してください。"
        
        return True, ""
    
    def validate_image_url(self, image_url: str) -> tuple[bool, str]:
        """画像URLを検証する"""
        if not image_url:
            return True, ""  # 画像は任意
        
        # 簡単なURL形式チェック
        if not (image_url.startswith('http://') or image_url.startswith('https://')):
            return False, "画像URLはhttp://またはhttps://で始まる必要があります。"
        
        return True, ""
