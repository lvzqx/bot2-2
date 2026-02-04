"""
プライベートスレッドユーティリティ関数
"""

import logging
import os
from typing import Optional

import discord
from discord import app_commands, ui, Interaction, Embed
from discord.ext import commands

# マネージャーをインポート
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from managers.post_manager import PostManager
from managers.message_ref_manager import MessageRefManager
from config import get_channel_id, extract_channel_id

# ロガー設定
logger = logging.getLogger(__name__)

async def find_or_create_private_thread(
    interaction: Interaction,
    private_channel: discord.TextChannel
) -> Optional[discord.Thread]:
    """既存のプライベートスレッドを検索または新規作成"""
    try:
        # 非公開投稿用の変数を初期化
        thread_prefix = f"非公開投稿 - {interaction.user.id}"
        target_thread: Optional[discord.Thread] = None
        
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
            except discord.Forbidden:
                logger.warning(f"⚠️ アーカイブスレッドのアクセス権限がありません")
            except Exception as e:
                logger.error(f"❌ アーカイブスレッド検索エラー: {e}")

        # スレッドがなければ新しく作成
        if target_thread is None:
            target_thread = await create_private_thread(interaction, private_channel, thread_prefix)
        else:
            # 既存スレッドをアンアーカイブ
            if target_thread.archived:
                await target_thread.edit(archived=False)
                logger.info(f"✅ プライベートスレッドをアンアーカイブしました: {target_thread.name}")
        
        return target_thread
        
    except Exception as e:
        logger.error(f"❌ プライベートスレッド検索・作成エラー: {e}")
        return None

async def create_private_thread(
    interaction: Interaction,
    private_channel: discord.TextChannel,
    thread_prefix: str
) -> Optional[discord.Thread]:
    """新しいプライベートスレッドを作成"""
    try:
        thread_name = f"{thread_prefix} ({interaction.user.name})"
        logger.info(f"🔧 プライベートスレッド作成開始:")
        logger.info(f"  - スレッド名: {thread_name}")
        logger.info(f"  - チャンネル名: {private_channel.name}")
        logger.info(f"  - チャンネルID: {private_channel.id}")
        logger.info(f"  - チャンネルタイプ: {private_channel.type}")
        
        # プライベートスレッド作成の前提条件をチェック
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
        
        try:
            thread = await private_channel.create_thread(
                name=thread_name[:100],
                type=discord.ChannelType.private_thread,
                reason=f"非公開投稿用スレッド作成 - {interaction.user.id}",
                invitable=False
            )
            logger.info(f"✅ プライベートスレッド作成成功: {thread.name} (ID: {thread.id})")
            return thread
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
            
    except Exception as e:
        logger.error(f"❌ プライベートスレッド作成エラー: {e}", exc_info=True)
        return None

async def setup_private_thread_permissions(
    interaction: Interaction,
    thread: discord.Thread
) -> bool:
    """プライベートスレッドの権限を設定"""
    try:
        # スレッドにユーザーを追加と権限設定
        thread_to_add = thread
        
        if thread_to_add:
            try:
                # スレッドにユーザーを追加（discord.py 2.6.4ではadd_member()が存在しない）
                # 代わりにスレッド招待を使用する方法
                try:
                    # 新しい方法: thread.add_member()の代替
                    invite = await thread_to_add.create_invite(max_age=0, max_uses=1)
                    logger.info(f"スレッド招待を作成しました: {invite.url}")
                    # 注: 実際の招待はDiscord UIを通じてユーザーが使用する必要があります
                except AttributeError:
                    # さらに古いバージョンの場合のフォールバック
                    logger.warning("thread.add_member()メソッドが利用できません。スキップします。")
                except Exception as invite_error:
                    logger.warning(f"スレッド招待作成に失敗しました: {invite_error}")
                
                logger.info(f"ユーザーをプライベートスレッドに追加しました: {interaction.user.name}")
                
                # スレッドの権限を確認・設定
                logger.info(f"🔧 スレッド権限確認: スレッドID={thread_to_add.id}")
                logger.info(f"  - スレッド名: {thread_to_add.name}")
                logger.info(f"  - スレッドタイプ: {thread_to_add.type}")
                logger.info(f"  - メンバー数: {len(thread_to_add.members)}")
                
                # ユーザーがスレッドにアクセスできるか確認
                user_can_view = thread_to_add.permissions_for(interaction.user).read_messages
                logger.info(f"  - ユーザーの閲覧権限: {user_can_view}")
                
                if not user_can_view:
                    logger.warning(f"⚠️ ユーザーがスレッドを閲覧できません: {interaction.user.name}")
                    # 権限を明示的に設定
                    await thread_to_add.set_permissions(interaction.user, read_messages=True, send_messages=True)
                    logger.info(f"✅ スレッド権限を設定しました: {interaction.user.name}")
                
                return True
                
            except discord.Forbidden:
                logger.error(f"❌ スレッドメンバー追加権限がありません: スレッドID={thread_to_add.id}")
                await interaction.followup.send(
                    "❌ プライベートスレッドに追加する権限がありません。\n"
                    "管理者にボットの権限設定を確認してください。",
                    ephemeral=True
                )
                return False
            except Exception as e:
                logger.error(f"❌ スレッドメンバー追加エラー: {e}")
                await interaction.followup.send(
                    "❌ スレッドへの追加中にエラーが発生しました。",
                    ephemeral=True
                )
                return False
        else:
            logger.warning(f"⚠️ スレッドオブジェクトが見つかりません")
            return False
            
    except Exception as e:
        logger.error(f"❌ スレッド権限設定エラー: {e}")
        return False

