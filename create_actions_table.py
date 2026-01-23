import sqlite3
from datetime import datetime

def create_actions_table():
    """actions-userテーブルを作成"""
    conn = sqlite3.connect('thoughts.db')
    cursor = conn.cursor()
    
    # actions-userテーブルを作成
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS actions_user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action_type TEXT NOT NULL,  -- 'like', 'reply', 'search', 'lucky'
            target_id INTEGER,           -- 投稿ID（like, replyの場合）
            action_data TEXT,             -- アクション詳細（JSON形式）
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES thoughts (user_id)
        )
    ''')
    
    # インデックスを作成
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_actions_user_user_id 
        ON actions_user (user_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_actions_user_action_type 
        ON actions_user (action_type)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_actions_user_created_at 
        ON actions_user (created_at)
    ''')
    
    conn.commit()
    conn.close()
    print("actions-userテーブルを作成しました！")

if __name__ == "__main__":
    create_actions_table()
