import logging
from typing import Optional, Dict, Any

import discord
from discord import app_commands, ui, Interaction, Embed

# マネージャーをインポート
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from managers.post_manager import PostManager
from managers.message_ref_manager import MessageRefManager
from config import get_channel_id, DEFAULT_AVATAR, extract_channel_id

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
        else:
            embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)
        
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
                return False
            
            if not permissions.send_messages:
                logger.error(f"❌ ボットにメッセージ送信権限がありません")
                await interaction.followup.send(
                    "❌ ボットにメッセージを送信する権限がありません。\n"
                    "管理者にボットの権限設定を確認してください。",
                    ephemeral=True
                )
                return False
            
            try:
                thread = await private_channel.create_thread(
                    name=thread_name[:100],
                    type=discord.ChannelType.private_thread,
                    reason=f"非公開投稿用スレッド作成 - {interaction.user.id}",
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
                return False
            except discord.HTTPException as e:
                logger.error(f"❌ スレッド作成中にHTTPエラー: {e}", exc_info=True)
                logger.error(f"❌ エラーステータス: {e.status if hasattr(e, 'status') else 'Unknown'}")
                logger.error(f"❌ エラーテキスト: {e.text if hasattr(e, 'text') else 'Unknown'}")
                
                await interaction.followup.send(
                    "❌ スレッドの作成中にエラーが発生しました。",
                    ephemeral=True
                )
                return False
            except Exception as e:
                logger.error(f"❌ 予期せぬスレッド作成エラー: {e}", exc_info=True)
                await interaction.followup.send(
                    "❌ スレッド作成中に予期せぬエラーが発生しました。",
                    ephemeral=True
                )
                return False
            
            channel = thread
        else:
            # 既存スレッドをアンアーカイブ
            if target_thread.archived:
                await target_thread.edit(archived=False)
            channel = target_thread

        # メッセージを作成
        embed = discord.Embed(
            description=message,
            color=discord.Color.purple()
        )
        
        # 投稿者情報を設定
        if is_anonymous:
            embed.set_author(name="匿名ユーザー", icon_url=DEFAULT_AVATAR)
        else:
            embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)
        
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
        
        # DBにはスレッドIDを保存
        channel = thread if 'thread' in locals() else channel
        
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
            except Exception as e:
                logger.error(f"ロール作成エラー: {e}")

        # ユーザーにロールを付与
        if private_role:
            try:
                await interaction.user.add_roles(private_role)
                logger.info(f"ユーザーに非公開ロールを付与しました: {interaction.user.name}")
            except discord.Forbidden:
                logger.warning("ロール付与権限がありません")
            except Exception as e:
                logger.error(f"ロール付与エラー: {e}")

        # スレッドにユーザーを追加と権限設定
        thread_to_add = None
        if 'thread' in locals():
            thread_to_add = thread
        elif hasattr(channel, 'type') and channel.type == discord.ChannelType.private_thread:
            thread_to_add = channel
        
        if thread_to_add:
            try:
                # スレッドにユーザーを追加
                await thread_to_add.add_member(interaction.user)
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
            logger.info(f"  - channel type: {type(channel)}")
            logger.info(f"  - channel id: {channel.id}")
            if hasattr(channel, 'type'):
                logger.info(f"  - channel discord type: {channel.type}")
        
        return True
        
    except Exception as e:
        logger.error(f"非公開投稿作成中にエラー: {e}", exc_info=True)
        return False
