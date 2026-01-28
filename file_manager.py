import json
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

# データ保存を制御する環境変数
SAVE_DATA = os.getenv('SAVE_DATA', 'true').lower() == 'true'

logger = logging.getLogger(__name__)

class FileManager:
    """ファイルベースのデータ管理"""
    
    def __init__(self, base_dir: str = "data"):
        self.base_dir = base_dir
        self.posts_dir = os.path.join(base_dir, "posts")
        self.replies_dir = os.path.join(base_dir, "replies")
        self.likes_dir = os.path.join(base_dir, "likes")
        self.actions_dir = os.path.join(base_dir, "actions")
        self.message_refs_dir = os.path.join(base_dir, "message_refs")
        
        # ディレクトリがなければ作成
        os.makedirs(self.posts_dir, exist_ok=True)
        os.makedirs(self.replies_dir, exist_ok=True)
        os.makedirs(self.likes_dir, exist_ok=True)
        os.makedirs(self.actions_dir, exist_ok=True)
        os.makedirs(self.message_refs_dir, exist_ok=True)
    
    def get_next_post_id(self) -> int:
        """次の投稿IDを取得"""
        existing_posts = [f for f in os.listdir(self.posts_dir) if f.endswith('.json')]
        if not existing_posts:
            return 1
        
        max_id = 0
        for filename in existing_posts:
            try:
                post_id = int(filename.replace('.json', ''))
                max_id = max(max_id, post_id)
            except ValueError:
                continue
        
        return max_id + 1
    
    def save_post(self, user_id: str, content: str, category: str = None, 
                  is_anonymous: bool = False, is_private: bool = False,
                  display_name: str = None, message_id: str = None, 
                  channel_id: str = None, image_url: str = None) -> int:
        """投稿を保存"""
        post_id = self.get_next_post_id()
        
        post_data = {
            "id": post_id,
            "user_id": user_id,
            "content": content,
            "category": category,
            "is_anonymous": is_anonymous,
            "is_private": is_private,
            "display_name": display_name,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "message_id": message_id,
            "channel_id": channel_id,
            "image_url": image_url
        }
        
        filename = os.path.join(self.posts_dir, f"{post_id}.json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(post_data, f, ensure_ascii=False, indent=2)
        
        return post_id
    
    def get_post(self, post_id: int) -> Optional[Dict[str, Any]]:
        """投稿を取得"""
        filename = os.path.join(self.posts_dir, f"{post_id}.json")
        
        if not os.path.exists(filename):
            return None
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return None
    
    def get_all_posts(self) -> List[Dict[str, Any]]:
        """全投稿を取得"""
        posts = []
        
        for filename in sorted(os.listdir(self.posts_dir)):
            if filename.endswith('.json'):
                try:
                    post_id = int(filename.replace('.json', ''))
                    post = self.get_post(post_id)
                    if post:
                        posts.append(post)
                except ValueError:
                    continue
        
        return posts
    
    def update_post(self, post_id: int, content: str = None, category: str = None, 
                   image_url: str = None) -> bool:
        """投稿を更新"""
        filename = os.path.join(self.posts_dir, f"{post_id}.json")
        
        if not os.path.exists(filename):
            return False
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                post_data = json.load(f)
            
            # 内容を更新
            if content is not None:
                post_data['content'] = content
            if category is not None:
                post_data['category'] = category
            if image_url is not None:
                post_data['image_url'] = image_url
            
            post_data['updated_at'] = datetime.now().isoformat()
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(post_data, f, ensure_ascii=False, indent=2)
            
            return True
        except (json.JSONDecodeError, FileNotFoundError):
            return False
    
    def get_like_by_user_and_post(self, post_id: int, user_id: str) -> Optional[Dict[str, Any]]:
        """ユーザーといいねされた投稿IDからいいねデータを取得（新しい仕組み）"""
        for filename in os.listdir(self.likes_dir):
            if filename.startswith('like_') and filename.endswith('.json'):
                try:
                    with open(os.path.join(self.likes_dir, filename), 'r', encoding='utf-8') as f:
                        like_data = json.load(f)
                    
                    if (like_data.get('post_id') == post_id and 
                        like_data.get('user_id') == user_id):
                        return like_data
                except (json.JSONDecodeError, FileNotFoundError):
                    continue
        return None
    
    def delete_like(self, post_id: int, user_id: str) -> bool:
        """いいねを削除（新しい仕組み）"""
        like_data = self.get_like_by_user_and_post(post_id, user_id)
        if not like_data:
            return False
        
        filename = os.path.join(self.likes_dir, f"like_{like_data['id']}.json")
        try:
            os.remove(filename)
            return True
        except FileNotFoundError:
            return False
    
    def get_reply_by_id_and_user(self, reply_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """リプライIDとユーザーIDからリプライデータを取得（新しい仕組み）"""
        for filename in os.listdir(self.replies_dir):
            if filename.startswith('reply_') and filename.endswith('.json'):
                try:
                    with open(os.path.join(self.replies_dir, filename), 'r', encoding='utf-8') as f:
                        reply_data = json.load(f)
                    
                    if (str(reply_data.get('id')) == str(reply_id) and 
                        reply_data.get('user_id') == user_id):
                        return reply_data
                except (json.JSONDecodeError, FileNotFoundError):
                    continue
        return None
    
    def delete_reply(self, reply_id: str, user_id: str) -> bool:
        """リプライを削除（新しい仕組み）"""
        reply_data = self.get_reply_by_id_and_user(reply_id, user_id)
        if not reply_data:
            return False
        
        # グローバルIDでファイル名を特定して削除
        filename = os.path.join(self.replies_dir, f"reply_{reply_id}.json")
        try:
            os.remove(filename)
            return True
        except FileNotFoundError:
            return False
    
    def update_reply(self, post_id: int, reply_id: int, content: str) -> bool:
        """リプライを更新（新しい仕組み）"""
        filename = os.path.join(self.replies_dir, f"reply_{reply_id}.json")
        
        if not os.path.exists(filename):
            return False
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                reply_data = json.load(f)
            
            if reply_data.get('post_id') != post_id:
                return False
            
            reply_data['content'] = content
            reply_data['updated_at'] = datetime.now().isoformat()
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(reply_data, f, ensure_ascii=False, indent=2)
            
            return True
        except (json.JSONDecodeError, FileNotFoundError):
            return False
    
    def save_action_record(self, action_type: str, user_id: str, target_id: str, 
                          action_data: Dict[str, Any] = None) -> None:
        """アクション記録を保存"""
        # アクション専用フォルダーは__init__で作成済み
        
        action_record = {
            'action_type': action_type,
            'user_id': user_id,
            'target_id': target_id,
            'timestamp': datetime.now().isoformat(),
            'data': action_data or {}
        }
        
        action_filename = os.path.join(self.actions_dir, f"action_{action_type}_{user_id}_{target_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        with open(action_filename, 'w', encoding='utf-8') as f:
            json.dump(action_record, f, ensure_ascii=False, indent=2)
        
        logger.info(f"アクション記録完了: {action_type} by user {user_id} on target {target_id}")
    
    def save_message_ref(self, post_id: int, message_id: str, channel_id: str, user_id: str) -> None:
        """メッセージ参照を保存"""
        # メッセージ参照フォルダーは__init__で作成済み
        
        message_ref_data = {
            "post_id": post_id,
            "message_id": message_id,
            "channel_id": channel_id,
            "user_id": user_id,
            "created_at": datetime.now().isoformat()
        }
        
        message_ref_file = os.path.join(self.message_refs_dir, f'message_ref_{post_id}.json')
        
        with open(message_ref_file, 'w', encoding='utf-8') as f:
            json.dump(message_ref_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"メッセージ参照を保存しました: 投稿ID={post_id}")
    
    def get_message_ref(self, post_id: int) -> Optional[Dict[str, Any]]:
        """メッセージ参照を取得"""
        message_ref_file = os.path.join(self.message_refs_dir, f'message_ref_{post_id}.json')
        
        if not os.path.exists(message_ref_file):
            return None
        
        try:
            with open(message_ref_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return None
    
    def delete_message_ref(self, post_id: int) -> bool:
        """メッセージ参照を削除"""
        message_ref_file = os.path.join(self.message_refs_dir, f'message_ref_{post_id}.json')
        
        try:
            os.remove(message_ref_file)
            return True
        except FileNotFoundError:
            return False
    
    def get_replies_by_post_id(self, post_id: int) -> List[Dict[str, Any]]:
        """投稿IDから全リプライを取得"""
        replies = []
        
        for filename in os.listdir(self.replies_dir):
            if filename.startswith(f'{post_id}_') and filename.endswith('.json'):
                try:
                    with open(os.path.join(self.replies_dir, filename), 'r', encoding='utf-8') as f:
                        reply_data = json.load(f)
                        replies.append(reply_data)
                except (json.JSONDecodeError, FileNotFoundError):
                    continue
        
        return replies
    
    def delete_replies_by_post_id(self, post_id: int) -> int:
        """投稿IDから全リプライを削除"""
        deleted_count = 0
        
        for filename in os.listdir(self.replies_dir):
            if filename.startswith(f'{post_id}_') and filename.endswith('.json'):
                try:
                    os.remove(os.path.join(self.replies_dir, filename))
                    deleted_count += 1
                except FileNotFoundError:
                    continue
        
        return deleted_count
    
    def search_posts(self, keyword: str = None, category: str = None, 
                     user_id: str = None) -> List[Dict[str, Any]]:
        """投稿を検索"""
        posts = self.get_all_posts()
        
        if keyword:
            keyword = keyword.lower()
            posts = [p for p in posts if keyword in p.get('content', '').lower()]
        
        if category:
            posts = [p for p in posts if p.get('category') == category]
        
        if user_id:
            posts = [p for p in posts if p.get('user_id') == user_id]
        
        return posts
    
    def get_next_reply_id(self) -> int:
        """次のリプライIDを取得（postと同じ仕組み）"""
        existing_replies = [f for f in os.listdir(self.replies_dir) if f.endswith('.json')]
        if not existing_replies:
            return 1
        
        max_id = 0
        for filename in existing_replies:
            try:
                # ファイル名からIDを抽出（例: reply_123.json）
                reply_id = int(filename.replace('.json', '').replace('reply_', ''))
                max_id = max(max_id, reply_id)
            except ValueError:
                continue
        
        return max_id + 1
    
    def save_reply(self, post_id: int, user_id: str, content: str, 
                   display_name: str) -> int:
        """リプライを保存"""
        if not SAVE_DATA:
            # データ保存を無効化 - ダミーIDを返す
            return 1
        
        # グローバルIDを取得（postと同じ仕組み）
        reply_id = self.get_next_reply_id()
        
        reply_data = {
            "id": reply_id,
            "post_id": post_id,
            "user_id": user_id,
            "content": content,
            "display_name": display_name,
            "created_at": datetime.now().isoformat()
        }
        
        # グローバルIDでファイル名を生成（postと同じ仕組み）
        filename = os.path.join(self.replies_dir, f"reply_{reply_id}.json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(reply_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"リプライを保存しました: reply_id={reply_id}, post_id={post_id}, user_id={user_id}")
        return reply_id
    
    def get_replies(self, post_id: int) -> List[Dict[str, Any]]:
        """投稿のリプライを取得（新しい仕組み）"""
        replies = []
        
        for filename in sorted(os.listdir(self.replies_dir)):
            if filename.startswith('reply_') and filename.endswith('.json'):
                try:
                    with open(os.path.join(self.replies_dir, filename), 'r', encoding='utf-8') as f:
                        reply = json.load(f)
                    
                    if reply.get('post_id') == post_id:
                        replies.append(reply)
                except (json.JSONDecodeError, FileNotFoundError):
                    continue
        
        return replies
    
    def get_next_like_id(self) -> int:
        """次のいいねIDを取得（postと同じ仕組み）"""
        existing_likes = [f for f in os.listdir(self.likes_dir) if f.endswith('.json')]
        if not existing_likes:
            return 1
        
        max_id = 0
        for filename in existing_likes:
            try:
                # ファイル名からIDを抽出（例: like_123.json）
                like_id = int(filename.replace('.json', '').replace('like_', ''))
                max_id = max(max_id, like_id)
            except ValueError:
                continue
        
        return max_id + 1
    
    def save_like(self, post_id: int, user_id: str, display_name: str) -> int:
        """いいねを保存"""
        if not SAVE_DATA:
            # データ保存を無効化 - ダミーIDを返す
            return 1
        
        # グローバルIDを取得（postと同じ仕組み）
        like_id = self.get_next_like_id()
        
        like_data = {
            "id": like_id,
            "post_id": post_id,
            "user_id": user_id,
            "display_name": display_name,
            "created_at": datetime.now().isoformat()
        }
        
        # グローバルIDでファイル名を生成（postと同じ仕組み）
        filename = os.path.join(self.likes_dir, f"like_{like_id}.json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(like_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"いいねを保存しました: like_id={like_id}, post_id={post_id}, user_id={user_id}")
        return like_id
    
    def update_like_message_id(self, like_id: int, message_id: str, channel_id: str, forwarded_message_id: str = None) -> None:
        """いいねファイルにメッセージIDを更新（新しい仕組み）"""
        filename = os.path.join(self.likes_dir, f"like_{like_id}.json")
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                like_data = json.load(f)
            
            # メッセージIDを追加・更新
            like_data['message_id'] = message_id
            like_data['channel_id'] = channel_id
            if forwarded_message_id:
                like_data['forwarded_message_id'] = forwarded_message_id
            
            # ファイルを更新
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(like_data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"いいねメッセージIDを更新しました: like_id={like_id}")
        except (json.JSONDecodeError, FileNotFoundError):
            logger.warning(f"いいねメッセージID更新失敗: like_id={like_id}")
    
    def update_reply_message_id(self, reply_id: int, message_id: str, channel_id: str, forwarded_message_id: str = None) -> None:
        """リプライファイルにメッセージIDを更新（新しい仕組み）"""
        filename = os.path.join(self.replies_dir, f"reply_{reply_id}.json")
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                reply_data = json.load(f)
            
            # メッセージIDを追加・更新
            reply_data['message_id'] = message_id
            reply_data['channel_id'] = channel_id
            if forwarded_message_id:
                reply_data['forwarded_message_id'] = forwarded_message_id
            
            # ファイルを更新
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(reply_data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"リプライメッセージIDを更新しました: reply_id={reply_id}")
        except (json.JSONDecodeError, FileNotFoundError):
            logger.warning(f"リプライメッセージID更新失敗: reply_id={reply_id}")
    
    def get_likes(self, post_id: int) -> List[Dict[str, Any]]:
        """投稿のいいねを取得（新しい仕組み）"""
        likes = []
        
        for filename in sorted(os.listdir(self.likes_dir)):
            if filename.startswith('like_') and filename.endswith('.json'):
                try:
                    with open(os.path.join(self.likes_dir, filename), 'r', encoding='utf-8') as f:
                        like = json.load(f)
                    
                    if like.get('post_id') == post_id:
                        likes.append(like)
                except (json.JSONDecodeError, FileNotFoundError):
                    continue
        
        return likes
    
    def delete_post(self, post_id: int) -> bool:
        """投稿を削除（新しい仕組み）"""
        filename = os.path.join(self.posts_dir, f"{post_id}.json")
        
        if os.path.exists(filename):
            os.remove(filename)
            
            # 関連するリプライといいねも削除（新しい仕組み）
            deleted_replies = self.delete_replies_by_post_id(post_id)
            
            # いいねを削除
            likes = self.get_likes(post_id)
            for like in likes:
                filename = os.path.join(self.likes_dir, f"like_{like['id']}.json")
                try:
                    os.remove(filename)
                except FileNotFoundError:
                    continue
            
            return True
        
        return False
