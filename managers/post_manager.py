import json
import os
import logging
import hashlib
import base64
from typing import Dict, Any, List, Optional
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

class PostManager:
    """投稿機能の管理"""
    
    def __init__(self, base_dir: str = "data"):
        self.base_dir = base_dir
        self.posts_dir = os.path.join(base_dir, "posts")
        self.public_posts_dir = os.path.join(self.posts_dir, "public")
        self.private_posts_dir = os.path.join(self.posts_dir, "private")
        self.access_log_dir = os.path.join(base_dir, "logs", "access")
        
        # ディレクトリを作成
        os.makedirs(self.public_posts_dir, exist_ok=True)
        os.makedirs(self.private_posts_dir, exist_ok=True)
        os.makedirs(self.access_log_dir, exist_ok=True)
        
        # 暗号化キーを生成
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher = Fernet(self.encryption_key)
    
    def _get_or_create_encryption_key(self) -> bytes:
        """暗号化キーを取得または生成"""
        key_file = os.path.join(self.base_dir, ".encryption_key")
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        
        # 新しいキーを生成
        password = b"discord_bot_private_posts_2026"
        salt = b"discord_bot_salt_2026"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        
        # キーを保存
        with open(key_file, 'wb') as f:
            f.write(key)
        
        return key
    
    def _encrypt_content(self, content: str) -> str:
        """コンテンツを暗号化"""
        return self.cipher.encrypt(content.encode()).decode()
    
    def _decrypt_content(self, encrypted_content: str) -> str:
        """コンテンツを復号"""
        return self.cipher.decrypt(encrypted_content.encode()).decode()
    
    def _log_access(self, user_id: str, post_id: int, action: str, is_private: bool = False):
        """アクセスログを記録"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "post_id": post_id,
            "action": action,
            "is_private": is_private
        }
        
        log_file = os.path.join(self.access_log_dir, f"access_{datetime.now().strftime('%Y%m%d')}.json")
        
        # 既存のログを読み込む
        logs = []
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            except:
                logs = []
        
        # 新しいログを追加
        logs.append(log_entry)
        
        # ログを保存
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
    
    def get_next_post_id(self) -> int:
        """次の投稿IDを取得"""
        # 公開・非公開両方のディレクトリをチェック
        all_posts = []
        
        for directory in [self.public_posts_dir, self.private_posts_dir]:
            if os.path.exists(directory):
                all_posts.extend([f for f in os.listdir(directory) if f.endswith('.json')])
        
        if not all_posts:
            return 1
        
        max_id = 0
        for filename in all_posts:
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
        
        # 非公開投稿はコンテンツを暗号化
        content_to_save = content
        if is_private:
            content_to_save = self._encrypt_content(content)
        
        post_data = {
            "id": post_id,
            "user_id": user_id,
            "content": content_to_save,
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
        
        # 公開・非公開でディレクトリを分けて保存
        if is_private:
            filename = os.path.join(self.private_posts_dir, f"{post_id}.json")
        else:
            filename = os.path.join(self.public_posts_dir, f"{post_id}.json")
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(post_data, f, ensure_ascii=False, indent=2)
        
        # アクセスログを記録
        self._log_access(user_id, post_id, "create", is_private)
        
        return post_id
    
    def get_post(self, post_id: int, user_id: str = None) -> Optional[Dict[str, Any]]:
        """投稿を取得"""
        # 公開・非公開両方のディレクトリをチェック
        for directory in [self.public_posts_dir, self.private_posts_dir]:
            filename = os.path.join(directory, f"{post_id}.json")
            
            if os.path.exists(filename):
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        post_data = json.load(f)
                    
                    # 非公開投稿のアクセス制御
                    if post_data.get('is_private'):
                        if not user_id or post_data.get('user_id') != user_id:
                            return None
                        
                        # 非公開投稿は復号
                        post_data['content'] = self._decrypt_content(post_data['content'])
                    
                    # アクセスログを記録
                    self._log_access(user_id or "anonymous", post_id, "read", post_data.get('is_private', False))
                    
                    return post_data
                except (json.JSONDecodeError, FileNotFoundError):
                    continue
        
        return None
    
    def get_all_posts(self, user_id: str = None) -> List[Dict[str, Any]]:
        """全投稿を取得"""
        posts = []
        
        # 公開・非公開両方のディレクトリをチェック
        for directory in [self.public_posts_dir, self.private_posts_dir]:
            if not os.path.exists(directory):
                continue
                
            for filename in sorted(os.listdir(directory)):
                if filename.endswith('.json'):
                    try:
                        post_id = int(filename.replace('.json', ''))
                        post = self.get_post(post_id, user_id)
                        if post:
                            posts.append(post)
                    except ValueError:
                        continue
        
        return posts
    
    def update_post(self, post_id: int, content: str = None, category: str = None, 
                   image_url: str = None, user_id: str = None) -> bool:
        """投稿を更新"""
        # 公開・非公開両方のディレクトリをチェック
        for directory in [self.public_posts_dir, self.private_posts_dir]:
            filename = os.path.join(directory, f"{post_id}.json")
            
            if os.path.exists(filename):
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        post_data = json.load(f)
                    
                    # 非公開投稿のアクセス制御
                    if post_data.get('is_private'):
                        if not user_id or post_data.get('user_id') != user_id:
                            return False
                    
                    if content is not None:
                        if post_data.get('is_private'):
                            post_data['content'] = self._encrypt_content(content)
                        else:
                            post_data['content'] = content
                    
                    if category is not None:
                        post_data['category'] = category
                    
                    if image_url is not None:
                        post_data['image_url'] = image_url
                    
                    post_data['updated_at'] = datetime.now().isoformat()
                    
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(post_data, f, ensure_ascii=False, indent=2)
                    
                    # アクセスログを記録
                    self._log_access(user_id or "anonymous", post_id, "update", post_data.get('is_private', False))
                    
                    return True
                except (json.JSONDecodeError, FileNotFoundError):
                    continue
        
        return False
    
    def delete_post(self, post_id: int, user_id: str = None) -> bool:
        """投稿を削除"""
        # 公開・非公開両方のディレクトリをチェック
        for directory in [self.public_posts_dir, self.private_posts_dir]:
            filename = os.path.join(directory, f"{post_id}.json")
            
            if os.path.exists(filename):
                try:
                    # アクセス制御チェック
                    with open(filename, 'r', encoding='utf-8') as f:
                        post_data = json.load(f)
                    
                    if post_data.get('is_private'):
                        if not user_id or post_data.get('user_id') != user_id:
                            return False
                    
                    # 削除実行
                    os.remove(filename)
                    
                    # アクセスログを記録
                    self._log_access(user_id or "anonymous", post_id, "delete", post_data.get('is_private', False))
                    
                    return True
                except (json.JSONDecodeError, FileNotFoundError):
                    continue
        
        return False
    
    def search_posts(self, keyword: str = None, category: str = None, 
                     user_id: str = None) -> List[Dict[str, Any]]:
        """投稿を検索"""
        posts = self.get_all_posts(user_id)
        
        if keyword:
            keyword = keyword.lower()
            posts = [p for p in posts if keyword in p.get('content', '').lower()]
        
        if category:
            posts = [p for p in posts if p.get('category') == category]
        
        if user_id:
            posts = [p for p in posts if p.get('user_id') == user_id]
        
        return posts
