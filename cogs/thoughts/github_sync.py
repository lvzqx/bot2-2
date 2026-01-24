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
        
        # 強制的に変更を検知させるためにタイムスタンプを更新
        os.utime(bot_db_path)
        
        # ダミーの変更を加えて確実にコミット対象にする
        import sqlite3
        conn = sqlite3.connect(bot_db_path)
        cursor = conn.cursor()
        
        # git_sync_markerテーブルにタイムスタンプを記録して強制変更
        cursor.execute('CREATE TABLE IF NOT EXISTS git_sync_marker (timestamp TEXT)')
        cursor.execute('INSERT OR REPLACE INTO git_sync_marker (timestamp) VALUES (?)', 
                      (datetime.now().isoformat(),))
        conn.commit()
        conn.close()
        
        # タイムスタンプ更新後に再度git add
        subprocess.run(['git', 'add', bot_db_path], 
                     capture_output=True, text=True, check=True)
        
        # 必ずコミット（変更チェックなし）
        try:
            # git commit（変更がない場合は無視）
            result = subprocess.run(['git', 'commit', '-m', commit_message], 
                         capture_output=True, text=True, check=False)
            
            # git push（リトライ付き）
            max_retries = 3
            for attempt in range(max_retries):
                result = subprocess.run(['git', 'push', 'origin', 'main'], 
                             capture_output=True, text=True, check=False)
                
                if result.returncode == 0:
                    success_msg = f" GitHubに保存しました: {action_description}"
                    logger.info(success_msg)
                    return success_msg
                else:
                    if "nothing to push" in result.stderr.lower():
                        success_msg = f" GitHubに保存しました: {action_description}（プッシュ不要）"
                        logger.info(success_msg)
                        return success_msg
                    elif attempt < max_retries - 1:
                        logger.warning(f"GitHubプッシュ失敗（リトライ {attempt + 1}/{max_retries}）: {result.stderr}")
                        import time
                        time.sleep(2)  # 2秒待機
                    else:
                        error_msg = f" GitHub保存に失敗: {result.stderr.strip()}"
                        logger.warning(f"GitHub保存失敗: {result.stderr}")
                        return error_msg
            
        except subprocess.CalledProcessError as git_error:
            error_msg = f" GitHub保存に失敗: {git_error.stderr.strip()}"
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
