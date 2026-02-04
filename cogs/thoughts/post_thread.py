"""
プライベートスレッド作成・管理機能
"""

import discord
from discord import app_commands, Interaction
from discord.ext import commands
from discord import ui
import logging
import os
from typing import Optional, Dict, Any

from config import get_channel_id, extract_channel_id
from managers.post_manager import PostManager

logger = logging.getLogger(__name__)

class PostThreadManager:
    """プライベートスレッド管理クラス"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.post_manager = PostManager()
    
    async def create_private_thread(self, interaction: Interaction, user_id: str, post_id: int) -> Optional[discord.Thread]:
        """プライベートスレッドを作成する"""
        try:
            # 非公開チャンネル情報を取得
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
            
            # スレッドプレフィックス
            thread_prefix = f"非公開投稿 - {user_id}"
            thread_name = f"{thread_prefix} ({interaction.user.name})"
            
            logger.info(f"🔧 プライベートスレッド作成開始:")
            logger.info(f"  - スレッド名: {thread_name}")
            logger.info(f"  - チャンネル名: {private_channel.name}")
            logger.info(f"  - チャンネルID: {private_channel.id}")
            logger.info(f"  - チャンネルタイプ: {private_channel.type}")
            
            # 権限チェック
            permissions = private_channel.permissions_for(interaction.guild.me)
            logger.info(f"  - 公開スレッド作成権限: {permissions.create_public_threads}")
            logger.info(f"  - プライベートスレッド作成権限: {permissions.create_private_threads}")
            logger.info(f"  - メッセージ送信権限: {permissions.send_messages}")
            logger.info(f"  - スレッド管理権限: {permissions.manage_threads}")
            
            # 権限がない場合は早期リターン
            if not permissions.create_private_threads:
                logger.error(f"❌ ボットにプライベートスレッド作成権限がありません")
                await interaction.followup.send(
                    "❌ ボットにプライベートスレッドを作成する権限がありません。\n"
                    "管理者にボットの権限設定を確認してください。",
                    ephemeral=True
                )
                return None
            
            if not permissions.send_messages:
                logger.error(f"❌ ボットにメッセージ送信権限がありません")
                await interaction.followup.send(
                    "❌ ボットにメッセージを送信する権限がありません。\n"
                    "管理者にボットの権限設定を確認してください。",
                    ephemeral=True
                )
                return None
            
            # 既存スレッドを検索
            target_thread = await self.find_existing_thread(private_channel, thread_prefix)
            
            if target_thread:
                thread = target_thread
                try:
                    if thread.archived:
                        await thread.edit(archived=False, locked=False)
                        logger.info(f"✅ アーカイブされたスレッドを復元しました: {thread.name}")
                except Exception as e:
                    logger.warning(f"スレッドの復元中にエラー: {e}")
            else:
                # 新しく作成
                try:
                    thread = await private_channel.create_thread(
                        name=thread_name[:100],
                        type=discord.ChannelType.private_thread,
                        reason=f"非公開投稿用スレッド作成 - {user_id}",
                        invitable=False
                    )
                    logger.info(f"✅ プライベートスレッド作成成功: {thread.name} (ID: {thread.id})")
                except discord.Forbidden as e:
                    logger.error(f"❌ プライベートスレッド作成権限なし: {e}")
                    logger.error(f"❌ ボット権限確認:")
                    try:
                        permissions = private_channel.permissions_for(interaction.guild.me)
                        logger.error(f"  - create_public_threads: {permissions.create_public_threads}")
                        logger.error(f"  - create_private_threads: {permissions.create_private_threads}")
                        logger.error(f"  - send_messages: {permissions.send_messages}")
                        logger.error(f"  - manage_threads: {permissions.manage_threads}")
                        logger.error(f"  - manage_channels: {permissions.manage_channels}")
                    except Exception as perm_error:
                        logger.error(f"❌ 権限確認エラー: {perm_error}")
                    
                    # チャンネルのスレッド設定を確認
                    logger.error(f"❌ チャンネル設定確認:")
                    logger.error(f"  - チャンネルタイプ: {private_channel.type}")
                    logger.error(f"  - NSFW: {private_channel.nsfw}")
                    logger.error(f"  - 位置: {private_channel.position}")
                    
                    await interaction.followup.send(
                        "❌ プライベートスレッドを作成する権限がありません。\n"
                        "管理者に以下の権限を確認してください:\n"
                        "• ボットに「プライベートスレッドを作成」権限\n"
                        "• 非公開チャンネルでプライベートスレッドが有効\n"
                        "• サーバーでプライベートスレッドが有効",
                        ephemeral=True
                    )
                    return None
                except discord.HTTPException as e:
                    logger.error(f"❌ スレッド作成中にHTTPエラー: {e}", exc_info=True)
                    logger.error(f"❌ エラーステータス: {e.status if hasattr(e, 'status') else 'Unknown'}")
                    logger.error(f"❌ エラーテキスト: {e.text if hasattr(e, 'text') else 'Unknown'}")
                    
                    await interaction.followup.send(
                        "❌ スレッドの作成中にエラーが発生しました。",
                        ephemeral=True
                    )
                    return None
                except Exception as e:
                    logger.error(f"❌ 予期せぬスレッド作成エラー: {e}", exc_info=True)
                    await interaction.followup.send(
                        "❌ スレッド作成中に予期せぬエラーが発生しました。",
                        ephemeral=True
                    )
                    return None
            
            # ユーザーをスレッドに追加
            await thread.add_user(interaction.user)
            
            # 非公開投稿用ロールを作成・管理
            await self.manage_private_role(interaction, thread)
            
            return thread
            
        except Exception as e:
            logger.error(f"❌ プライベートスレッド作成中にエラー: {e}", exc_info=True)
            return None
    
    async def find_existing_thread(self, private_channel: discord.TextChannel, thread_prefix: str) -> Optional[discord.Thread]:
        """既存のスレッドを検索する"""
        target_thread = None
        
        # アクティブスレッドから検索
        for t in private_channel.threads:
            if t.name.startswith(thread_prefix):
                target_thread = t
                break
        
        # アーカイブされたスレッドからも検索
        if target_thread is None:
            try:
                async for t in private_channel.archived_threads(private=True, limit=50):
                    if t.name.startswith(thread_prefix):
                        target_thread = t
                        break
            except Exception as e:
                logger.warning(f"アーカイブスレッドの検索中にエラー: {e}")
        
        return target_thread
    
    async def manage_private_role(self, interaction: Interaction, thread: discord.Thread):
        """非公開投稿用ロールを管理する"""
        try:
            # 非公開投稿用ロールを作成
            private_role = discord.utils.get(interaction.guild.roles, name="非公開")
            if not private_role:
                private_role = await interaction.guild.create_role(
                    name="非公開",
                    reason="非公開投稿用ロール作成"
                )
                logger.info(f"✅ 非公開ロールを作成しました: {private_role.name}")
            
            # 投稿者にロールを付与
            member = interaction.guild.get_member(interaction.user.id)
            if member and private_role not in member.roles:
                await member.add_roles(private_role, reason="非公開投稿権限付与")
                logger.info(f"✅ ユーザーに非公開ロールを付与しました: {interaction.user.name}")
            
            # 非公開投稿用ロールをスレッドに追加
            for role_member in private_role.members:
                try:
                    await thread.add_user(role_member)
                except discord.HTTPException:
                    pass
            
            logger.info(f"✅ 非公開ロールのメンバーをスレッドに追加しました: {len(private_role.members)}人")
            
        except Exception as e:
            logger.error(f"❌ 非公開ロール管理中にエラー: {e}")
            # ロール管理のエラーはスレッド作成の失敗とはしない
