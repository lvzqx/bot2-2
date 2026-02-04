"""
編集ロジック
"""

import discord
from discord import app_commands, ui, Interaction, Embed
from discord.ext import commands
import logging
from typing import Optional

# マネージャーをインポート
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from managers.post_manager import PostManager
from managers.message_ref_manager import MessageRefManager

logger = logging.getLogger(__name__)

async def update_post_embed(
    interaction: Interaction,
    message_id: str,
    channel_id: str,
    message: str,
    category: Optional[str],
    image_url: Optional[str],
    post_id: int,
    message_ref_manager: MessageRefManager
) -> bool:
    """DiscordのEmbedメッセージを更新"""
    try:
        # 元の投稿チャンネルを取得
        channel = interaction.guild.get_channel(int(channel_id))
        if not channel:
            logger.error(f"❌ チャンネルが見つかりません: channel_id={channel_id}")
            return False
        
        # 元の投稿メッセージを取得
        try:
            original_message = await channel.fetch_message(int(message_id))
        except discord.NotFound:
            logger.warning(f"⚠️ 元の投稿メッセージが見つかりません: message_id={message_id}")
            return False
        except discord.Forbidden:
            logger.error(f"❌ メッセージ取得権限がありません: message_id={message_id}")
            return False
        
        # 新しいEmbedを作成
        embed = discord.Embed(
            description=message,
            color=discord.Color.blue()
        )
        
        # 投稿者情報を設定（元のEmbedから取得）
        if original_message.embeds:
            original_embed = original_message.embeds[0]
            if original_embed.author:
                embed.set_author(
                    name=original_embed.author.name,
                    icon_url=original_embed.author.icon_url
                )
        
        # 画像URLがあれば設定
        if image_url:
            embed.set_image(url=image_url)
        
        # フッターを設定
        footer_parts = []
        if category:
            footer_parts.append(f"カテゴリー: {category}")
        footer_parts.append(f"投稿ID: {post_id}")
        embed.set_footer(text=" | ".join(footer_parts))
        
        # メッセージを更新
        await original_message.edit(embed=embed)
        logger.info(f"✅ Embedメッセージを更新しました: message_id={message_id}")
        
        return True
        
    except discord.Forbidden:
        logger.error(f"❌ メッセージ更新権限がありません: message_id={message_id}")
        return False
    except discord.HTTPException as e:
        logger.error(f"❌ メッセージ更新HTTPエラー: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ メッセージ更新エラー: {e}")
        return False

async def update_post_data(
    post_id: int,
    message: str,
    category: Optional[str],
    image_url: Optional[str],
    post_manager: PostManager
) -> bool:
    """投稿データを更新"""
    try:
        # 投稿を更新
        success = post_manager.update_post(
            post_id=post_id,
            content=message,
            category=category,
            image_url=image_url
        )
        
        if success:
            logger.info(f"✅ 投稿データを更新しました: post_id={post_id}")
        else:
            logger.error(f"❌ 投稿データの更新に失敗しました: post_id={post_id}")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ 投稿データ更新エラー: {e}")
        return False
