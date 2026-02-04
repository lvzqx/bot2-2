"""
リプライ編集ロジック
"""

import discord
from discord import app_commands, ui, Interaction, Embed
from discord.ext import commands
import logging

# マネージャーをインポート
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from managers.reply_manager import ReplyManager
from managers.message_ref_manager import MessageRefManager

logger = logging.getLogger(__name__)

async def update_reply_embed(
    interaction: Interaction,
    message_id: str,
    channel_id: str,
    message: str,
    reply_id: int,
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
        
        # リプライEmbedを探して更新
        if original_message.embeds:
            for i, embed in enumerate(original_message.embeds):
                embed_footer = embed.footer.text if embed.footer else ""
                if f"リプライID: {reply_id}" in embed_footer:
                    # 新しいEmbedを作成
                    new_embed = discord.Embed(
                        description=message,
                        color=discord.Color.green()
                    )
                    
                    # 元のEmbedの情報を維持
                    if embed.author:
                        new_embed.set_author(
                            name=embed.author.name,
                            icon_url=embed.author.icon_url
                        )
                    
                    # フッターを更新
                    footer_parts = []
                    if "カテゴリー:" in embed_footer:
                        # カテゴリー情報を維持
                        for part in embed_footer.split(" | "):
                            if part.startswith("カテゴリー:"):
                                footer_parts.append(part)
                    footer_parts.append(f"リプライID: {reply_id}")
                    new_embed.set_footer(text=" | ".join(footer_parts))
                    
                    # Embedを更新
                    await original_message.edit(embeds=[new_embed])
                    logger.info(f"✅ リプライEmbedを更新しました: reply_id={reply_id}")
                    return True
        
        logger.warning(f"⚠️ リプライEmbedが見つかりませんでした: reply_id={reply_id}")
        return False
        
    except discord.Forbidden:
        logger.error(f"❌ メッセージ更新権限がありません: message_id={message_id}")
        return False
    except discord.HTTPException as e:
        logger.error(f"❌ メッセージ更新HTTPエラー: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ メッセージ更新エラー: {e}")
        return False

async def update_reply_data(
    reply_id: int,
    message: str,
    reply_manager: ReplyManager
) -> bool:
    """リプライデータを更新"""
    try:
        # リプライを更新
        success = reply_manager.update_reply(
            reply_id=reply_id,
            content=message
        )
        
        if success:
            logger.info(f"✅ リプライデータを更新しました: reply_id={reply_id}")
        else:
            logger.error(f"❌ リプライデータの更新に失敗しました: reply_id={reply_id}")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ リプライデータ更新エラー: {e}")
        return False
