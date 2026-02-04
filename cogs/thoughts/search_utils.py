"""
検索ユーティリティ関数
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

# ロガー設定
logger = logging.getLogger(__name__)

# 定数
MAX_SEARCH_RESULTS = 50
ITEMS_PER_PAGE = 3

# 型定義
PostData = Dict[str, Any]

def search_posts(
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    author_id: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    is_anonymous: Optional[bool] = None,
    post_manager: Optional[PostManager] = None
) -> List[PostData]:
    """投稿を検索する"""
    if not post_manager:
        return []
    
    try:
        # 全投稿を取得
        all_posts = post_manager.get_all_posts()
        
        # 検索条件でフィルタリング
        filtered_posts = []
        for post in all_posts:
            # キーワード検索
            if keyword:
                content = post.get('content', '').lower()
                category_match = post.get('category', '').lower()
                if keyword.lower() not in content and keyword.lower() not in category_match:
                    continue
            
            # カテゴリー検索
            if category:
                post_category = post.get('category', '').lower()
                if category.lower() not in post_category:
                    continue
            
            # 著者検索
            if author_id:
                if post.get('user_id') != author_id:
                    continue
            
            # 日付検索
            if date_from or date_to:
                try:
                    post_date = datetime.fromisoformat(post.get('created_at', '').replace('Z', '+00:00'))
                    if date_from and post_date < date_from:
                        continue
                    if date_to and post_date > date_to:
                        continue
                except (ValueError, TypeError):
                    continue
            
            # 匿名フィルター
            if is_anonymous is not None:
                if post.get('is_anonymous') != is_anonymous:
                    continue
            
            filtered_posts.append(post)
        
        # 作成日でソート（新しい順）
        filtered_posts.sort(
            key=lambda x: datetime.fromisoformat(x.get('created_at', '').replace('Z', '+00:00')),
            reverse=True
        )
        
        return filtered_posts[:MAX_SEARCH_RESULTS]
        
    except Exception as e:
        logger.error(f"投稿検索中にエラー: {e}")
        return []

def search_replies(
    keyword: Optional[str] = None,
    author_id: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    reply_manager: Optional[ReplyManager] = None
) -> List[Dict[str, Any]]:
    """リプライを検索する"""
    if not reply_manager:
        return []
    
    try:
        # 全リプライを取得
        all_replies = reply_manager.get_all_replies()
        
        # 検索条件でフィルタリング
        filtered_replies = []
        for reply in all_replies:
            # キーワード検索
            if keyword:
                content = reply.get('content', '').lower()
                if keyword.lower() not in content:
                    continue
            
            # 著者検索
            if author_id:
                if reply.get('user_id') != author_id:
                    continue
            
            # 日付検索
            if date_from or date_to:
                try:
                    reply_date = datetime.fromisoformat(reply.get('created_at', '').replace('Z', '+00:00'))
                    if date_from and reply_date < date_from:
                        continue
                    if date_to and reply_date > date_to:
                        continue
                except (ValueError, TypeError):
                    continue
            
            filtered_replies.append(reply)
        
        # 作成日でソート（新しい順）
        filtered_replies.sort(
            key=lambda x: datetime.fromisoformat(x.get('created_at', '').replace('Z', '+00:00')),
            reverse=True
        )
        
        return filtered_replies[:MAX_SEARCH_RESULTS]
        
    except Exception as e:
        logger.error(f"リプライ検索中にエラー: {e}")
        return []

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

def parse_date_string(date_str: str) -> Optional[datetime]:
    """日付文字列を解析"""
    try:
        # YYYY-MM-DD形式を解析
        if len(date_str) == 10 and date_str.count('-') == 2:
            return datetime.strptime(date_str, '%Y-%m-%d')
        
        # その他の形式を試す
        formats = ['%Y/%m/%d', '%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M']
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None
    except Exception:
        return None

def validate_search_params(
    keyword: Optional[str],
    category: Optional[str],
    date_from_str: Optional[str],
    date_to_str: Optional[str]
) -> tuple[bool, str]:
    """検索パラメータを検証"""
    # 日付の検証
    date_from = None
    date_to = None
    
    if date_from_str:
        date_from = parse_date_string(date_from_str)
        if not date_from:
            return False, "開始日付の形式が正しくありません。YYYY-MM-DD形式で入力してください。"
    
    if date_to_str:
        date_to = parse_date_string(date_to_str)
        if not date_to:
            return False, "終了日付の形式が正しくありません。YYYY-MM-DD形式で入力してください。"
    
    # 日付範囲の検証
    if date_from and date_to:
        if date_from > date_to:
            return False, "開始日付は終了日付より前にしてください。"
    
    # キーワードの検証
    if keyword and len(keyword.strip()) < 2:
        return False, "キーワードは2文字以上で入力してください。"
    
    # カテゴリーの検証
    if category and len(category.strip()) < 2:
        return False, "カテゴリーは2文字以上で入力してください。"
    
    return True, ""
