import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import logging
from typing import Optional, List, Dict, Any
from bot import DatabaseMixin

logger = logging.getLogger(__name__)

class Delete(commands.Cog, DatabaseMixin):
    """投稿削除用Cog"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        DatabaseMixin.__init__(self)
    
    @app_commands.command(name="delete", description="🗑️ 投稿削除")
    @app_commands.describe(post_id="削除する投稿のID")
    async def delete_post(self, interaction: discord.Interaction, post_id: Optional[str] = None) -> None:
        """投稿を削除します。投稿IDが指定されていない場合は投稿一覧を表示します。"""
        if post_id:
            await self._delete_by_post_id(interaction, post_id)
        else:
            await self._show_post_list(interaction)
    
    async def _show_post_list(self, interaction: discord.Interaction) -> None:
        """削除可能な投稿の一覧を表示します"""
        try:
            # 応答を遅延（既にdeferされている可能性があるためチェック）
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            
            # ユーザーの投稿を取得
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT t.id, t.content, t.is_private, t.is_anonymous, t.category, t.created_at,
                           m.message_id, m.channel_id
                    FROM thoughts t
                    LEFT JOIN message_references m ON t.id = m.post_id
                    WHERE t.user_id = ?
                    ORDER BY t.created_at DESC
                    LIMIT 25  # Discordの制限に合わせて25件まで
                ''', (str(interaction.user.id),))
                posts = cursor.fetchall()
            
            if not posts:
                await interaction.followup.send("削除可能な投稿が見つかりませんでした。", ephemeral=True)
                return
            
            # 投稿一覧を表示
            view = PostSelectView(posts, self)
            await interaction.followup.send("削除する投稿を選択してください:", view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"投稿一覧取得中にエラーが発生しました: {e}", exc_info=True)
            try:
                await interaction.followup.send("投稿の取得中にエラーが発生しました。もう一度お試しください。", ephemeral=True)
            except:
                pass
    
    async def _delete_by_post_id(self, interaction: discord.Interaction, post_id: str, followup: bool = False) -> None:
        """投稿IDで投稿を削除します"""
        logger.info(f"delete コマンドが呼び出されました。ユーザー: {interaction.user}, 投稿ID: {post_id}")
        
        # followupでなければ応答を遅延
        if not followup:
            await interaction.response.defer(ephemeral=True)
        
        try:
            # 投稿IDで投稿を検索
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                # message_referencesテーブルにuser_idカラムがなければ追加
                cursor.execute('PRAGMA table_info(message_references)')
                columns = [column[1] for column in cursor.fetchall()]
                logger.info(f"message_references columns: {columns}")
                
                if 'user_id' not in columns:
                    cursor.execute('ALTER TABLE message_references ADD COLUMN user_id INTEGER')
                    conn.commit()
                    logger.info("message_referencesテーブルにuser_idカラムを追加しました")
                    
                    # 既存データにuser_idを補完
                    cursor.execute('''
                        UPDATE message_references 
                        SET user_id = (
                            SELECT t.user_id 
                            FROM thoughts t 
                            WHERE t.id = message_references.post_id
                        )
                        WHERE user_id IS NULL
                    ''')
                    conn.commit()
                    logger.info("既存データにuser_idを補完しました")
                
                # 投稿IDで直接検索
                cursor.execute('''
                    SELECT t.id as post_id, mr.channel_id, t.user_id, t.is_private, mr.message_id
                    FROM thoughts t
                    LEFT JOIN message_references mr ON t.id = mr.post_id
                    WHERE t.id = ?
                ''', (int(post_id),))
                
                row = cursor.fetchone()
                logger.info(f"クエリ結果: {row}")
                
                if not row:
                    await interaction.followup.send(
                        "❌ 指定された投稿IDの投稿が見つかりません。",
                        ephemeral=True
                    )
                    return
                
                post_id, channel_id, post_user_id, is_private, message_id = row
                logger.info(f"投稿を検出: post_id={post_id}, channel_id={channel_id}, message_id={message_id}")
                
                # 権限チェック
                is_admin = interaction.user.guild_permissions.administrator
                if str(post_user_id) != str(interaction.user.id) and not is_admin:
                    await interaction.followup.send(
                        "❌ この投稿を削除する権限がありません。",
                        ephemeral=True
                    )
                    return
                
                # メッセージを削除（メッセージが存在する場合）
                if message_id and channel_id:
                    try:
                        channel = await interaction.guild.fetch_channel(int(channel_id))
                        if channel:
                            message = await channel.fetch_message(int(message_id))
                            await message.delete()
                            logger.info(f"メッセージ {message_id} を削除しました")
                    except discord.NotFound:
                        logger.warning(f"メッセージが見つかりません: {message_id}")
                    except discord.Forbidden:
                        logger.warning(f"メッセージの削除権限がありません: {message_id}")
                    except Exception as e:
                        logger.error(f"メッセージ削除中にエラー: {e}")
                else:
                    logger.info("メッセージIDまたはチャンネルIDが存在しないため、メッセージの削除をスキップします")
                
                # 非公開投稿の場合、スレッドも削除
                if is_private and message_id and channel_id:
                    try:
                        channel = await interaction.guild.fetch_channel(int(channel_id))
                        if channel:
                            logger.info(f"チャンネルを検出: {channel.name} (ID: {channel.id})")
                            logger.info(f"チャンネルタイプ: {channel.type}")
                            
                            # プライベートスレッドの場合は削除
                            if hasattr(channel, 'type') and channel.type == discord.ChannelType.private_thread:
                                await channel.delete(reason="非公開投稿の削除に伴うスレッド削除")
                                logger.info(f"プライベートスレッド {channel.id} を削除しました")
                            else:
                                logger.warning(f"チャンネル {channel.id} はプライベートスレッドではありませんでした")
                        else:
                            logger.warning(f"チャンネル {channel_id} が見つかりませんでした")
                            
                    except discord.NotFound:
                        logger.warning(f"スレッドが見つかりません: {channel_id}")
                    except discord.Forbidden as e:
                        logger.error(f"スレッドの削除権限がありません: {channel_id} - {e}")
                    except Exception as e:
                        logger.error(f"スレッド削除中にエラー: {e}", exc_info=True)
                
                # データベースから投稿を削除
                try:
                    # メッセージ参照を先に削除
                    cursor.execute('DELETE FROM message_references WHERE post_id = ?', (post_id,))
                    # 投稿を削除
                    cursor.execute('DELETE FROM thoughts WHERE id = ?', (post_id,))
                    conn.commit()
                    logger.info(f"投稿ID {post_id} をデータベースから削除しました")
                except Exception as e:
                    logger.error(f"データベース削除中にエラー: {e}")
                    conn.rollback()
                    await interaction.followup.send(
                        "❌ データベースの削除に失敗しました。",
                        ephemeral=True
                    )
                    return
                
                # 非公開投稿の場合、ロールを確認
                if is_private:
                    try:
                        # 残りの非公開投稿数を確認
                        cursor.execute('''
                            SELECT COUNT(*) as count 
                            FROM thoughts 
                            WHERE user_id = ? AND is_private = 1
                        ''', (post_user_id,))
                        remaining_posts = cursor.fetchone()['count']
                        
                        logger.info(f"ユーザー {post_user_id} の残り非公開投稿数: {remaining_posts}")
                        
                        if remaining_posts == 0:
                            # 非公開ロールを削除
                            try:
                                member = await interaction.guild.fetch_member(post_user_id)
                                private_role = discord.utils.get(interaction.guild.roles, name="非公開")
                                
                                if private_role:
                                    if member and private_role in member.roles:
                                        await member.remove_roles(private_role, reason="非公開投稿がなくなりました")
                                        logger.info(f"ユーザー {member.display_name} から非公開ロールを削除しました")
                                    else:
                                        logger.warning(f"ユーザー {post_user_id} に非公開ロールがありませんでした")
                                else:
                                    logger.warning("非公開ロールが見つかりませんでした")
                                    
                            except discord.NotFound:
                                logger.warning(f"ユーザー {post_user_id} が見つかりませんでした")
                            except discord.Forbidden as e:
                                logger.error(f"ユーザー {post_user_id} からロールを削除する権限がありません: {e}")
                            except Exception as e:
                                logger.error(f"非公開ロールの削除中にエラーが発生しました: {e}", exc_info=True)
                    except Exception as e:
                        logger.error(f"非公開ロールの確認中にエラーが発生しました: {e}")
                
                await interaction.followup.send(
                    "✅ 投稿を削除しました。",
                    ephemeral=True
                )
                    
        except Exception as e:
            logger.error(f"削除処理中にエラーが発生しました: {e}", exc_info=True)
            await interaction.followup.send(
                f"❌ 削除中にエラーが発生しました: {e}",
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(Delete(bot))

class PostSelect(discord.ui.Select):
    """投稿を選択するドロップダウンメニュー"""
    
    def __init__(self, posts, cog):
        self.cog = cog
        self.posts = posts
        
        options = []
        for idx, post in enumerate(posts, 1):
            # プレビューテキストの作成
            preview = post['content'].replace('\n', ' ')[:50]
            if len(post['content']) > 50:
                preview += '...'
                
            # ラベルと説明の作成（投稿IDを表示）
            label = f"ID:{post[0]} {idx}. {preview}"
            if post[2]:  # is_private
                label = f"🔒 {label}"
            
            options.append(discord.SelectOption(
                label=label[:100],
                value=str(post[0]),  # 投稿IDをvalueとして使用
                description=f"カテゴリ: {(post[4] or 'なし')[:50]}"
            ))
        
        super().__init__(
            placeholder='削除する投稿を選択...',
            options=options,
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        """投稿が選択されたときの処理"""
        try:
            selected_post_id = int(self.values[0])
            # 投稿IDで投稿を検索
            selected_post = None
            for post in self.posts:
                if post[0] == selected_post_id:
                    selected_post = post
                    break
            
            if not selected_post:
                await interaction.response.send_message("投稿が見つかりませんでした。", ephemeral=True)
                return
            
            # 確認ビューを作成
            view = DeleteConfirmView(selected_post, self.cog)
            
            # 投稿内容をプレビュー表示
            preview = selected_post[1][:100]  # content
            if len(selected_post[1]) > 100:
                preview += '...'
            
            await interaction.response.edit_message(
                content=f"以下の投稿を削除してもよろしいですか？\n\n**内容:** {preview}\n**投稿ID:** {selected_post[0]}",
                view=view,
                embed=None
            )
        except Exception as e:
            logger.error(f"投稿選択中にエラーが発生しました: {e}", exc_info=True)
            await interaction.response.send_message(
                "投稿の選択中にエラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )

class PostSelectView(discord.ui.View):
    """投稿選択用のビュー"""
    
    def __init__(self, posts, cog):
        super().__init__(timeout=60)  # 60秒でタイムアウト
        self.add_item(PostSelect(posts, cog))
    
    async def on_timeout(self):
        """タイムアウト時の処理"""
        # ビューの無効化
        for item in self.children:
            item.disabled = True

class DeleteConfirmView(discord.ui.View):
    """削除確認用のビュー"""
    
    def __init__(self, post, cog):
        super().__init__(timeout=30)  # 30秒でタイムアウト
        self.post = post
        self.cog = cog
    
    @discord.ui.button(label="削除する", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """削除を確定するボタン"""
        try:
            # ボタンを無効化
            button.disabled = True
            for item in self.children:
                item.disabled = True
            
            await interaction.response.edit_message(
                content="削除中です...",
                view=self
            )
            
            # 投稿IDで削除を実行（タプルの最初の要素が投稿ID）
            await self.cog._delete_by_post_id(interaction, str(self.post[0]), followup=True)
            
        except Exception as e:
            logger.error(f"削除確認中にエラーが発生しました: {e}", exc_info=True)
            await interaction.followup.send(
                "削除中にエラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )
    
    @discord.ui.button(label="キャンセル", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """キャンセルボタン"""
        try:
            await interaction.response.edit_message(
                content="削除をキャンセルしました。",
                view=None,
                embed=None
            )
        except Exception as e:
            logger.error(f"キャンセル処理中にエラーが発生しました: {e}", exc_info=True)
    
    async def on_timeout(self):
        """タイムアウト時の処理"""
        for item in self.children:
            item.disabled = True
