"""
検索タイプ選択ビュー
"""

import logging
import os

import discord
from discord import app_commands, ui, Interaction
from discord.ext import commands

# ロガー設定
logger = logging.getLogger(__name__)

class SearchTypeView(ui.View):
    """検索タイプ選択用ビュー"""
    
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog
        
        self.select = ui.Select(
            placeholder="検索タイプを選択してください",
            options=[
                discord.SelectOption(
                    label="📝 投稿検索",
                    description="投稿を検索します",
                    emoji="📝"
                ),
                discord.SelectOption(
                    label="💬 リプライ検索",
                    description="リプライを検索します",
                    emoji="💬"
                ),
                discord.SelectOption(
                    label="🔍 詳細検索",
                    description="詳細な条件で検索します",
                    emoji="🔍"
                )
            ]
        )
        
        self.select.callback = self.select_callback
        self.add_item(self.select)
    
    async def select_callback(self, interaction: Interaction):
        """選択時のコールバック"""
        selected = self.select.values[0]
        
        # SearchModalを動的にインポートして循環インポートを回避
        from .search_modal import SearchModal
        
        if selected == "📝 投稿検索":
            modal = SearchModal(self.cog)
            modal.title = "📝 投稿検索"
            await interaction.response.send_modal(modal)
        elif selected == "💬 リプライ検索":
            modal = SearchModal(self.cog)
            modal.title = "💬 リプライ検索"
            await interaction.response.send_modal(modal)
        elif selected == "🔍 詳細検索":
            modal = SearchModal(self.cog)
            modal.title = "🔍 詳細検索"
            await interaction.response.send_modal(modal)

# SearchTypeViewをエクスポート
__all__ = ['SearchTypeView']
