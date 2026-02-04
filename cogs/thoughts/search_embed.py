"""
検索Embed作成ロジック
"""

import logging
import os
from typing import List, Dict, Any

import discord
from discord import app_commands, ui, Interaction, Embed
from discord.ext import commands

# ロガー設定
logger = logging.getLogger(__name__)

# 定数
ITEMS_PER_PAGE = 3

def create_search_embed(
    results: List[Dict[str, Any]],
    search_type: str,
    page: int = 1,
    total_pages: int = 1
) -> Embed:
    """検索結果のEmbedを作成"""
    embed = discord.Embed(
        title=f"🔍 {search_type}検索結果",
        color=discord.Color.blue()
    )
    
    if not results:
        embed.description = "検索結果が見つかりませんでした。"
        embed.add_field(
            name="💡 ヒント",
            value="• 異なるキーワードを試してください\n• カテゴリーで絞り込んでみてください\n• 日付範囲を調整してみてください",
            inline=False
        )
        return embed
    
    # 結果を表示
    start_idx = (page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    page_results = results[start_idx:end_idx]
    
    for i, item in enumerate(page_results, start=start_idx + 1):
        if search_type == "投稿":
            content = item.get('content', '')[:200] + "..." if len(item.get('content', '')) > 200 else item.get('content', '')
            category = item.get('category', '未分類')
            post_id = item.get('id', '不明')
            created_at = item.get('created_at', '不明')
            is_anonymous = item.get('is_anonymous', False)
            
            author = "匿名" if is_anonymous else f"ユーザーID: {item.get('user_id', '不明')}"
            
            field_name = f"📝 {i}. 投稿ID: {post_id}"
            field_value = f"**著者:** {author}\n**カテゴリー:** {category}\n**内容:** {content}\n**作成日:** {created_at}"
            
        elif search_type == "リプライ":
            content = item.get('content', '')[:200] + "..." if len(item.get('content', '')) > 200 else item.get('content', '')
            reply_id = item.get('id', '不明')
            post_id = item.get('post_id', '不明')
            created_at = item.get('created_at', '不明')
            
            field_name = f"💬 {i}. リプライID: {reply_id}"
            field_value = f"**投稿ID:** {post_id}\n**内容:** {content}\n**作成日:** {created_at}\n**著者:** ユーザーID: {item.get('user_id', '不明')}"
        
        embed.add_field(
            name=field_name,
            value=field_value,
            inline=False
        )
    
    # フッター情報
    embed.set_footer(
        text=f"ページ {page}/{total_pages} | 全{len(results)}件の結果"
    )
    
    return embed
