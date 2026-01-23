import logging
from typing import Dict, Any
import sqlite3

import discord
from discord import app_commands, ui, Interaction, Embed
from discord.ext import commands

logger = logging.getLogger(__name__)

class EditReply(commands.Cog):
    """リプライ編集用Cog"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_path = "bot.db"
    
    def _get_db_connection(self):
        """データベース接続を取得"""
        return sqlite3.connect(self.db_path)
    
    @app_commands.command(name='edit_reply', description='💬 リプライを編集')
    async def edit_reply(self, interaction: discord.Interaction):
        """編集するリプライを選択するコマンド"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # ユーザーのリプライを取得
            cursor.execute('''
                SELECT r.id, r.content, r.post_id, r.created_at, t.content as post_content
                FROM replies r
                LEFT JOIN thoughts t ON r.post_id = t.id
                WHERE r.user_id = ?
                ORDER BY r.id DESC
                LIMIT 25
            ''', (str(interaction.user.id),))
            
            replies = cursor.fetchall()
            conn.close()
            
            if not replies:
                await interaction.followup.send(
                    "❌ **リプライが見つかりません**\n\n"
                    "編集できるリプライがありません。",
                    ephemeral=True
                )
                return
            
            # リプライ選択ビューを表示
            view = ReplySelectView(replies, self)
            embed = discord.Embed(
                title="💬 編集するリプライを選択",
                description="編集したいリプライを選択してください",
                color=discord.Color.blue()
            )
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"edit_replyコマンド実行中にエラーが発生しました: {e}")
            await interaction.followup.send(
                "❌ **エラーが発生しました**\n\n"
                "リプライの取得に失敗しました。",
                ephemeral=True
            )


class ReplySelectView(ui.View):
    """リプライ選択ビュー"""
    
    def __init__(self, replies, cog):
        super().__init__(timeout=300)
        self.replies = replies
        self.cog = cog
        
        # リプライ選択ドロップダウン
        self.reply_select = ui.Select(
            placeholder="編集するリプライを選択...",
            min_values=1,
            max_values=1
        )
        
        for reply in replies:
            reply_id, content, post_id, created_at, post_content = reply
            content_preview = content[:50] + "..." if len(content) > 50 else content
            post_preview = post_content[:30] + "..." if len(post_content) > 30 else post_content
            
            self.reply_select.add_option(
                label=f"リプライID: {reply_id}",
                description=f"投稿: {post_preview} | リプライ: {content_preview}",
                value=str(reply_id)
            )
        
        self.reply_select.callback = self.reply_select_callback
        self.add_item(self.reply_select)
    
    async def reply_select_callback(self, interaction: Interaction):
        """リプライ選択時のコールバック"""
        selected_reply_id = int(self.reply_select.values[0])
        
        # 選択されたリプライデータを取得
        reply_data = next((reply for reply in self.replies if reply[0] == selected_reply_id), None)
        
        if reply_data:
            modal = ReplyEditModal(reply_data, self.cog)
            await interaction.response.send_modal(modal)


class ReplyEditModal(ui.Modal, title="💬 リプライを編集"):
    """リプライ編集用モーダル"""
    
    def __init__(self, reply_data, cog):
        super().__init__(timeout=300)
        self.cog = cog
        self.reply_data = reply_data
        
        reply_id, content, post_id, created_at, post_content = reply_data
        
        self.content_input = ui.TextInput(
            label="💬 リプライ内容",
            placeholder="リプライの内容を入力...",
            required=True,
            style=discord.TextStyle.paragraph,
            max_length=2000,
            default=content
        )
        
        self.add_item(self.content_input)
    
    async def on_submit(self, interaction: Interaction):
        """リプライ編集を実行"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            conn = self.cog._get_db_connection()
            cursor = conn.cursor()
            
            # リプライを更新
            cursor.execute('''
                UPDATE replies 
                SET content = ? 
                WHERE id = ? AND user_id = ?
            ''', (self.content_input.value, self.reply_data[0], str(interaction.user.id)))
            
            conn.commit()
            
            # Discordメッセージも更新
            try:
                # リプライのメッセージIDを取得
                cursor.execute('''
                    SELECT message_id 
                    FROM replies 
                    WHERE id = ? AND user_id = ?
                ''', (self.reply_data[0], str(interaction.user.id)))
                reply_msg = cursor.fetchone()
                
                if reply_msg and reply_msg[0]:
                    # 「リプライ」チャンネルを取得
                    reply_channel = discord.utils.get(interaction.guild.text_channels, name="リプライ")
                    if reply_channel:
                        try:
                            # 保存されたメッセージIDで直接編集
                            reply_message = await reply_channel.fetch_message(int(reply_msg[0]))
                            
                            # 既存のembedを取得して内容だけ編集
                            if reply_message.embeds:
                                embed = reply_message.embeds[0]
                                # 新しいembedを作成して内容だけ更新
                                new_embed = discord.Embed(
                                    color=embed.color or discord.Color.blue()
                                )
                                
                                # 既存のフィールドをコピーして内容だけ更新
                                for field in embed.fields:
                                    if field.name == "💬 リプライ内容":
                                        new_embed.add_field(
                                            name=field.name,
                                            value=self.content_input.value,
                                            inline=field.inline
                                        )
                                    else:
                                        new_embed.add_field(
                                            name=field.name,
                                            value=field.value,
                                            inline=field.inline
                                        )
                                
                                await reply_message.edit(embed=new_embed)
                                logger.info(f"リプライメッセージの内容を更新しました: {reply_msg[0]}")
                            else:
                                logger.warning(f"リプライメッセージにembedがありません: {reply_msg[0]}")
                        except discord.NotFound:
                            logger.warning(f"リプライメッセージが見つかりません: {reply_msg[0]}")
                        except Exception as e:
                            logger.error(f"リプライメッセージの編集中にエラー: {e}")
            except Exception as e:
                logger.error(f"Discordメッセージの更新に失敗しました: {e}")
            
            conn.close()
            
            await interaction.followup.send(
                f"✅ **リプライを編集しました！**\n\n"
                f"リプライID: {self.reply_data[0]} を更新しました。",
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"リプライ編集中にエラーが発生しました: {e}")
            await interaction.followup.send(
                "❌ **エラーが発生しました**\n\n"
                "リプライの編集に失敗しました。",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(EditReply(bot))
