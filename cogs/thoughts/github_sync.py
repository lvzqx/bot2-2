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
    ファイルベースのデータ変更をGitHubに同期する
    
    Args:
        action_description: アクションの説明 (例: "edit", "delete", "like")
        user_name: 実行ユーザー名 (オプション)
        post_id: 投稿ID (オプション)
    
    Returns:
        str: GitHub同期の結果メッセージ
    """
    try:
        # dataディレクトリのパスを取得
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
        
        # 強制的に変更を検知させるための処理
        # タイムスタンプファイルを作成
        timestamp_file = os.path.join(data_dir, '.last_sync')
        with open(timestamp_file, 'w') as f:
            f.write(datetime.now().isoformat())
        
        # ファイルのタイムスタンプを更新
        if os.path.exists(data_dir):
            os.utime(data_dir)
        
        # コミットメッセージを作成
        if post_id and user_name:
            commit_message = f"🔄 {action_description.capitalize()} post #{post_id} by {user_name} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        elif user_name:
            commit_message = f"🔄 {action_description.capitalize()} by {user_name} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        else:
            commit_message = f"🔄 {action_description.capitalize()} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # git add
        subprocess.run(['git', 'add', 'data/'], 
                     capture_output=True, text=True, check=True)
        
        # 必ずコミット（変更チェックなし）
        max_retries = 3  # 3回に減らして整理
        for attempt in range(max_retries):
            try:
                # git commit
                subprocess.run(['git', 'commit', '-m', commit_message], 
                             capture_output=True, text=True, check=True)
                
                # git push（リトライ付き）
                for push_attempt in range(max_retries):
                    try:
                        subprocess.run(['git', 'push', 'origin', 'main'], 
                                     capture_output=True, text=True, check=True)
                        
                        success_msg = f"✅ GitHubに保存しました: {action_description}"
                        logger.info(success_msg)
                        return success_msg
                        
                    except subprocess.CalledProcessError as push_error:
                        if push_attempt < max_retries - 1:
                            logger.warning(f"Git push失敗、リトライします (試行 {push_attempt + 1}/{max_retries}): {push_error.stderr.strip()}")
                            # リモートの変更を取得してリベース
                            subprocess.run(['git', 'pull', '--rebase', 'origin', 'main'], 
                                         capture_output=True, text=True, check=False)
                            import time
                            time.sleep(2)
                        else:
                            # 最終手段：クリーンな強制プッシュ
                            logger.error("最終手段：クリーンな強制プッシュを実行します")
                            subprocess.run(['git', 'push', 'origin', 'main', '--force'], 
                                         capture_output=True, text=True, check=False)
                            success_msg = f"🔄 強制プッシュでGitHubに保存しました: {action_description}"
                            logger.info(success_msg)
                            return success_msg
                
            except subprocess.CalledProcessError as commit_error:
                if attempt < max_retries - 1:
                    logger.warning(f"Git commit失敗、リトライします (試行 {attempt + 1}/{max_retries}): {commit_error.stderr.strip()}")
                    import time
                    time.sleep(2)
                else:
                    # 最終手段：クリーンな強制コミット
                    logger.error("最終手段：クリーンな強制コミットを実行します")
                    subprocess.run(['git', 'add', '-A'], 
                                 capture_output=True, text=True, check=False)
                    subprocess.run(['git', 'commit', '-m', f'🔄 File sync - {action_description} - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'], 
                                 capture_output=True, text=True, check=False)
                    subprocess.run(['git', 'push', 'origin', 'main', '--force'], 
                                 capture_output=True, text=True, check=False)
                    success_msg = f"🔄 強制コミットでGitHubに保存しました: {action_description}"
                    logger.info(success_msg)
                    return success_msg
        
    except subprocess.CalledProcessError as git_error:
        error_msg = f"⚠️ GitHub保存に失敗: {git_error.stderr.strip()}"
        logger.warning(f"GitHub保存失敗: {git_error}")
        return error_msg
    except Exception as git_error:
        error_msg = f"⚠️ GitHub保存エラー: {str(git_error)}"
        logger.warning(f"GitHub保存エラー: {git_error}")
        return error_msg
