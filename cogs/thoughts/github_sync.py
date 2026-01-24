"""
GitHub同期機能の共通モジュール
"""
import subprocess
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

async def sync_to_github(action_description: str, user_name: str = None, post_id: int = None):
    """
    データベースの変更をGitHubに同期する
    
    Args:
        action_description: アクションの説明 (例: "edit", "delete", "like")
        user_name: 実行ユーザー名 (オプション)
        post_id: 投稿ID (オプション)
    
    Returns:
        str: GitHub同期の結果メッセージ
    """
    try:
        # bot.dbのパスを取得
        bot_db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'bot.db')
        
        # コミットメッセージを作成
        if post_id and user_name:
            commit_message = f"🔄 {action_description.capitalize()} post #{post_id} by {user_name} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        elif user_name:
            commit_message = f"🔄 {action_description.capitalize()} by {user_name} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        else:
            commit_message = f"🔄 {action_description.capitalize()} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # git add
        subprocess.run(['git', 'add', bot_db_path], 
                     capture_output=True, text=True, check=True)
        
        # 必ずコミット（変更チェックなし）
        try:
            # git commit
            subprocess.run(['git', 'commit', '-m', commit_message], 
                         capture_output=True, text=True, check=True)
            
            # git push
            subprocess.run(['git', 'push', 'origin', 'main'], 
                         capture_output=True, text=True, check=True)
            
            success_msg = f"✅ GitHubに保存しました: {action_description}"
            logger.info(success_msg)
            return success_msg
            
        except subprocess.CalledProcessError as git_error:
            error_msg = f"⚠️ GitHub保存に失敗: {git_error.stderr.strip()}"
            logger.warning(f"GitHub保存失敗: {git_error}")
            return error_msg
        
    except subprocess.CalledProcessError as git_error:
        error_msg = f"⚠️ GitHub保存に失敗: {git_error.stderr.strip()}"
        logger.warning(f"GitHub保存失敗: {git_error}")
        return error_msg
    except Exception as git_error:
        error_msg = f"⚠️ GitHub保存エラー: {str(git_error)}"
        logger.warning(f"GitHub保存エラー: {git_error}")
        return error_msg
