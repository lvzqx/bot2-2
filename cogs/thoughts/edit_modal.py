"""
編集UIコンポーネント
"""

import discord
from discord import app_commands, ui, Interaction
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

class PostEditSelectView(ui.View):
    """投稿選択用ビュー"""
    
    def __init__(self, items: List[Dict[str, Any]], cog):
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
            
            if selected_value.startswith("post_"):
                post_id = int(selected_value.split("_")[1])
                post_data = next((item for item in self.items if item['id'] == post_id), None)
                
                if post_data:
                    modal = PostEditModal(post_data, self.cog)
                    await interaction.response.send_modal(modal)
                else:
                    await interaction.response.send_message("投稿データが見つかりません。", ephemeral=True)
            else:
                await interaction.response.send_message("無効な選択です。", ephemeral=True)
                
        except Exception as e:
            logger.error(f"投稿選択エラー: {e}")
            await interaction.response.send_message("エラーが発生しました。もう一度お試しください。", ephemeral=True)


class PostEditModal(ui.Modal, title="投稿を編集"):
    """投稿編集用モーダル"""
    
    def __init__(self, post_data: Dict[str, Any], cog: 'Edit'):
        super().__init__(timeout=None)
        self.cog = cog
        self.post_data = post_data
        
        # 現在の内容をプレフィルド
        self.message = ui.TextInput(
            label='📝 投稿内容',
            placeholder='投稿内容を入力...',
            required=True,
            style=discord.TextStyle.paragraph,
            max_length=2000,
            default=post_data.get('content', '')
        )
        
        self.category = ui.TextInput(
            label='📁 カテゴリー',
            placeholder='カテゴリーを入力（任意）',
            required=False,
            style=discord.TextStyle.short,
            max_length=50,
            default=post_data.get('category', '')
        )
        
        self.image_url = ui.TextInput(
            label='🖼️ 画像URL',
            placeholder='画像URLを入力（任意）',
            required=False,
            style=discord.TextStyle.short,
            max_length=500,
            default=post_data.get('image_url', '')
        )
        
        self.add_item(self.message)
        self.add_item(self.category)
        self.add_item(self.image_url)
    
    async def on_submit(self, interaction: Interaction):
        """編集内容を送信"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # フォームデータを取得
            message = self.message.value.strip()
            category = self.category.value.strip() if self.category.value else None
            image_url = self.image_url.value.strip() if self.image_url.value else None
            
            # 入力検証
            if len(message) < 1:
                await interaction.followup.send("投稿内容を入力してください。", ephemeral=True)
                return
            
            # 投稿を更新
            success = await self.cog.update_post(
                interaction=interaction,
                post_id=self.post_data['id'],
                message=message,
                category=category,
                image_url=image_url
            )
            
            if success:
                await interaction.followup.send(
                    f"✅ 投稿を更新しました！\n\n"
                    f"投稿ID: {self.post_data['id']}",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ 投稿の更新に失敗しました。",
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"編集送信エラー: {e}")
            await interaction.followup.send(
                "❌ エラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )
