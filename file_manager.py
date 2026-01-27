import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

class FileManager:
    """ファイルベースのデータ管理"""
    
    def __init__(self, base_dir: str = "data"):
        self.base_dir = base_dir
        self.posts_dir = os.path.join(base_dir, "posts")
        self.replies_dir = os.path.join(base_dir, "replies")
        self.likes_dir = os.path.join(base_dir, "likes")
        
        # ディレクトリがなければ作成
        os.makedirs(self.posts_dir, exist_ok=True)
        os.makedirs(self.replies_dir, exist_ok=True)
        os.makedirs(self.likes_dir, exist_ok=True)
    
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
        """ユーザーといいねされた投稿IDからいいねデータを取得"""
        for filename in os.listdir(self.likes_dir):
            if filename.startswith(f'{post_id}_') and filename.endswith('.json'):
                try:
                    with open(os.path.join(self.likes_dir, filename), 'r', encoding='utf-8') as f:
                        like_data = json.load(f)
                    
                    if like_data.get('user_id') == user_id:
                        return like_data
                except (json.JSONDecodeError, FileNotFoundError):
                    continue
        return None
    
    def delete_like(self, post_id: int, user_id: str) -> bool:
        """いいねを削除"""
        like_data = self.get_like_by_user_and_post(post_id, user_id)
        if not like_data:
            return False
        
        filename = os.path.join(self.likes_dir, f"{post_id}_{like_data['id']}.json")
        try:
            os.remove(filename)
            return True
        except FileNotFoundError:
            return False
    
    def get_reply_by_id_and_user(self, reply_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """リプライIDとユーザーIDからリプライデータを取得"""
        for filename in os.listdir(self.replies_dir):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(self.replies_dir, filename), 'r', encoding='utf-8') as f:
                        reply_data = json.load(f)
                    
                    if (reply_data.get('id') == reply_id and 
                        reply_data.get('user_id') == user_id):
                        return reply_data
                except (json.JSONDecodeError, FileNotFoundError):
                    continue
        return None
    
    def delete_reply(self, reply_id: str, user_id: str) -> bool:
        """リプライを削除"""
        reply_data = self.get_reply_by_id_and_user(reply_id, user_id)
        if not reply_data:
            return False
        
        # ファイル名を特定して削除
        for filename in os.listdir(self.replies_dir):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(self.replies_dir, filename), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if (data.get('id') == reply_id and 
                        data.get('user_id') == user_id):
                        os.remove(os.path.join(self.replies_dir, filename))
                        return True
                except (json.JSONDecodeError, FileNotFoundError):
                    continue
        return False
    
    def update_reply(self, post_id: int, reply_id: int, content: str) -> bool:
        """リプライを更新"""
        for filename in os.listdir(self.replies_dir):
            if filename.startswith(f'{post_id}_') and filename.endswith('.json'):
                try:
                    with open(os.path.join(self.replies_dir, filename), 'r', encoding='utf-8') as f:
                        reply_data = json.load(f)
                    
                    if reply_data.get('id') == reply_id:
                        reply_data['content'] = content
                        reply_data['updated_at'] = datetime.now().isoformat()
                        
                        with open(os.path.join(self.replies_dir, filename), 'w', encoding='utf-8') as f:
                            json.dump(reply_data, f, ensure_ascii=False, indent=2)
                        return True
                except (json.JSONDecodeError, FileNotFoundError):
                    continue
        return False
    
    def save_action_record(self, action_type: str, user_id: str, target_id: str, 
                          action_data: Dict[str, Any] = None) -> None:
        """アクション記録を保存"""
        # アクション専用フォルダーを作成
        action_dir = os.path.join(self.base_dir, 'data', 'actions')
        os.makedirs(action_dir, exist_ok=True)
        
        action_record = {
            'action_type': action_type,
            'user_id': user_id,
            'target_id': target_id,
            'timestamp': datetime.now().isoformat(),
            'data': action_data or {}
        }
        
        action_filename = os.path.join(action_dir, f"action_{action_type}_{user_id}_{target_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        with open(action_filename, 'w', encoding='utf-8') as f:
            json.dump(action_record, f, ensure_ascii=False, indent=2)
        
        logger.info(f"アクション記録完了: {action_type} by user {user_id} on target {target_id}")
    
    def save_message_ref(self, post_id: int, message_id: str, channel_id: str, user_id: str) -> None:
        """メッセージ参照を保存"""
        # メッセージ参照専用フォルダーを作成
        message_ref_dir = os.path.join(self.base_dir, 'data', 'message_refs')
        os.makedirs(message_ref_dir, exist_ok=True)
        
        message_ref_file = os.path.join(message_ref_dir, f'message_ref_{post_id}.json')
        
        message_ref_data = {
            'post_id': post_id,
            'message_id': message_id,
            'channel_id': channel_id,
            'user_id': user_id,
            'created_at': datetime.now().isoformat()
        }
        
        with open(message_ref_file, 'w', encoding='utf-8') as f:
            json.dump(message_ref_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"メッセージ参照を保存しました: 投稿ID={post_id}")
    
    def get_message_ref(self, post_id: int) -> Optional[Dict[str, Any]]:
        """メッセージ参照を取得"""
        message_ref_dir = os.path.join(self.base_dir, 'data', 'message_refs')
        message_ref_file = os.path.join(message_ref_dir, f'message_ref_{post_id}.json')
        
        if not os.path.exists(message_ref_file):
            return None
        
        try:
            with open(message_ref_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return None
    
    def delete_message_ref(self, post_id: int) -> bool:
        """メッセージ参照を削除"""
        message_ref_dir = os.path.join(self.base_dir, 'data', 'message_refs')
        message_ref_file = os.path.join(message_ref_dir, f'message_ref_{post_id}.json')
        
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
    
    def save_reply(self, post_id: int, user_id: str, content: str, 
                   display_name: str) -> int:
        """リプライを保存"""
        # リプライIDを取得
        existing_replies = [f for f in os.listdir(self.replies_dir) 
                           if f.startswith(f"{post_id}_") and f.endswith('.json')]
        
        reply_id = len(existing_replies) + 1
        
        reply_data = {
            "id": reply_id,
            "post_id": post_id,
            "user_id": user_id,
            "content": content,
            "display_name": display_name,
            "created_at": datetime.now().isoformat()
        }
        
        filename = os.path.join(self.replies_dir, f"{post_id}_{reply_id}.json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(reply_data, f, ensure_ascii=False, indent=2)
        
        return reply_id
    
    def get_replies(self, post_id: int) -> List[Dict[str, Any]]:
        """投稿のリプライを取得"""
        replies = []
        
        for filename in sorted(os.listdir(self.replies_dir)):
            if filename.startswith(f"{post_id}_") and filename.endswith('.json'):
                try:
                    with open(os.path.join(self.replies_dir, filename), 'r', encoding='utf-8') as f:
                        reply = json.load(f)
                        replies.append(reply)
                except (json.JSONDecodeError, FileNotFoundError):
                    continue
        
        return replies
    
    def save_like(self, post_id: int, user_id: str, display_name: str) -> int:
        """いいねを保存"""
        # いいねIDを取得
        existing_likes = [f for f in os.listdir(self.likes_dir) 
                        if f.startswith(f"{post_id}_") and f.endswith('.json')]
        
        like_id = len(existing_likes) + 1
        
        like_data = {
            "id": like_id,
            "post_id": post_id,
            "user_id": user_id,
            "display_name": display_name,
            "created_at": datetime.now().isoformat()
        }
        
        filename = os.path.join(self.likes_dir, f"{post_id}_{like_id}.json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(like_data, f, ensure_ascii=False, indent=2)
        
        return like_id
    
    def update_like_message_id(self, like_id: int, message_id: str, channel_id: str, forwarded_message_id: str = None) -> None:
        """いいねファイルにメッセージIDを更新"""
        # 全いいねファイルを検索
        for filename in os.listdir(self.likes_dir):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(self.likes_dir, filename), 'r', encoding='utf-8') as f:
                        like_data = json.load(f)
                    
                    if like_data.get('id') == like_id:
                        # メッセージIDを追加・更新
                        like_data['message_id'] = message_id
                        like_data['channel_id'] = channel_id
                        if forwarded_message_id:
                            like_data['forwarded_message_id'] = forwarded_message_id
                        
                        # ファイルを更新
                        with open(os.path.join(self.likes_dir, filename), 'w', encoding='utf-8') as f:
                            json.dump(like_data, f, ensure_ascii=False, indent=2)
                        break
                except (json.JSONDecodeError, FileNotFoundError):
                    continue
    
    def update_reply_message_id(self, reply_id: int, message_id: str, channel_id: str, forwarded_message_id: str = None) -> None:
        """リプライファイルにメッセージIDを更新"""
        # 全リプライファイルを検索
        for filename in os.listdir(self.replies_dir):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(self.replies_dir, filename), 'r', encoding='utf-8') as f:
                        reply_data = json.load(f)
                    
                    if reply_data.get('id') == reply_id:
                        # メッセージIDを追加・更新
                        reply_data['message_id'] = message_id
                        reply_data['channel_id'] = channel_id
                        if forwarded_message_id:
                            reply_data['forwarded_message_id'] = forwarded_message_id
                        
                        # ファイルを更新
                        with open(os.path.join(self.replies_dir, filename), 'w', encoding='utf-8') as f:
                            json.dump(reply_data, f, ensure_ascii=False, indent=2)
                        break
                except (json.JSONDecodeError, FileNotFoundError):
                    continue
    
    def save_message_ref(self, post_id: int, message_id: str, channel_id: str, user_id: str) -> None:
        """メッセージ参照を保存"""
        message_ref_data = {
            "post_id": post_id,
            "message_id": message_id,
            "channel_id": channel_id,
            "user_id": user_id,
            "created_at": datetime.now().isoformat()
        }
        
        filename = os.path.join(self.base_dir, f"message_ref_{post_id}.json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(message_ref_data, f, ensure_ascii=False, indent=2)
    
    def get_message_ref(self, post_id: int) -> Optional[Dict[str, Any]]:
        """メッセージ参照を取得"""
        filename = os.path.join(self.base_dir, f"message_ref_{post_id}.json")
        
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        
        return None
    
    def get_likes(self, post_id: int) -> List[Dict[str, Any]]:
        """投稿のいいねを取得"""
        likes = []
        
        for filename in sorted(os.listdir(self.likes_dir)):
            if filename.startswith(f"{post_id}_") and filename.endswith('.json'):
                try:
                    with open(os.path.join(self.likes_dir, filename), 'r', encoding='utf-8') as f:
                        like = json.load(f)
                        likes.append(like)
                except (json.JSONDecodeError, FileNotFoundError):
                    continue
        
        return likes
    
    def delete_post(self, post_id: int) -> bool:
        """投稿を削除"""
        filename = os.path.join(self.posts_dir, f"{post_id}.json")
        
        if os.path.exists(filename):
            os.remove(filename)
            
            # 関連するリプライといいねも削除
            for filename in os.listdir(self.replies_dir):
                if filename.startswith(f"{post_id}_"):
                    os.remove(os.path.join(self.replies_dir, filename))
            
            for filename in os.listdir(self.likes_dir):
                if filename.startswith(f"{post_id}_"):
                    os.remove(os.path.join(self.likes_dir, filename))
            
            return True
        
        return False
