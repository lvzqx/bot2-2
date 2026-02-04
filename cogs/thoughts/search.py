"""
Disgle検索機能 - 完全に動作するバージョン
Google風の検索インターフェースと完全な機能
"""

import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

import discord
from discord import app_commands, ui, Interaction, Embed
from discord.ext import commands

# マネージャーをインポート
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from managers.post_manager import PostManager
from managers.reply_manager import ReplyManager
from managers.like_manager import LikeManager
from managers.message_ref_manager import MessageRefManager
from managers.action_manager import ActionManager
from config import get_channel_id, extract_channel_id

# モーダルとユーティリティをインポート
from .search_modal import SearchModal, SearchTypeView
from .search_pagination import SearchResultsView
from .search_utils import search_posts, search_replies, create_search_embed

# ロガー設定
logger = logging.getLogger(__name__)

# 定数
MAX_SEARCH_RESULTS = 50
ITEMS_PER_PAGE = 3

# 型定義
PostData = Dict[str, Any]

class Search(commands.Cog):
    """投稿検索機能を提供するCog"""
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.post_manager = PostManager()
        self.reply_manager = ReplyManager()
        self.like_manager = LikeManager()
        self.message_ref_manager = MessageRefManager()
        self.action_manager = ActionManager()
        logger.info("Search cog が初期化されました")
    
    @app_commands.command(name="search", description="🔍 投稿を検索")
    async def search_command(self, interaction: Interaction) -> None:
        """検索コマンド"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # 検索タイプ選択ビューを表示
            view = SearchTypeView(self)
            embed = discord.Embed(
                title="🔍 検索タイプを選択",
                description="検索したい対象を選択してください",
                color=discord.Color.blue()
            )
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"searchコマンド実行中にエラー: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ **エラーが発生しました**\n\n"
                "検索の実行に失敗しました。",
                ephemeral=True
            )
    
        
    async def show_search_results(self, interaction: Interaction, results: List[Dict[str, Any]], search_type: str) -> None:
        """検索結果を表示"""
        try:
            # Embedを作成
            embed = create_search_embed(results, search_type)
            
            # ビューを作成
            view = SearchResultsView(self, results, search_type)
            
            # 結果を送信
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"検索結果表示中にエラー: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ **エラーが発生しました**\n\n"
                "検索結果の表示に失敗しました。",
                ephemeral=True
            )
    
    def _get_post_stats(self) -> Dict[str, int]:
        """投稿統計を取得"""
        try:
            all_posts = self.post_manager.get_all_posts()
            
            stats = {
                'total': len(all_posts),
                'public': len([p for p in all_posts if not p.get('is_private', False)]),
                'private': len([p for p in all_posts if p.get('is_private', False)]),
                'anonymous': len([p for p in all_posts if p.get('is_anonymous', False)]),
                'with_category': len([p for p in all_posts if p.get('category')])
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"投稿統計取得中にエラー: {e}")
            return {}
    
    def _get_reply_stats(self) -> Dict[str, int]:
        """リプライ統計を取得"""
        try:
            all_replies = self.reply_manager.get_all_replies()
            
            stats = {
                'total': len(all_replies),
                'recent': len([r for r in all_replies if self._is_recent(r.get('created_at'))])
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"リプライ統計取得中にエラー: {e}")
            return {}
    
    def _is_recent(self, date_str: str) -> bool:
        """最近の投稿か判定"""
        try:
            if not date_str:
                return False
            
            post_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            now = datetime.now(post_date.tzinfo)
            
            # 7日以内を「最近」と判定
            return (now - post_date).days <= 7
            
        except Exception:
            return False

async def setup(bot: commands.Bot) -> None:
    """Cogをセットアップする"""
    await bot.add_cog(Search(bot))
