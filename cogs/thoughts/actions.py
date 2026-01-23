import logging
import sqlite3
import json
from typing import Dict, Any
from datetime import datetime

import discord
from discord import app_commands, ui, Interaction, Embed
from discord.ext import commands

logger = logging.getLogger(__name__)

class LikeModal(ui.Modal, title="❤️ いいねする投稿"):
    """いいねする投稿IDを入力するモーダル"""
    
    def __init__(self):
        super().__init__(timeout=300)
        
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
            import os
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'bot.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # thoughtsテーブルの存在確認
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='thoughts'")
            if not cursor.fetchone():
                await interaction.followup.send(
                    "データベースが初期化されていません。",
                    ephemeral=True
                )
                conn.close()
                return
            
            cursor.execute('SELECT content, user_id FROM thoughts WHERE id = ?', (post_id,))
            post = cursor.fetchone()
            
            if not post:
                await interaction.followup.send(
                    "投稿が見つかりませんでした。\n\n"
                    f"投稿ID: {post_id}\n"
                    "※正しい投稿IDを入力してください。",
                    ephemeral=True
                )
                conn.close()
                return
            
            post_content = post[0]
            post_user_id = post[1]
            
            # アクションを記録
            await self._log_action(interaction.user.id, 'like', post_id, {
                'post_content': post_content[:100],
                'post_user_id': post_user_id
            })
            
            # 元の投稿メッセージを取得
            cursor.execute('''
                SELECT message_id, channel_id 
                FROM message_references 
                WHERE post_id = ?
            ''', (post_id,))
            message_ref = cursor.fetchone()
            
            if message_ref:
                try:
                    # メッセージを取得してリアクションを追加
                    channel = interaction.guild.get_channel(int(message_ref[1]))
                    if channel:
                        message = await channel.fetch_message(int(message_ref[0]))
                        
                        # いいね処理
                        try:
                            # 新しいいいねメッセージを送信
                            like_message = f"❤️いいね：{interaction.user.display_name}"
                            await message.reply(like_message)
                            
                            await interaction.followup.send(
                                f"❤️ **いいねしました！**\n\n"
                                f"投稿にいいねしました！",
                                ephemeral=True
                            )
                        except discord.Forbidden:
                            await interaction.followup.send(
                                f"❤️ **いいねしました！**\n\n"
                                f"投稿にいいねしました！\n"
                                f"※権限がないため、メッセージを送信できませんでした。",
                                ephemeral=True
                            )
                        except Exception as e:
                            logger.error(f"いいねメッセージ送信中にエラー: {e}")
                            await interaction.followup.send(
                                f"❤️ **いいねしました！**\n\n"
                                f"投稿にいいねしました！",
                                ephemeral=True
                            )
                    else:
                        await interaction.followup.send(
                            f"**いいねしました！**\n\n"
                            f"投稿にいいねしました。\n"
                            f"※チャンネルが見つからないため、リアクションを追加できませんでした",
                            ephemeral=True
                        )
                except:
                    await interaction.followup.send(
                        f"**いいねしました！**\n\n"
                        f"投稿にいいねしました。\n"
                        f"※メッセージが見つからないため、リアクションを追加できませんでした",
                        ephemeral=True
                    )
            else:
                # メッセージ参照がない場合は個人メッセージのみ
                await interaction.followup.send(
                    f"❤️ **いいねしました！**\n\n"
                    f"投稿にいいねしました。",
                    ephemeral=True
                )
            
            conn.close()
            
        except ValueError:
            await interaction.followup.send(
                "❤️ 投稿IDは数字で入力してください。",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"いいね処理中にエラーが発生しました: {e}")
            await interaction.followup.send(
                "❤️ エラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )
    
    async def _log_action(self, user_id: int, action_type: str, target_id: int, action_data: Dict[str, Any]) -> None:
        """アクションをデータベースに記録"""
        try:
            import os
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'bot.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # テーブル存在確認
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='actions_user'")
            if cursor.fetchone():
                cursor.execute('''
                    INSERT INTO actions_user (user_id, action_type, target_id, action_data)
                    VALUES (?, ?, ?, ?)
                ''', (
                    user_id,
                    action_type,
                    target_id,
                    str(action_data)
                ))
                conn.commit()
                logger.info(f"アクション記録完了: {action_type} by user {user_id} on target {target_id}")
            else:
                logger.warning("actions_userテーブルが存在しません")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"アクション記録中にエラーが発生しました: {e}", exc_info=True)


