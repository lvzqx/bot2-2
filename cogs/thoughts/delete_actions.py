import discord
from discord import app_commands, ui, Interaction
from discord.ext import commands
import sqlite3
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DeleteActions(commands.Cog):
    """いいねとリプライを削除する機能を提供するCog"""
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        logger.info("DeleteActions cog が初期化されました")
    
    def get_db_path(self) -> str:
        """データベースパスを取得"""
        # bot.pyと同じディレクトリのbot.dbを使用
        bot_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        return os.path.join(bot_dir, 'bot.db')
    
    @app_commands.command(name="unlike", description="❌ いいねを削除")
    async def unlike_command(self, interaction: Interaction) -> None:
        """いいね取り消しコマンド"""
        try:
            logger.info(f"いいね取り消しコマンド実行: ユーザー {interaction.user.name} (ID: {interaction.user.id})")
            modal = UnlikeModal(self.get_db_path())
            await interaction.response.send_modal(modal)
        except Exception as e:
            logger.error(f"いいね取り消しコマンド実行中にエラーが発生しました: {e}", exc_info=True)
            try:
                await interaction.response.send_message(
                    "エラーが発生しました。もう一度お試しください。",
                    ephemeral=True
                )
            except:
                logger.error("いいね取り消しコマンドのエラーメッセージ送信に失敗しました")

    @app_commands.command(name="delete_reply", description="🗑️ リプライを削除")
    async def delete_reply_command(self, interaction: Interaction) -> None:
        """リプライ削除コマンド"""
        try:
            logger.info(f"リプライ削除コマンド実行: ユーザー {interaction.user.name} (ID: {interaction.user.id})")
            modal = DeleteReplyModal(self.get_db_path())
            await interaction.response.send_modal(modal)
        except Exception as e:
            logger.error(f"リプライ削除コマンド実行中にエラーが発生しました: {e}", exc_info=True)
            try:
                await interaction.response.send_message(
                    "エラーが発生しました。もう一度お試しください。",
                    ephemeral=True
                )
            except:
                logger.error("リプライ削除コマンドのエラーメッセージ送信に失敗しました")


