"""
投稿ユーティリティ関数
"""

import logging
import os
from typing import Optional, Dict, Any

import discord
from discord import app_commands, ui, Interaction, Embed
from discord.ext import commands

# マネージャーをインポート
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from managers.post_manager import PostManager
from managers.message_ref_manager import MessageRefManager
from config import get_channel_id, DEFAULT_AVATAR, extract_channel_id

# プライベートスレッドユーティリティをインポート
from .private_thread_utils import (
    find_or_create_private_thread,
    setup_private_thread_permissions,
    check_private_channel_permissions
)

# ロガーの設定
logger = logging.getLogger(__name__)

async def create_public_post(
    interaction: Interaction,
    message: str,
    category: Optional[str],
    image_url: Optional[str],
    is_anonymous: bool,
    display_name: Optional[str],
    post_id: int,
    cog
) -> bool:
    """公開投稿を作成する"""
    try:
        # 公開チャンネルに投稿
        channel_url = get_channel_id('public')
        channel_id = extract_channel_id(channel_url)
        channel = interaction.guild.get_channel(channel_id)
        if not channel:
            raise ValueError("公開チャンネルが見つかりません")
        
        # メッセージを作成
        embed = discord.Embed(
            description=message,
            color=discord.Color.blue()
        )
        
        # 投稿者情報を設定
        if is_anonymous:
            embed.set_author(name="匿名ユーザー", icon_url=DEFAULT_AVATAR)
        elif display_name:
            embed.set_author(name=display_name, icon_url=DEFAULT_AVATAR)
        else:
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        
        # 画像URLがあれば設定
        if image_url:
            embed.set_image(url=image_url)

        footer_parts = []
        if category:
            footer_parts.append(f"カテゴリー: {category}")
        footer_parts.append(f"投稿ID: {post_id}")
        # UIDは表示しない
        embed.set_footer(text=" | ".join(footer_parts))
        
        # メッセージを送信
        sent_message = await channel.send(embed=embed)
        
        # メッセージ送信成功後にmessage_refを更新
        if sent_message:
            cog.message_ref_manager.save_message_ref(post_id, str(sent_message.id), str(sent_message.channel.id), str(interaction.user.id))
            logger.info(f"メッセージ参照を保存しました: 投稿ID={post_id}")
            
            # 投稿データのmessage_idとchannel_idを更新
            try:
                cog.post_manager.update_post_message_ref(post_id, str(sent_message.id), str(sent_message.channel.id))
            except Exception as e:
                logger.warning(f"投稿のmessage_ref更新中にエラー: {e}")
        else:
            logger.error(f"❌ メッセージ送信に失敗しました: 投稿ID={post_id}")
            await interaction.followup.send(
                "❌ メッセージ送信に失敗しました。もう一度お試しください。",
                ephemeral=True
            )
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"公開投稿作成中にエラー: {e}", exc_info=True)
        return False

async def create_private_post(
    interaction: Interaction,
    message: str,
    category: Optional[str],
    image_url: Optional[str],
    is_anonymous: bool,
    display_name: Optional[str],
    post_id: int,
    cog
) -> bool:
    """非公開投稿を作成する"""
    try:
        # 非公開チャンネルに投稿
        private_channel_url = get_channel_id('private')
        private_channel_id = extract_channel_id(private_channel_url)
        logger.info(f"非公開チャンネルURL: {private_channel_url}")
        logger.info(f"非公開チャンネルID: {private_channel_id}")
        logger.info(f"サーバーID: {interaction.guild.id if interaction.guild else 'None'}")
        logger.info(f"ボットID: {interaction.client.user.id if interaction.client.user else 'None'}")
        
        private_channel = interaction.guild.get_channel(private_channel_id)
        if not private_channel:
            logger.error(f"❌ 非公開チャンネルが見つかりません: ID={private_channel_id}")
            logger.error(f"❌ 利用可能なチャンネル一覧:")
            for channel in interaction.guild.text_channels:
                logger.error(f"  - {channel.name} (ID: {channel.id})")
            raise ValueError("非公開チャンネルが見つかりません")
        
        logger.info(f"✅ 非公開チャンネル取得成功: {private_channel.name} (ID: {private_channel.id})")
        
        # 非公開チャンネルの権限を確認・設定
        if not await check_private_channel_permissions(interaction, private_channel):
            return False
        
        # プライベートスレッドを検索または作成
        thread = await find_or_create_private_thread(interaction, private_channel)
        if not thread:
            logger.error(f"❌ プライベートスレッドの作成に失敗しました")
            return False
        
        # メッセージを作成
        embed = discord.Embed(
            description=message,
            color=discord.Color.purple()
        )
        
        # 投稿者情報を設定
        if is_anonymous:
            embed.set_author(name="匿名ユーザー", icon_url=DEFAULT_AVATAR)
        elif display_name:
            embed.set_author(name=display_name, icon_url=DEFAULT_AVATAR)
        else:
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        
        # 画像URLがあれば設定
        if image_url:
            embed.set_image(url=image_url)

        footer_parts = []
        if category:
            footer_parts.append(f"カテゴリー: {category}")
        footer_parts.append(f"投稿ID: {post_id}")
        # UIDは表示しない
        embed.set_footer(text=" | ".join(footer_parts))
        
        # メッセージを送信
        sent_message = await thread.send(embed=embed)
        
        # 非公開投稿のmessage_refを保存
        if sent_message:
            cog.message_ref_manager.save_message_ref(post_id, str(sent_message.id), str(sent_message.channel.id), str(interaction.user.id))
            logger.info(f"メッセージ参照を保存しました: 投稿ID={post_id}")
            
            # 投稿データのmessage_idとchannel_idを更新
            try:
                cog.post_manager.update_post_message_ref(post_id, str(sent_message.id), str(sent_message.channel.id))
            except Exception as e:
                logger.warning(f"投稿のmessage_ref更新中にエラー: {e}")
        else:
            logger.error(f"❌ 非公開メッセージ送信に失敗しました: 投稿ID={post_id}")
            await interaction.followup.send(
                "❌ 非公開メッセージ送信に失敗しました。もう一度お試しください。",
                ephemeral=True
            )
            return False

        # スレッド権限を設定
        if not await setup_private_thread_permissions(interaction, thread):
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"非公開投稿作成中にエラー: {e}", exc_info=True)
        
        # ユーザーに分かりやすいエラーメッセージを送信
        error_msg = "❌ **非公開投稿の作成に失敗しました**\n\n"
        
        if "見つかりません" in str(e):
            error_msg += "原因: 非公開チャンネルが見つかりません\n"
            error_msg += "解決策: 管理者にチャンネル設定を確認してください\n\n"
        elif "権限" in str(e) or "Forbidden" in str(e):
            error_msg += "原因: ボットに必要な権限がありません\n"
            error_msg += "解決策: 管理者にボット権限の確認を依頼してください\n\n"
        elif "スレッド" in str(e):
            error_msg += "原因: プライベートスレッドの作成に失敗しました\n"
            error_msg += "解決策: サーバーでプライベートスレッドが有効か確認してください\n\n"
        else:
            error_msg += f"原因: {str(e)}\n\n"
        
        error_msg += "必要な権限:\n"
        error_msg += "• メッセージを送信\n"
        error_msg += "• プライベートスレッドを作成\n"
        error_msg += "• スレッドを管理\n"
        error_msg += "• ロールを管理"
        
        try:
            await interaction.followup.send(error_msg, ephemeral=True)
        except:
            logger.error("エラーメッセージの送信にも失敗しました")
        
        return False
