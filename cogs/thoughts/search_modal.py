"""
検索モーダル
"""

import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

import discord
from discord import app_commands, ui, Interaction
from discord.ext import commands

# ロガー設定
logger = logging.getLogger(__name__)

class SearchModal(ui.Modal, title='🔍 詳細検索'):
    """詳細検索用モーダル"""
    
    def __init__(self, cog) -> None:
        super().__init__(timeout=None)
        self.cog = cog
        
        self.keyword = ui.TextInput(
            label='🔍 キーワード',
            placeholder='検索キーワードを入力（任意）',
            required=False,
            style=discord.TextStyle.short,
            max_length=100
        )
        
        self.category = ui.TextInput(
            label='📁 カテゴリー',
            placeholder='カテゴリーで絞り込み（任意）',
            required=False,
            style=discord.TextStyle.short,
            max_length=50
        )
        
        self.author_id = ui.TextInput(
            label='👤 ユーザーID',
            placeholder='投稿者のユーザーIDで絞り込み（任意）',
            required=False,
            style=discord.TextStyle.short,
            max_length=50
        )
        
        self.date_from = ui.TextInput(
            label='📅 開始日',
            placeholder='YYYY-MM-DD形式（任意）',
            required=False,
            style=discord.TextStyle.short,
            max_length=20
        )
        
        self.date_to = ui.TextInput(
            label='📅 終了日',
            placeholder='YYYY-MM-DD形式（任意）',
            required=False,
            style=discord.TextStyle.short,
            max_length=20
        )
        
        self.add_item(self.keyword)
        self.add_item(self.category)
        self.add_item(self.author_id)
        self.add_item(self.date_from)
        self.add_item(self.date_to)
    
    async def on_submit(self, interaction: Interaction) -> None:
        """モーダル送信時の処理"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # フォームデータを取得
            keyword = self.keyword.value.strip() if self.keyword.value else None
            category = self.category.value.strip() if self.category.value else None
            author_id = self.author_id.value.strip() if self.author_id.value else None
            date_from_str = self.date_from.value.strip() if self.date_from.value else None
            date_to_str = self.date_to.value.strip() if self.date_to.value else None
            
            # 検索パラメータを検証
            from .search_utils import validate_search_params
            is_valid, error_message = validate_search_params(keyword, category, date_from_str, date_to_str)
            
            if not is_valid:
                await interaction.followup.send(
                    f"❌ **入力エラー**\n\n{error_message}",
                    ephemeral=True
                )
                return
            
            # 日付を解析
            from .search_utils import parse_date_string
            date_from = parse_date_string(date_from_str) if date_from_str else None
            date_to = parse_date_string(date_to_str) if date_to_str else None
            
            # 匿名フィルター（デフォルトは含まない）
            is_anonymous = None
            
            # 検索実行
            from .search_utils import search_posts
            results = search_posts(
                keyword=keyword,
                category=category,
                author_id=author_id,
                date_from=date_from,
                date_to=date_to,
                is_anonymous=is_anonymous,
                post_manager=self.cog.post_manager
            )
            
            if not results:
                await interaction.followup.send(
                    "❌ **検索結果がありません**\n\n"
                    "指定された条件に一致する投稿が見つかりませんでした。",
                    ephemeral=True
                )
                return
            
            # 結果を表示
            await self.cog.show_search_results(interaction, results, "投稿")
            
        except Exception as e:
            logger.error(f"検索モーダル送信中にエラー: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ **エラーが発生しました**\n\n"
                "検索中にエラーが発生しました。",
                ephemeral=True
            )

# SearchModalのみをエクスポート
__all__ = ['SearchModal']
