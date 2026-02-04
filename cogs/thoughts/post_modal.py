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
from config import get_channel_id, DEFAULT_AVATAR

# ロガーの設定
logger = logging.getLogger(__name__)

class PostModal(ui.Modal, title='新規投稿'):
    """投稿用モーダル"""
    
    def __init__(self, cog) -> None:
        super().__init__(timeout=None)
        self.cog = cog
        self.is_public = True
        
        self.message = ui.TextInput(
            label='📝 投稿内容',
            placeholder='ここに投稿内容を入力...',
            required=True,
            style=discord.TextStyle.paragraph,
            max_length=2000
        )
        
        self.category = ui.TextInput(
            label='📁 カテゴリー',
            placeholder='カテゴリーを入力（任意）',
            required=False,
            style=discord.TextStyle.short,
            max_length=50
        )
        
        self.image_url = ui.TextInput(
            label='🖼️ 画像URL',
            placeholder='画像URLを入力（任意）',
            required=False,
            style=discord.TextStyle.short,
            max_length=500
        )
        
        self.is_anonymous = ui.TextInput(
            label='👤 匿名設定',
            placeholder='匿名にする場合は「匿名」と入力',
            required=False,
            style=discord.TextStyle.short,
            max_length=10
        )
        
        self.display_name = ui.TextInput(
            label='🏷️ 表示名',
            placeholder='表示名を入力（任意）',
            required=False,
            style=discord.TextStyle.short,
            max_length=50
        )
        
        self.add_item(self.message)
        self.add_item(self.category)
        self.add_item(self.image_url)
        self.add_item(self.is_anonymous)
        self.add_item(self.display_name)
    
    async def on_submit(self, interaction: Interaction) -> None:
        """フォーム送信時の処理"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # フォームデータを取得
            message = self.message.value.strip()
            category = self.category.value.strip() if self.category.value else None
            image_url = self.image_url.value.strip() if self.image_url.value else None
            is_anonymous = self.is_anonymous.value.strip().lower() == '匿名'
            display_name = self.display_name.value.strip() if self.display_name.value else None
            
            # 入力検証
            # 簡易的なバリデーション（MessageManagerがないため）
            if len(message) < 1:
                await interaction.followup.send(
                    "❌ **エラーが発生しました**\n\n"
                    "投稿内容を入力してください。",
                    ephemeral=True
                )
                return
            
            if len(message) > 2000:
                await interaction.followup.send(
                    "❌ **エラーが発生しました**\n\n"
                    "投稿内容は2000文字以内で入力してください。",
                    ephemeral=True
                )
                return
            
            if image_url and len(image_url) > 500:
                await interaction.followup.send(
                    "❌ **エラーが発生しました**\n\n"
                    "画像URLは500文字以内で入力してください。",
                    ephemeral=True
                )
                return
            
            # 投稿を保存
            post_id = await self.cog.save_post(
                interaction=interaction,
                message=message,
                category=category,
                image_url=image_url,
                is_anonymous=is_anonymous,
                is_public=self.is_public,
                display_name=display_name
            )
            
            if post_id:
                await interaction.followup.send(
                    f"✅ **{'公開' if self.is_public else '非公開'}投稿を作成しました！**\n\n"
                    f"投稿ID: {post_id}",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ 投稿の作成に失敗しました。",
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"モーダル送信中にエラーが発生しました: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ **エラーが発生しました**\n\n"
                "投稿の作成中にエラーが発生しました。",
                ephemeral=True
            )

class PostSelectView(ui.View):
    """投稿タイプ選択用ビュー"""
    
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog
        
        self.select = ui.Select(
            placeholder="投稿タイプを選択してください",
            options=[
                discord.SelectOption(
                    label="🌍 公開投稿",
                    description="全員が見える投稿を作成します",
                    emoji="🌍"
                ),
                discord.SelectOption(
                    label="🔒 非公開投稿",
                    description="自分だけが見える投稿を作成します",
                    emoji="🔒"
                )
            ]
        )
        
        self.select.callback = self.select_callback
        self.add_item(self.select)
    
    async def select_callback(self, interaction: Interaction):
        """選択時のコールバック"""
        selected = self.select.values[0]
        
        if selected == "🌍 公開投稿":
            modal = PostModal(self.cog)
            modal.is_public = True
            modal.title = "🌍 公開投稿"
        else:
            modal = PostModal(self.cog)
            modal.is_public = False
            modal.title = "🔒 非公開投稿"
        
        await interaction.response.send_modal(modal)
