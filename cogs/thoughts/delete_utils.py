"""
削除ユーティリティ関数
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

# ロガー設定
logger = logging.getLogger(__name__)

async def delete_discord_message(
    interaction: Interaction,
    message_id: str,
    channel_id: str,
    message_ref_manager: MessageRefManager
) -> bool:
    """Discordメッセージを削除する"""
    try:
        if message_id and channel_id:
            # 元の投稿チャンネルを取得
            original_channel = interaction.guild.get_channel(int(channel_id))
            if not original_channel:
                logger.error(f"❌ チャンネルが見つかりません: channel_id={channel_id}")
                return False
            
            logger.info(f"🔧 チャンネルを取得しました: ID={channel_id}, タイプ={type(original_channel)}")
            
            # プライベートスレッドの場合は特別処理
            if hasattr(original_channel, 'type') and original_channel.type == discord.ChannelType.private_thread:
                # これはプライベートスレッド自体
                thread = original_channel
                logger.info(f"🔧 プライベートスレッドを直接削除します: スレッドID={thread.id}")
                logger.info(f"🔧 スレッド名: {thread.name}")
                
                try:
                    # スレッドをアーカイブしてから削除
                    logger.info(f"🔧 スレッドをアーカイブします...")
                    await thread.edit(archived=True, locked=True)
                    logger.info(f"🔧 スレッドを削除します...")
                    await thread.delete()
                    logger.info(f"✅ プライベートスレッドを削除しました: スレッドID={thread.id}")
                    return True
                except discord.Forbidden:
                    logger.error(f"❌ プライベートスレッドの削除権限がありません: スレッドID={thread.id}")
                    return False
                except discord.HTTPException as e:
                    logger.error(f"❌ スレッド削除HTTPエラー: {e}")
                    return False
                except Exception as e:
                    logger.error(f"❌ プライベートスレッド削除エラー: {e}")
                    return False
            else:
                # 通常チャンネルの場合
                # 元の投稿メッセージを削除
                try:
                    original_message = await original_channel.fetch_message(int(message_id))
                except discord.NotFound:
                    logger.warning(f"⚠️ メッセージが見つかりません: message_id={message_id}")
                    return False
                except discord.Forbidden:
                    logger.error(f"❌ メッセージ取得権限がありません: message_id={message_id}")
                    return False
                except Exception as e:
                    logger.error(f"❌ メッセージ取得エラー: {e}")
                    return False
                
                logger.info(f"🔧 メッセージを取得しました: メッセージID={message_id}")
                logger.info(f"🔧 メッセージチャンネルタイプ: {type(original_message.channel)}")
                logger.info(f"🔧 メッセージチャンネルID: {original_message.channel.id}")
                
                # メッセージがスレッド内にあるかチェック
                if hasattr(original_message.channel, 'type') and original_message.channel.type == discord.ChannelType.private_thread:
                    # これはスレッド内のメッセージ
                    thread = original_message.channel
                    logger.info(f"🔧 スレッド内メッセージを検出しました: スレッドID={thread.id}")
                    
                    try:
                        # スレッドをアーカイブしてから削除
                        logger.info(f"🔧 スレッドをアーカイブします...")
                        await thread.edit(archived=True, locked=True)
                        logger.info(f"🔧 スレッドを削除します...")
                        await thread.delete()
                        logger.info(f"✅ プライベートスレッドを削除しました: スレッドID={thread.id}")
                        return True
                    except discord.Forbidden:
                        logger.error(f"❌ プライベートスレッドの削除権限がありません: スレッドID={thread.id}")
                        return False
                    except discord.HTTPException as e:
                        logger.error(f"❌ スレッド削除HTTPエラー: {e}")
                        return False
                    except Exception as e:
                        logger.error(f"❌ プライベートスレッド削除エラー: {e}")
                        return False
                elif hasattr(original_message.channel, 'type') and original_message.channel.type == discord.ChannelType.public_thread:
                    # 公開スレッドの場合
                    thread = original_message.channel
                    logger.info(f"🔧 公開スレッドを検出しました: スレッドID={thread.id}")
                    
                    try:
                        # 公開スレッドも削除
                        await thread.edit(archived=True, locked=True)
                        await thread.delete()
                        logger.info(f"✅ 公開スレッドを削除しました: スレッドID={thread.id}")
                        return True
                    except discord.Forbidden:
                        logger.error(f"❌ 公開スレッドの削除権限がありません: スレッドID={thread.id}")
                        return False
                    except discord.HTTPException as e:
                        logger.error(f"❌ 公開スレッド削除HTTPエラー: {e}")
                        return False
                    except Exception as e:
                        logger.error(f"❌ 公開スレッド削除エラー: {e}")
                        return False
                else:
                    # 通常のメッセージの場合
                    logger.info(f"🔧 通常メッセージを削除します: チャンネルID={original_channel.id}")
                    try:
                        await original_message.delete()
                        logger.info(f"✅ 元の投稿メッセージを削除しました: メッセージID={message_id}")
                        return True
                    except discord.Forbidden:
                        logger.error(f"❌ メッセージ削除権限がありません: メッセージID={message_id}")
                        return False
                    except discord.HTTPException as e:
                        logger.error(f"❌ メッセージ削除HTTPエラー: {e}")
                        return False
                    except Exception as e:
                        logger.error(f"❌ メッセージ削除エラー: {e}")
                        return False
        else:
            logger.warning(f"⚠️ メッセージIDまたはチャンネルIDがありません: message_id={message_id}, channel_id={channel_id}")
            return False
            
    except discord.NotFound:
        logger.warning(f"⚠️ 元の投稿メッセージが見つかりません: message_id={message_id}")
        return False
    except discord.Forbidden:
        logger.error(f"❌ 元の投稿メッセージの削除権限がありません: message_id={message_id}")
        return False
    except Exception as e:
        logger.error(f"❌ 元の投稿メッセージ削除エラー: {e}")
        return False

def cleanup_message_ref(post_id: int, message_ref_manager: MessageRefManager) -> bool:
    """message_refをクリーンアップ"""
    try:
        message_ref_manager.delete_message_ref(post_id)
        logger.info(f"✅ message_refをクリーンアップしました: 投稿ID={post_id}")
        return True
    except Exception as e:
        logger.error(f"❌ message_refクリーンアップ中にエラー: {e}")
        return False