class UnlikeModal(ui.Modal, title="❤️ いいねを取り消す"):
    """いいねを取り消す投稿IDを入力するモーダル"""
    
    def __init__(self, db_path: str):
        super().__init__(timeout=300)
        self.db_path = db_path
        
        self.post_id_input = ui.TextInput(
            label="投稿ID",
            placeholder="いいねを取り消す投稿のIDを入力...",
            required=True,
            style=discord.TextStyle.short,
            max_length=10
        )
        
        self.add_item(self.post_id_input)
    
    async def on_submit(self, interaction: Interaction) -> None:
        """いいね取り消し実行"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            post_id = int(self.post_id_input.value.strip())
            
            # データベース接続
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # テーブルの存在確認
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='message_references'")
            if not cursor.fetchone():
                await interaction.followup.send(
                    "データベースが初期化されていません。",
                    ephemeral=True
                )
                conn.close()
                return
            
            # thoughtsテーブルで投稿の存在確認
            cursor.execute('SELECT id FROM thoughts WHERE id = ?', (post_id,))
            if not cursor.fetchone():
                await interaction.followup.send(
                    "投稿が見つかりませんでした。\n\n"
                    f"投稿ID: {post_id}\n"
                    "※正しい投稿IDを入力してください。",
                    ephemeral=True
                )
                conn.close()
                return
            
            # message_referencesから投稿情報を取得
            cursor.execute('''
                SELECT message_id, channel_id 
                FROM message_references 
                WHERE post_id = ?
            ''', (post_id,))
            message_ref = cursor.fetchone()
            
            # 投稿が存在するか確認
            cursor.execute('SELECT id FROM thoughts WHERE id = ?', (post_id,))
            post_exists = cursor.fetchone()
            
            if not post_exists:
                await interaction.followup.send(
                    f"**投稿が見つかりません**\n\n"
                    f"投稿ID: {post_id}\n"
                    f"※正しい投稿IDを入力してください。",
                    ephemeral=True
                )
                conn.close()
                return
            
            if message_ref:
                try:
                    # Discordメッセージを取得
                    channel = interaction.guild.get_channel(int(message_ref[1]))
                    if channel:
                        message = await channel.fetch_message(int(message_ref[0]))
                        
                        # この投稿へのいいねメッセージを検索して削除
                        like_message_found = False
                        async for reply in message.channel.history(limit=50):
                            if (reply.reference and 
                                reply.reference.message_id == message.id and
                                reply.author == interaction.guild.me and
                                reply.content.startswith(f"❤️いいね：{interaction.user.display_name}")):
                                # メッセージを削除
                                await reply.delete()
                                like_message_found = True
                                break
                        
                        if like_message_found:
                            await interaction.followup.send(
                                f"❤️ **いいねを削除しました！**\n\n"
                                f"投稿から❤️いいねを削除しました。",
                                ephemeral=True
                            )
                        else:
                            await interaction.followup.send(
                                f"❤️ **いいねが見つかりません**\n\n"
                                f"投稿には❤️いいねがありません。",
                                ephemeral=True
                            )
                    else:
                        await interaction.followup.send(
                            f"❌ **チャンネルが見つかりません**\n\n"
                            f"投稿のチャンネルが見つかりませんでした。",
                            ephemeral=True
                        )
                except discord.NotFound:
                    await interaction.followup.send(
                        f"❌ **メッセージが見つかりません**\n\n"
                        f"投稿のメッセージが見つかりませんでした。",
                        ephemeral=True
                    )
                except discord.Forbidden:
                    await interaction.followup.send(
                        f"❌ **権限がありません**\n\n"
                        f"メッセージにアクセスする権限がありません。",
                        ephemeral=True
                    )
                except Exception as e:
                    logger.error(f"いいね削除中にエラーが発生しました: {e}")
                    await interaction.followup.send(
                        f"❌ **エラーが発生しました**\n\n"
                        f"いいねの削除に失敗しました。",
                        ephemeral=True
                    )
            else:
                await interaction.followup.send(
                    f"**メッセージ参照が見つかりません**\n\n"
                    f"投稿のメッセージ参照が見つかりません。",
                    ephemeral=True
                )
            
            conn.close()
            
        except ValueError:
            await interaction.followup.send(
                "❤️ 投稿IDは数字で入力してください。",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"いいね取り消し処理中にエラーが発生しました: {e}")
            await interaction.followup.send(
                "❤️ エラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )


class DeleteReplyModal(ui.Modal, title="🗑️ リプライを削除"):
    """リプライを削除する投稿IDを入力するモーダル"""
    
    def __init__(self, db_path: str):
        super().__init__(timeout=300)
        self.db_path = db_path
        
        self.post_id_input = ui.TextInput(
            label="投稿ID",
            placeholder="リプライを削除したい元の投稿のIDを入力...",
            required=True,
            style=discord.TextStyle.short,
            max_length=10
        )
        
        self.add_item(self.post_id_input)
    
    async def on_submit(self, interaction: Interaction) -> None:
        """リプライ削除実行"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            post_id = int(self.post_id_input.value.strip())
            
            # データベース接続
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # この投稿に対する自分のリプライを検索
            cursor.execute('''
                SELECT id, user_id, content FROM replies 
                WHERE post_id = ? AND user_id = ?
                ORDER BY id
            ''', (post_id, interaction.user.id))
            replies = cursor.fetchall()
            
            if replies:
                if len(replies) == 1:
                    # リプライが1つだけの場合は直接削除
                    reply_id = replies[0][0]
                    
                    # Discordメッセージも削除
                    try:
                        # リプライのメッセージIDを取得
                        cursor.execute('''
                            SELECT message_id 
                            FROM replies 
                            WHERE id = ? AND user_id = ?
                        ''', (reply_id, interaction.user.id))
                        reply_msg = cursor.fetchone()
                        
                        if reply_msg and reply_msg[0]:
                            # 「リプライ」チャンネルを取得
                            reply_channel = discord.utils.get(interaction.guild.text_channels, name="リプライ")
                            if reply_channel:
                                try:
                                    # 保存されたメッセージIDで直接削除（Embedメッセージ）
                                    reply_message = await reply_channel.fetch_message(int(reply_msg[0]))
                                    
                                    # 転送メッセージも取得して削除
                                    if reply_message.reference:
                                        try:
                                            forwarded_message = await reply_channel.fetch_message(reply_message.reference.message_id)
                                            await forwarded_message.delete()
                                            logger.info(f"転送メッセージを削除しました: {reply_message.reference.message_id}")
                                        except discord.NotFound:
                                            logger.warning(f"転送メッセージが見つかりません: {reply_message.reference.message_id}")
                                        except Exception as e:
                                            logger.error(f"転送メッセージの削除中にエラー: {e}")
                                    
                                    # Embedメッセージを削除
                                    await reply_message.delete()
                                    logger.info(f"リプライメッセージを直接削除しました: {reply_msg[0]}")
                                except discord.NotFound:
                                    logger.warning(f"リプライメッセージが見つかりません: {reply_msg[0]}")
                                except Exception as e:
                                    logger.error(f"リプライメッセージの削除中にエラー: {e}")
                    except Exception as e:
                        logger.error(f"Discordメッセージ削除中にエラー: {e}")
                    
                    # データベースから削除
                    cursor.execute('DELETE FROM replies WHERE id = ?', (reply_id,))
                    conn.commit()
                    
                    await interaction.followup.send(
                        f"**リプライを削除しました！**\n\n"
                        f"投稿へのリプライとDiscordメッセージを削除しました。",
                        ephemeral=True
                    )
                else:
                    # リプライが複数ある場合は選択肢を表示
                    reply_list = "\n".join([
                        f"ID: {reply[0]} - {reply[2][:30]}..."
                        for reply in replies
                    ])
                    
                    # 最初のリプライのメッセージIDを取得して削除
                    try:
                        # 「リプライ」チャンネルを取得
                        reply_channel = discord.utils.get(interaction.guild.text_channels, name="リプライ")
                        if reply_channel:
                            for reply in replies:
                                reply_id = reply[0]
                                cursor.execute('''
                                    SELECT message_id 
                                    FROM replies 
                                    WHERE id = ? AND user_id = ?
                                ''', (reply_id, interaction.user.id))
                                reply_msg = cursor.fetchone()
                                
                                if reply_msg and reply_msg[0]:
                                    try:
                                        reply_message = await reply_channel.fetch_message(int(reply_msg[0]))
                                        await reply_message.delete()
                                        logger.info(f"リプライメッセージを直接削除しました: {reply_msg[0]}")
                                    except discord.NotFound:
                                        logger.warning(f"リプライメッセージが見つかりません: {reply_msg[0]}")
                                    except Exception as e:
                                        logger.error(f"リプライメッセージの削除中にエラー: {e}")
                                
                                # データベースから削除
                                cursor.execute('DELETE FROM replies WHERE id = ?', (reply_id,))
                                conn.commit()
                            
                            await interaction.followup.send(
                                f"**すべてのリプライを削除しました！**\n\n"
                                f"投稿へのリプライとDiscordメッセージを削除しました。",
                                ephemeral=True
                            )
                            return
                    except Exception as e:
                        logger.error(f"複数リプライ削除中にエラー: {e}")
                    
                    await interaction.followup.send(
                        f"**複数のリプライが見つかりました**\n\n"
                        f"投稿にはあなたのリプライが {len(replies)} 件あります。\n\n"
                        f"削除したいリプライIDを指定してください:\n{reply_list}\n\n"
                        f"現在、複数リプライの直接削除には対応していません。\n"
                        f"今後のアップデートで対応予定です。",
                        ephemeral=True
                    )
            else:
                # リプライがない場合
                await interaction.followup.send(
                    f"**リプライが見つかりません**\n\n"
                    f"投稿にはあなたのリプライがありません。",
                    ephemeral=True
                )
            
            conn.close()
            
        except ValueError:
            await interaction.followup.send(
                "投稿IDは数字で入力してください。",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"リプライ削除処理中にエラーが発生しました: {e}")
            await interaction.followup.send(
                "エラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )


async def setup(bot: commands.Bot) -> None:
    """Cogをセットアップ"""
    try:
        logger.info("DeleteActions cog のセットアップを開始します...")
        await bot.add_cog(DeleteActions(bot))
        logger.info("DeleteActions cog がセットアップされました")
        
        # コマンドが正常に登録されたか確認
        unlike_cmd = bot.tree.get_command('unlike')
        deletereply_cmd = bot.tree.get_command('deletereply')
        
        if unlike_cmd:
            logger.info("✅ /unlike コマンドが正常に登録されました")
        else:
            logger.error("❌ /unlike コマンドの登録に失敗しました")
            
        if deletereply_cmd:
            logger.info("✅ /deletereply コマンドが正常に登録されました")
        else:
            logger.error("❌ /deletereply コマンドの登録に失敗しました")
            
    except Exception as e:
        logger.error(f"DeleteActions cog のセットアップ中にエラーが発生しました: {e}", exc_info=True)
        raise
