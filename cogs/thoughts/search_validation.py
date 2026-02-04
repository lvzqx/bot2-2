"""
検索バリデーションと解析ロジック
"""

import logging
import os
from typing import Optional, tuple
from datetime import datetime

# ロガー設定
logger = logging.getLogger(__name__)

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
