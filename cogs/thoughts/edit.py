import discord
from discord import app_commands, ui, Interaction
from discord.ext import commands
import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

# マネージャーをインポート
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from managers.post_manager import PostManager
from managers.reply_manager import ReplyManager
from managers.message_ref_manager import MessageRefManager

logger = logging.getLogger(__name__)

class Edit(commands.Cog):
    """投稿を編集用Cog"""
    
    def __init__(self, bot):
        self.bot = bot
        self.post_manager = PostManager()
        self.reply_manager = ReplyManager()
        self.message_ref_manager = MessageRefManager()
    
    @app_commands.command(name='edit', description='📝 投稿を編集')
    async def edit(self, interaction: discord.Interaction):
        """編集する投稿を選択するコマンド"""
        try:
            # 最初に応答を遅延
            await interaction.response.defer(ephemeral=True)
            
            # ユーザーの投稿を取得
            posts = self.post_manager.search_posts(user_id=str(interaction.user.id))
            
            if not posts:
                await interaction.followup.send("編集できる投稿がありません。", ephemeral=True)
                return
            
            # メッセージリストを作成
            items_list = []
            for post in posts[:25]:  # 最大25件
                # メッセージ参照を取得
                message_ref_data = self.message_ref_manager.get_message_ref(post['id'])
                if message_ref_data:
                    message_id = message_ref_data.get('message_id')
                    channel_id = message_ref_data.get('channel_id')
                else:
                    message_id = None
                    channel_id = None
                
                items_list.append({
                    'type': 'post',
                    'id': post['id'],
                    'content': post['content'],
                    'is_private': post.get('is_private', False),
                    'is_anonymous': post.get('is_anonymous', False),
                    'category': post.get('category'),
                    'image_url': post.get('image_url'),
                    'message_id': message_id,
                    'channel_id': channel_id
                })
            
            # 選択ビューを作成
            view = EditSelectView(items_list, self)
            
            await interaction.followup.send("編集する投稿を選択してください:", view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"editコマンド実行中にエラーが発生しました: {e}", exc_info=True)
            await interaction.followup.send("エラーが発生しました。もう一度お試しください。", ephemeral=True)


class EditSelectView(ui.View):
    """編集する投稿を選択するビュー"""
    
    def __init__(self, items: List[Dict[str, Any]], cog: 'Edit'):
        super().__init__(timeout=None)
        self.items = items
        self.cog = cog
        
        # 投稿選択メニューを作成
        options = []
        for item in items[:25]:  # Discordの制限で25件まで
            content_preview = item['content'][:50] + "..." if len(item['content']) > 50 else item['content']
            options.append(
                discord.SelectOption(
                    label=f"投稿 ID: {item['id']}",
                    description=f"{content_preview} ({'公開' if not item['is_private'] else '非公開'})",
                    value=f"post_{item['id']}"
                )
            )
        
        self.select_menu = ui.Select(
            placeholder="編集する投稿を選択...",
            options=options,
            min_values=1,
            max_values=1
        )
        self.select_menu.callback = self.select_callback
        self.add_item(self.select_menu)
    
    async def select_callback(self, interaction: Interaction):
        """選択された投稿を編集"""
        try:
            selected_value = self.select_menu.values[0]
            
            if selected_value.startswith('post_'):
                # 投稿編集
                post_id = int(selected_value.split('_')[1])
                item = next((item for item in self.items if item['type'] == 'post' and item['id'] == post_id), None)
                if item:
                    modal = PostEditModal(item, self.cog)
                    await interaction.response.send_modal(modal)
            
        except Exception as e:
            logger.error(f"選択コールバック中にエラーが発生しました: {e}")
            await interaction.response.send_message("エラーが発生しました。もう一度お試しください。", ephemeral=True)


