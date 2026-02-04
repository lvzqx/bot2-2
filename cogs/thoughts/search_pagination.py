"""
検索結果ページングビュー
"""

import logging
import os
from typing import List, Dict, Any

import discord
from discord import app_commands, ui, Interaction
from discord.ext import commands

# ロガー設定
logger = logging.getLogger(__name__)

# 定数
ITEMS_PER_PAGE = 3

class SearchResultsView(ui.View):
    """検索結果表示用ビュー"""
    
    def __init__(self, cog, results: List[Dict[str, Any]], search_type: str):
        super().__init__(timeout=None)
        self.cog = cog
        self.results = results
        self.search_type = search_type
        self.current_page = 1
        self.total_pages = (len(results) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
        
        # ボタンを追加
        self._add_buttons()
    
    def _add_buttons(self):
        """ボタンを追加"""
        if self.total_pages > 1:
            # 前のページボタン
            self.prev_button = ui.Button(
                label='◀️ 前へ',
                style=discord.ButtonStyle.secondary,
                disabled=self.current_page <= 1
            )
            self.prev_button.callback = self.prev_page_callback
            self.add_item(self.prev_button)
            
            # 次のページボタン
            self.next_button = ui.Button(
                label='次へ ▶️',
                style=discord.ButtonStyle.secondary,
                disabled=self.current_page >= self.total_pages
            )
            self.next_button.callback = self.next_page_callback
            self.add_item(self.next_button)
            
            # ページ情報ボタン
            self.page_button = ui.Button(
                label=f'{self.current_page}/{self.total_pages}',
                style=discord.ButtonStyle.primary,
                disabled=True
            )
            self.add_item(self.page_button)
    
    async def prev_page_callback(self, interaction: Interaction):
        """前のページ"""
        if self.current_page > 1:
            self.current_page -= 1
            await self._update_page(interaction)
    
    async def next_page_callback(self, interaction: Interaction):
        """次のページ"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            await self._update_page(interaction)
    
    async def _update_page(self, interaction: Interaction):
        """ページを更新"""
        # Embedを再作成
        from .search_embed import create_search_embed
        embed = create_search_embed(
            self.results,
            self.search_type,
            self.current_page,
            self.total_pages
        )
        
        # ボタンの状態を更新
        if self.total_pages > 1:
            self.prev_button.disabled = self.current_page <= 1
            self.next_button.disabled = self.current_page >= self.total_pages
            self.page_button.label = f'{self.current_page}/{self.total_pages}'
        
        await interaction.response.edit_message(embed=embed, view=self)
