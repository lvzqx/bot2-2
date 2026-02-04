"""
検索リプライロジック
"""

import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

# マネージャーをインポート
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from managers.reply_manager import ReplyManager

# ロガー設定
logger = logging.getLogger(__name__)

# 定数
MAX_SEARCH_RESULTS = 50

# 型定義
ReplyData = Dict[str, Any]

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
                content = (reply.get('content') or '').lower()
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