class PostEditModal(ui.Modal, title="投稿を編集"):
    """投稿編集用モーダル"""
    
    def __init__(self, post_data: Dict[str, Any], cog: 'Edit'):
        super().__init__(timeout=None)
        self.post_data = post_data
        self.cog = cog
        
        self.content_input = ui.TextInput(
            label='📝 投稿内容',
            placeholder='編集する投稿内容を入力...',
            required=True,
            style=discord.TextStyle.paragraph,
            max_length=2000,
            default=post_data['content'][:1000]  # Discordの制限で1000文字まで
        )
        
        self.category_input = ui.TextInput(
            label='📁 カテゴリー',
            placeholder='カテゴリーを入力...',
            required=False,
            style=discord.TextStyle.short,
            max_length=50,
            default=post_data.get('category', '')
        )
        
        self.image_url_input = ui.TextInput(
            label='🖼️ 画像URL',
            placeholder='画像URLを入力... (https://...)',
            required=False,
            style=discord.TextStyle.short,
            max_length=500,
            default=post_data.get('image_url', '')
        )
        
        self.add_item(self.content_input)
        self.add_item(self.category_input)
        self.add_item(self.image_url_input)
    
    async def on_submit(self, interaction: Interaction):
        """投稿を編集実行"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            new_content = self.content_input.value.strip()
            new_category = self.category_input.value.strip() or None
            new_image_url = self.image_url_input.value.strip() or None
            
            # 公開設定を処理（現在の設定を維持）
            is_public = not self.post_data.get('is_private', False)
            
            # message_refからmessage_idとchannel_idを取得
            logger.info(f"message_ref取得開始: 投稿ID={self.post_data['id']}")
            message_ref_data = self.cog.message_ref_manager.get_message_ref(self.post_data['id'])
            message_id = None
            channel_id = None
            if message_ref_data:
                message_id = message_ref_data.get('message_id')
                channel_id = message_ref_data.get('channel_id')
                logger.info(f"message_ref取得成功: message_id={message_id}, channel_id={channel_id}")
            else:
                logger.warning(f"⚠️ message_refが見つかりません: 投稿ID={self.post_data['id']}")
                # 投稿データから直接取得を試みる
                post_data = self.cog.post_manager.get_post(self.post_data['id'], str(interaction.user.id))
                if post_data:
                    message_id = post_data.get('message_id')
                    channel_id = post_data.get('channel_id')
                    logger.info(f"投稿データから取得: message_id={message_id}, channel_id={channel_id}")
                else:
                    logger.warning(f"⚠️ 投稿データも見つかりません: 投稿ID={self.post_data['id']}")
            
            # post_managerを使って投稿を更新
            success = self.cog.post_manager.update_post(
                post_id=self.post_data['id'],
                content=new_content,
                category=new_category,
                image_url=new_image_url,
                user_id=str(interaction.user.id),
                message_id=message_id,
                channel_id=channel_id
            )
            
            if not success:
                await interaction.followup.send(
                    "❌ **投稿が見つかりません**\n\n"
                    "投稿ファイルが存在しないか、権限がありません。",
                    ephemeral=True
                )
                return
            
            logger.info(f"投稿を更新しました: 投稿ID={self.post_data['id']}")
            
            # まず成功メッセージを送信（速度改善）
            await interaction.followup.send(
                f"✅ **投稿を編集しました！**\n\n"
                f"投稿ID: {self.post_data['id']} を更新しました。",
                ephemeral=True
            )
            
            # Discordメッセージをバックグラウンドで更新
            if message_id and channel_id:
                try:
                    logger.info(f"Discordメッセージ更新開始: message_id={message_id}, channel_id={channel_id}")
                    channel = interaction.guild.get_channel(int(channel_id))
                    if channel:
                        logger.info(f"チャンネル取得成功: {channel.name} (ID: {channel.id})")
                        message = await channel.fetch_message(int(message_id))
                        if message:
                            logger.info(f"メッセージ取得成功: {message.id}")
                            if message.embeds:
                                logger.info(f"embeds取得成功: {len(message.embeds)}個")
                                embed = message.embeds[0]
                                # post.pyと同じ形式で更新
                                embed.description = new_content
                                if new_image_url:
                                    embed.set_image(url=new_image_url)
                                else:
                                    # 画像URLが空の場合は画像をクリア
                                    embed.set_image(url=None)
                                
                                # Footerを更新 - post.pyと同じ形式
                                footer_parts = []
                                if new_category:
                                    footer_parts.append(f"カテゴリー: {new_category}")
                                footer_parts.append(f"投稿ID: {self.post_data['id']}")
                                embed.set_footer(text=" | ".join(footer_parts))
                                
                                await message.edit(embed=embed)
                                logger.info(f"✅ Discordメッセージ更新完了: 投稿ID={self.post_data['id']}")
                            else:
                                logger.warning(f"⚠️ メッセージにembedsがありません: message_id={message_id}")
                        else:
                            logger.warning(f"⚠️ メッセージ取得失敗: message_id={message_id}")
                    else:
                        logger.warning(f"⚠️ チャンネル取得失敗: channel_id={channel_id}")
                except Exception as e:
                    logger.error(f"❌ Discordメッセージ更新中にエラー: {e}", exc_info=True)
            else:
                logger.warning(f"⚠️ message_idまたはchannel_idがありません: message_id={message_id}, channel_id={channel_id}")
            
            # GitHubに保存する処理
            from utils.github_sync import sync_to_github
            await sync_to_github("edit post", interaction.user.name, self.post_data['id'])
            
        except Exception as e:
            logger.error(f"投稿編集中にエラーが発生しました: {e}")
            await interaction.followup.send("編集中にエラーが発生しました。もう一度お試しください。", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    """Cogをセットアップ"""
    try:
        await bot.add_cog(Edit(bot))
        logger.info("Edit cog がセットアップされました")
    except Exception as e:
        logger.error(f"Edit cog セットアップ中にエラーが発生しました: {e}", exc_info=True)
        raise
