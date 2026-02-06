"""
いいねUIコンポーネント
"""

import discord
from discord import app_commands, ui, Interaction
from discord.ext import commands
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class LikeSelectView(ui.View):
    """投稿選択用ビュー（いいね）"""
    
    def __init__(self, items: List[Dict[str, Any]], cog):
        super().__init__(timeout=300.0)  # 5分でタイムアウト
        self.items = items
        self.cog = cog
        
        # 投稿選択メニューを作成
        options = []
        for item in items[:25]:  # Discordの制限で25件まで
            content_preview = item['content'][:50] + "..." if len(item['content']) > 50 else item['content']
            options.append(
                discord.SelectOption(
                    label=f"投稿 ID: {item['id']}",
                    description=f"{content_preview} ({'公開' if not item['is_private'] else '非公開'})",
                    value=f"post_{item['id']}"
                )
            )
        
        self.select_menu = ui.Select(
            placeholder="いいねする投稿を選択...",
            options=options,
            min_values=1,
            max_values=1
        )
        self.select_menu.callback = self.select_callback
        self.add_item(self.select_menu)
    
    async def select_callback(self, interaction: Interaction):
        """選択された投稿をいいね"""
        try:
            selected_value = self.select_menu.values[0]
            
            if selected_value.startswith("post_"):
                post_id = int(selected_value.split("_")[1])
                post_data = next((item for item in self.items if item['id'] == post_id), None)
                
                if post_data:
                    # いいね処理を実行
                    await self.cog.process_like(interaction, post_data)
                else:
                    await interaction.response.send_message("投稿データが見つかりません。", ephemeral=True)
            else:
                await interaction.response.send_message("無効な選択です。", ephemeral=True)
                
        except discord.InteractionTimedOut:
            logger.warning("いいね選択がタイムアウトしました")
            await interaction.response.send_message("タイムアウトしました。もう一度お試しください。", ephemeral=True)
        except discord.Forbidden:
            logger.error("いいね選択権限がありません")
            await interaction.response.send_message("権限がありません。", ephemeral=True)
        except discord.NotFound:
            logger.error("いいね選択でデータが見つかりません")
            await interaction.response.send_message("データが見つかりません。", ephemeral=True)
        except Exception as e:
            logger.error(f"いいね選択エラー: {e}")
            await interaction.response.send_message("エラーが発生しました。もう一度お試しください。", ephemeral=True)

    async def on_timeout(self):
        """タイムアウト時の処理"""
        # 選択メニューを無効化
        self.select_menu.disabled = True
        # メッセージを更新（可能であれば）
        try:
            # タイムアウトメッセージを送信
            embed = discord.Embed(
                title="⏰ タイムアウト",
                description="選択時間が5分を超えたため、操作をキャンセルしました。",
                color=discord.Color.orange()
            )
            await self.message.edit(embed=embed, view=self)
        except Exception as e:
            logger.warning(f"タイムアウト時のメッセージ更新に失敗: {e}")
