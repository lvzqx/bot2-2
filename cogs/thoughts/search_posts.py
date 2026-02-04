"""
検索投稿ロジック
"""

import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

# マネージャーをインポート
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from managers.post_manager import PostManager

# ロガー設定
logger = logging.getLogger(__name__)

# 定数
MAX_SEARCH_RESULTS = 50

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
        logger.info(f"🔍 検索デバッグ: 全投稿数={len(all_posts)}")
        
        if not all_posts:
            logger.warning("⚠️ 検索デバッグ: 投稿データがありません")
            return []
        
        # 検索条件をログ
        logger.info(f"🔍 検索条件: keyword={keyword}, category={category}, author_id={author_id}")
        
        # 検索条件でフィルタリング
        filtered_posts = []
        for i, post in enumerate(all_posts):
            logger.info(f"🔍 投稿{i+1}: ID={post.get('id')}, content={post.get('content', '')[:50]}...")
            
            # キーワード検索
            if keyword:
                content = post.get('content', '').lower()
                category_match = post.get('category', '').lower()
                keyword_lower = keyword.lower()
                
                content_match = keyword_lower in content
                category_match_result = keyword_lower in category_match
                
                logger.info(f"  - キーワード検索: '{keyword_lower}'")
                logger.info(f"    * content match: {content_match}")
                logger.info(f"    * category match: {category_match_result}")
                
                if not content_match and not category_match_result:
                    logger.info(f"  ❌ キーワードに一致しないためスキップ")
                    continue
                else:
                    logger.info(f"  ✅ キーワードに一致")
            
            # カテゴリー検索
            if category:
                post_category = post.get('category', '').lower()
                category_lower = category.lower()
                category_match = category_lower in post_category
                
                logger.info(f"  - カテゴリー検索: '{category_lower}' in '{post_category}' = {category_match}")
                
                if not category_match:
                    logger.info(f"  ❌ カテゴリーに一致しないためスキップ")
                    continue
                else:
                    logger.info(f"  ✅ カテゴリーに一致")
            
            # 著者検索
            if author_id:
                post_author = post.get('user_id')
                author_match = post_author == author_id
                
                logger.info(f"  - 著者検索: {post_author} == {author_id} = {author_match}")
                
                if not author_match:
                    logger.info(f"  ❌ 著者に一致しないためスキップ")
                    continue
                else:
                    logger.info(f"  ✅ 著者に一致")
            
            # この投稿は全ての条件をクリア
            logger.info(f"  ✅ 投稿を検索結果に追加: ID={post.get('id')}")
            filtered_posts.append(post)
            
            # 日付検索
            if date_from or date_to:
                try:
                    post_date = datetime.fromisoformat(post.get('created_at', '').replace('Z', '+00:00'))
                    logger.info(f"  - 日付検索: {post_date}")
                    
                    if date_from and post_date < date_from:
                        logger.info(f"    ❌ 開始日より前のためスキップ: {post_date} < {date_from}")
                        continue
                    if date_to and post_date > date_to:
                        logger.info(f"    ❌ 終了日より後のためスキップ: {post_date} > {date_to}")
                        continue
                    
                    logger.info(f"    ✅ 日付範囲内")
                except (ValueError, TypeError):
                    logger.warning(f"    ⚠️ 日付解析エラー: {post.get('created_at')}")
                    continue
            
            # 匿名フィルター
            if is_anonymous is not None:
                post_anonymous = post.get('is_anonymous', False)
                anonymous_match = post_anonymous == is_anonymous
                
                logger.info(f"  - 匿名フィルター: {post_anonymous} == {is_anonymous} = {anonymous_match}")
                
                if not anonymous_match:
                    logger.info(f"    ❌ 匿名設定が一致しないためスキップ")
                    continue
                else:
                    logger.info(f"    ✅ 匿名設定が一致")
        
        logger.info(f"🔍 検索結果: {len(filtered_posts)}件の投稿が一致")
        
        # 作成日でソート（新しい順）
        filtered_posts.sort(
            key=lambda x: datetime.fromisoformat(x.get('created_at', '').replace('Z', '+00:00')),
            reverse=True
        )
        
        return filtered_posts[:MAX_SEARCH_RESULTS]
        
    except Exception as e:
        logger.error(f"投稿検索中にエラー: {e}")
        return []
