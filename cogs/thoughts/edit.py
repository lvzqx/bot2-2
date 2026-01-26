import discord
from discord import app_commands, ui, Interaction
from discord.ext import commands
import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

# ファイルマネージャーをインポート
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from file_manager import FileManager

logger = logging.getLogger(__name__)

class Edit(commands.Cog):
    """投稿を編集用Cog"""
    
    def __init__(self, bot):
        self.bot = bot
        self.file_manager = FileManager()
    
    @app_commands.command(name='edit', description='📝 投稿を編集')
    async def edit(self, interaction: discord.Interaction):
        """編集する投稿を選択するコマンド"""
        try:
            # 最初に応答を遅延
            await interaction.response.defer(ephemeral=True)
            
            # ユーザーの投稿を取得
            posts = self.file_manager.search_posts(user_id=str(interaction.user.id))
            
            if not posts:
                await interaction.followup.send("編集できる投稿がありません。", ephemeral=True)
                return
            
            # メッセージリストを作成
            items_list = []
            for post in posts[:25]:  # 最大25件
                # メッセージ参照ファイルを確認
                message_ref_file = os.path.join("data", f"message_ref_{post['id']}.json")
                message_id = None
                channel_id = None
                
                if os.path.exists(message_ref_file):
                    try:
                        import json
                        with open(message_ref_file, 'r', encoding='utf-8') as f:
                            message_ref_data = json.load(f)
                            message_id = message_ref_data.get('message_id')
                            channel_id = message_ref_data.get('channel_id')
                    except (json.JSONDecodeError, FileNotFoundError):
                        pass
                
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
        super().__init__(timeout=300)
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
        super().__init__(timeout=300)
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
            
            # ファイルを更新
            post_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                   'data', 'posts', f"{self.post_data['id']}.json")
            
            if os.path.exists(post_file):
                import json
                with open(post_file, 'r', encoding='utf-8') as f:
                    post_data = json.load(f)
                
                # 内容を更新
                post_data['content'] = new_content
                post_data['category'] = new_category
                post_data['image_url'] = new_image_url
                post_data['updated_at'] = datetime.now().isoformat()
                
                with open(post_file, 'w', encoding='utf-8') as f:
                    json.dump(post_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"投稿を更新しました: 投稿ID={self.post_data['id']}")
            else:
                await interaction.followup.send(
                    "❌ **投稿が見つかりません**\n\n"
                    "投稿ファイルが存在しません。",
                    ephemeral=True
                )
                return
            
            # Discordメッセージも更新
            if self.post_data.get('message_id') and self.post_data.get('channel_id'):
                try:
                    channel = interaction.guild.get_channel(int(self.post_data['channel_id']))
                    if channel:
                        message = await channel.fetch_message(int(self.post_data['message_id']))
                        if message.embeds:
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
                except Exception as e:
                    logger.error(f"Discordメッセージ更新中にエラー: {e}")
            
            await interaction.followup.send(
                f"✅ **投稿を編集しました！**\n\n"
                f"投稿ID: {self.post_data['id']} を更新しました。",
                ephemeral=True
            )
            
            # GitHubに保存する処理
            from .github_sync import sync_to_github
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