class ReplyModal(ui.Modal, title="💬 リプライする投稿"):
    """リプライする投稿IDと内容を入力するモーダル"""
    
    def __init__(self):
        super().__init__(timeout=300)
        
        self.post_id_input = ui.TextInput(
            label="📝 投稿ID",
            placeholder="リプライする投稿のIDを入力...",
            required=True,
            style=discord.TextStyle.short,
            max_length=10
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
            import os
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'bot.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT id, content FROM thoughts WHERE id = ?', (post_id,))
            parent_post = cursor.fetchone()
            
            if not parent_post:
                await interaction.followup.send(
                    "💬 指定された投稿が見つかりませんでした。",
                    ephemeral=True
                )
                conn.close()
                return
            
            # アクションを記録
            await self._log_action(interaction.user.id, 'reply', post_id, {
                'reply_content': reply_content[:100],
                'parent_id': post_id
            })
            
            # リプライをデータベースに保存
            cursor.execute('''
                INSERT INTO replies (post_id, user_id, content, display_name, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                post_id,  # 親投稿ID
                interaction.user.id,
                reply_content,
                interaction.user.display_name,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            
            # 「リプライ」チャンネルを取得
            reply_channel = discord.utils.get(interaction.guild.text_channels, name="リプライ")
            
            if reply_channel:
                # 元の投稿メッセージを取得
                cursor.execute('''
                    SELECT message_id, channel_id 
                    FROM message_references 
                    WHERE post_id = ?
                ''', (post_id,))
                message_ref = cursor.fetchone()
                
                if message_ref:
                    # 元の投稿があったチャンネルから投稿を取得
                    original_channel = interaction.guild.get_channel(int(message_ref[1]))
                    
                    if original_channel:
                        try:
                            # 元の投稿メッセージを取得
                            message = await original_channel.fetch_message(int(message_ref[0]))
                            
                            # Discordの公式転送機能を使用
                            forwarded_message = await message.forward(reply_channel)
                            
                            # 転送されたメッセージにリプライとして投稿
                            reply_embed = discord.Embed(
                                color=discord.Color.blue()
                            )
                            
                            reply_embed.add_field(
                                name="💬 リプライ内容",
                                value=reply_content,
                                inline=False
                            )
                            
                            reply_embed.add_field(
                                name="👤 リプライ投稿者",
                                value=interaction.user.display_name,
                                inline=True
                            )
                            
                            # 転送されたメッセージにリプライとして送信
                            reply_message = await reply_channel.send(
                                embed=reply_embed,
                                reference=forwarded_message  # 転送メッセージへのリプライ
                            )
                            
                            # メッセージIDを保存（後の編集用）
                            cursor.execute('''
                                UPDATE replies 
                                SET message_id = ?
                                WHERE post_id = ? AND user_id = ?
                            ''', (reply_message.id, post_id, interaction.user.id))
                            conn.commit()
                            
                            await interaction.followup.send(
                                f"💬 **リプライを投稿しました！**\n\n"
                                f"投稿に返信しました。\n"
                                f"📢 「リプライ」チャンネルに転送されました！",
                                ephemeral=True
                            )
                        
                        except Exception as e:
                            logger.error(f"元の投稿の転送中にエラー: {e}")
                            await interaction.followup.send(
                                f"💬 **エラーが発生しました**\n\n"
                                f"元の投稿の転送に失敗しました。",
                                ephemeral=True
                            )
                else:
                    await interaction.followup.send(
                        f"💬 **エラーが発生しました**\n\n"
                        f"元の投稿チャンネルが見つかりません。",
                        ephemeral=True
                    )
            else:
                await interaction.followup.send(
                    f"💬 **エラーが発生しました**\n\n"
                    f"「リプライ」チャンネルが見つかりません。",
                    ephemeral=True
                )
            
            conn.close()
            
        except ValueError:
            await interaction.followup.send(
                "💬 投稿IDは数字で入力してください。",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"リプライ処理中にエラーが発生しました: {e}")
            await interaction.followup.send(
                "💬 エラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )
    
    async def _log_action(self, user_id: int, action_type: str, target_id: int, action_data: Dict[str, Any]) -> None:
        """アクションをデータベースに記録"""
        try:
            import os
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'bot.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # テーブル存在確認
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='actions_user'")
            if cursor.fetchone():
                cursor.execute('''
                    INSERT INTO actions_user (user_id, action_type, target_id, action_data)
                    VALUES (?, ?, ?, ?)
                ''', (
                    user_id,
                    action_type,
                    target_id,
                    str(action_data)
                ))
                conn.commit()
                logger.info(f"アクション記録完了: {action_type} by user {user_id} on target {target_id}")
            else:
                logger.warning("actions_userテーブルが存在しません")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"アクション記録中にエラーが発生しました: {e}", exc_info=True)


class Actions(commands.Cog):
    """いいね・リプライ機能を提供するCog"""
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        logger.info("Actions cog が初期化されました")
    
    @app_commands.command(name="like", description="❤️ いいねする")
    async def like_command(self, interaction: Interaction) -> None:
        """いいねコマンド"""
        try:
            logger.info(f"いいねコマンド実行: ユーザー {interaction.user.name} (ID: {interaction.user.id})")
            modal = LikeModal()
            await interaction.response.send_modal(modal)
        except Exception as e:
            logger.error(f"いいねコマンド実行中にエラーが発生しました: {e}", exc_info=True)
            try:
                await interaction.response.send_message(
                    "エラーが発生しました。もう一度お試しください。",
                    ephemeral=True
                )
            except:
                logger.error("いいねコマンドのエラーメッセージ送信に失敗しました")
    
    @app_commands.command(name="reply", description="💬 リプライする")
    async def reply_command(self, interaction: Interaction) -> None:
        """リプライコマンド"""
        try:
            logger.info(f"リプライコマンド実行: ユーザー {interaction.user.name} (ID: {interaction.user.id})")
            modal = ReplyModal()
            await interaction.response.send_modal(modal)
        except Exception as e:
            logger.error(f"リプライコマンド実行中にエラーが発生しました: {e}", exc_info=True)
            try:
                await interaction.response.send_message(
                    "エラーが発生しました。もう一度お試しください。",
                    ephemeral=True
                )
            except:
                logger.error("リプライコマンドのエラーメッセージ送信に失敗しました")


async def setup(bot: commands.Bot) -> None:
    """Cogをセットアップ"""
    try:
        logger.info("Actions cog のセットアップを開始します...")
        await bot.add_cog(Actions(bot))
        logger.info("Actions cog がセットアップされました")
        
        # コマンドが正常に登録されたか確認
        like_cmd = bot.tree.get_command('like')
        reply_cmd = bot.tree.get_command('reply')
        
        if like_cmd:
            logger.info("✅ /like コマンドが正常に登録されました")
        else:
            logger.error("❌ /like コマンドの登録に失敗しました")
            
        if reply_cmd:
            logger.info("✅ /reply コマンドが正常に登録されました")
        else:
            logger.error("❌ /reply コマンドの登録に失敗しました")
            
    except Exception as e:
        logger.error(f"Actions cog のセットアップ中にエラーが発生しました: {e}", exc_info=True)
        raise
