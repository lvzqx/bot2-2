# Default avatar for anonymous posts
DEFAULT_AVATAR = "https://cdn.discordapp.com/attachments/958663922901217280/1457097821315399822/08350cafa4fabb8a6a1be2d9f18f2d88.png"

import re
import os

def extract_channel_id(channel_input):
    """チャンネルIDまたはURLからIDを抽出する"""
    if isinstance(channel_input, str):
        # Discord URL形式からIDを抽出
        url_match = re.search(r'https://discord\.com/channels/(\d+)/(\d+)', channel_input)
        if url_match:
            return int(url_match.group(2))  # 最後の数字がチャンネルID
        
        # 数値のみの場合はそのまま返す
        if channel_input.isdigit():
            return int(channel_input)
    
    return channel_input

# Channel IDs
# 優先順位: 環境変数 → URL → デフォルト値
def get_channel_id(channel_type):
    """チャンネルURLを環境変数またはデフォルト値から取得する"""
    # 環境変数を優先
    env_var = os.getenv(f'DISCORD_{channel_type.upper()}_CHANNEL_ID')
    if env_var:
        return env_var
    
    # URL設定を次に優先
    url_env = os.getenv(f'DISCORD_{channel_type.upper()}_CHANNEL_URL')
    if url_env:
        return url_env
    
    # デフォルト値を使用
    return DEFAULT_CHANNELS.get(channel_type)

# デフォルトチャンネル設定（URL形式で保持）
DEFAULT_CHANNELS = {
    'public': 'https://discord.com/channels/1449421401609212088/1457611087561101332',  # 公開用チャンネル
    'private': 'https://discord.com/channels/1449421401609212088/1457611128225009666'  # 非公開用チャンネル
}

# 現在のチャンネル設定（URLをそのまま使用）
CHANNELS = {
    'public': DEFAULT_CHANNELS['public'],
    'private': DEFAULT_CHANNELS['private']
}