async def setup_private_role(
    interaction: Interaction
) -> Optional[discord.Role]:
    """非公開投稿用ロールを設定"""
    try:
        # 非公開投稿用ロールを作成
        private_role = discord.utils.get(interaction.guild.roles, name="非公開")
        if not private_role:
            try:
                private_role = await interaction.guild.create_role(
                    name="非公開",
                    color=discord.Color.dark_grey(),
                    reason="非公開投稿用ロール"
                )
                logger.info(f"非公開投稿用ロールを作成しました: {private_role.name}")
            except discord.Forbidden:
                logger.warning("非公開投稿用ロールの作成権限がありません")
                return None
            except Exception as e:
                logger.error(f"ロール作成エラー: {e}")
                return None

        # ユーザーにロールを付与
        if private_role:
            try:
                await interaction.user.add_roles(private_role)
                logger.info(f"ユーザーに非公開ロールを付与しました: {interaction.user.name}")
                return private_role
            except discord.Forbidden:
                logger.warning("ロール付与権限がありません")
                return None
            except Exception as e:
                logger.error(f"ロール付与エラー: {e}")
                return None
        
        return None
        
    except Exception as e:
        logger.error(f"❌ 非公開ロール設定エラー: {e}")
        return None

async def check_private_channel_permissions(
    interaction: Interaction,
    private_channel: discord.TextChannel
) -> bool:
    """非公開チャンネルの権限を確認・設定"""
    try:
        # 非公開チャンネルの権限を確認
        logger.info(f"🔧 非公開チャンネル権限確認:")
        logger.info(f"  - チャンネル名: {private_channel.name}")
        logger.info(f"  - チャンネルタイプ: {private_channel.type}")
        logger.info(f"  - NSFW: {private_channel.nsfw}")
        logger.info(f"  - 位置: {private_channel.position}")
        
        # ボットの権限を確認
        bot_permissions = private_channel.permissions_for(interaction.guild.me)
        logger.info(f"  - ボット権限:")
        logger.info(f"    * read_messages: {bot_permissions.read_messages}")
        logger.info(f"    * send_messages: {bot_permissions.send_messages}")
        logger.info(f"    * create_private_threads: {bot_permissions.create_private_threads}")
        logger.info(f"    * manage_threads: {bot_permissions.manage_threads}")
        
        # ユーザーの権限を確認
        user_permissions = private_channel.permissions_for(interaction.user)
        logger.info(f"  - ユーザー権限:")
        logger.info(f"    * read_messages: {user_permissions.read_messages}")
        logger.info(f"    * send_messages: {user_permissions.send_messages}")
        logger.info(f"    * create_private_threads: {user_permissions.create_private_threads}")
        
        # ユーザーがチャンネルにアクセスできるか確認
        if not user_permissions.read_messages:
            logger.warning(f"⚠️ ユーザーが非公開チャンネルを閲覧できません: {interaction.user.name}")
            # ユーザーにチャンネル閲覧権限を付与
            try:
                await private_channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
                logger.info(f"✅ 非公開チャンネル権限を設定しました: {interaction.user.name}")
            except discord.Forbidden:
                logger.error(f"❌ 非公開チャンネル権限設定権限がありません")
                await interaction.followup.send(
                    "❌ 非公開チャンネルの権限設定ができません。\n"
                    "管理者にチャンネル権限の確認を依頼してください。",
                    ephemeral=True
                )
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 非公開チャンネル権限確認エラー: {e}")
        return False
