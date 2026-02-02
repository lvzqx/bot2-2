import logging
import os
from typing import Dict, Any

import discord
from discord import app_commands, ui, Interaction, Embed
from discord.ext import commands

# マネージャーをインポート
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from managers.reply_manager import ReplyManager
from managers.post_manager import PostManager

logger = logging.getLogger(__name__)

class EditReply(commands.Cog):
    """リプライ編集用Cog"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reply_manager = ReplyManager()
        self.post_manager = PostManager()
    
    @app_commands.command(name='edit_reply', description='💬 リプライを編集')
    async def edit_reply(self, interaction: discord.Interaction):
        """編集するリプライを選択するコマンド"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # 全投稿を取得してユーザーのリプライを検索
            all_posts = self.post_manager.get_all_posts()
            user_replies = []
            
            for post in all_posts:
                replies = self.reply_manager.get_replies(post['id'])
                
                for reply in replies:
                    if reply.get('user_id') == str(interaction.user.id):
                        # 親投稿情報を追加
                        reply['post_content'] = post.get('content', '元の投稿が見つかりません')
                        user_replies.append(reply)
            
            # 作成日時でソート
            user_replies.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            user_replies = user_replies[:25]  # 最大25件
            
            if not user_replies:
                await interaction.followup.send(
                    "❌ **リプライが見つかりません**\n\n"
                    "編集できるリプライがありません。",
                    ephemeral=True
                )
                return
            
            # リプライ選択ビューを表示
            view = ReplySelectView(user_replies, self)
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
        super().__init__(timeout=None)
        self.replies = replies
        self.cog = cog
        
        # リプライ選択ドロップダウン
        self.reply_select = ui.Select(
            placeholder="編集するリプライを選択...",
            min_values=1,
            max_values=1
        )
        
        for reply in replies:
            reply_id = reply.get('id')
            content = reply.get('content', '')
            post_id = reply.get('post_id')
            created_at = reply.get('created_at')
            post_content = reply.get('post_content', '')
            
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
        reply_data = next((reply for reply in self.replies if reply.get('id') == selected_reply_id), None)
        
        if reply_data:
            modal = ReplyEditModal(reply_data, self.cog)
            await interaction.response.send_modal(modal)


class ReplyEditModal(ui.Modal, title="💬 リプライを編集"):
    """リプライ編集用モーダル"""
    
    def __init__(self, reply_data, cog):
        super().__init__(timeout=None)
        self.cog = cog
        self.reply_data = reply_data
        
        content = reply_data.get('content', '')
        post_id = reply_data.get('post_id')
        created_at = reply_data.get('created_at')
        post_content = reply_data.get('post_content', '')
        
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
            
            # reply_managerを使ってリプライを更新
            post_id = self.reply_data.get('post_id')
            reply_id = self.reply_data.get('id')
            
            # リプライを更新
            success = self.cog.reply_manager.update_reply(post_id, reply_id, self.content_input.value)
            
            if not success:
                logger.error(f"リプライの更新に失敗しました: 投稿ID={post_id}, リプライID={reply_id}")
                await interaction.followup.send(
                    "❌ **エラーが発生しました**\n\n"
                    "リプライの更新に失敗しました。",
                    ephemeral=True
                )
                return
            
            logger.info(f"リプライを更新しました: 投稿ID={post_id}, リプライID={reply_id}")
            
            # Discordメッセージを同期的に更新
            message_ref_data = self.cog.reply_manager.get_reply_message_ref(reply_id)
            message_id = None
            channel_id = None
            
            if message_ref_data:
                message_id = message_ref_data.get('message_id')
                channel_id = message_ref_data.get('channel_id')
                logger.info(f"リプライmessage_ref取得成功: message_id={message_id}, channel_id={channel_id}")
            else:
                logger.warning(f"⚠️ リプライmessage_refが見つかりません: リプライID={reply_id}")
            
            if message_id and channel_id:
                try:
                    logger.info(f"リプライDiscordメッセージ更新開始: message_id={message_id}, channel_id={channel_id}")
                    channel = interaction.guild.get_channel(int(channel_id))
                    if channel:
                        logger.info(f"チャンネル取得成功: {channel.name} (ID: {channel.id})")
                        message = await channel.fetch_message(int(message_id))
                        if message:
                            logger.info(f"メッセージ取得成功: {message.id}")
                            if message.embeds:
                                logger.info(f"embeds取得成功: {len(message.embeds)}個")
                                embed = message.embeds[0]
                                # リプライembedを更新
                                embed.description = self.content_input.value
                                # Footerは維持（更新しない）
                                
                                await message.edit(embed=embed)
                                logger.info(f"✅ リプライDiscordメッセージ更新完了: リプライID={reply_id}")
                            else:
                                logger.warning(f"⚠️ メッセージにembedsがありません: message_id={message_id}")
                        else:
                            logger.warning(f"⚠️ メッセージ取得失敗: message_id={message_id}")
                    else:
                        logger.warning(f"⚠️ チャンネル取得失敗: channel_id={channel_id}")
                except Exception as e:
                    logger.error(f"❌ リプライDiscordメッセージ更新中にエラー: {e}", exc_info=True)
            else:
                logger.warning(f"⚠️ message_idまたはchannel_idがありません: message_id={message_id}, channel_id={channel_id}")
            
            # GitHubに保存する処理
            from utils.github_sync import sync_to_github
            await sync_to_github("edit reply", interaction.user.name, reply_id)
            
            await interaction.followup.send(
                f"✅ **リプライを更新しました**\n\n"
                f"投稿ID: {post_id}\n"
                f"リプライID: {reply_id}",
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"リプライ編集中にエラーが発生しました: {e}")
            await interaction.followup.send(
                "❌ **エラーが発生しました**\n\n"
                "リプライの更新に失敗しました。",
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(EditReply(bot))
