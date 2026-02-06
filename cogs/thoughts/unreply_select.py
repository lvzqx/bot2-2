"""
unreply UIコンポーネント
"""

import discord
from discord import app_commands, ui, Interaction
from discord.ext import commands
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class UnreplySelectView(ui.View):
    """リプライ選択用ビュー（unreply）"""
    
    def __init__(self, items: List[Dict[str, Any]], cog):
        super().__init__(timeout=300.0)  # 5分でタイムアウト
        self.items = items
        self.cog = cog
        
        # リプライ選択メニューを作成
        options = []
        for item in items[:25]:  # Discordの制限で25件まで
            content_preview = item['content'][:50] + "..." if len(item['content']) > 50 else item['content']
            options.append(
                discord.SelectOption(
                    label=f"リプライ ID: {item['id']} (投稿ID: {item['post_id']})",
                    description=f"{content_preview} - {item.get('created_at', '')[:10]}",
                    value=f"reply_{item['id']}"
                )
            )
        
        self.select_menu = ui.Select(
            placeholder="削除するリプライを選択...",
            options=options,
            min_values=1,
            max_values=1
        )
        self.select_menu.callback = self.select_callback
        self.add_item(self.select_menu)
    
    async def select_callback(self, interaction: Interaction):
        """選択されたリプライを削除"""
        try:
            selected_value = self.select_menu.values[0]
            
            if selected_value.startswith("reply_"):
                reply_id = int(selected_value.split("_")[1])
                reply_data = next((item for item in self.items if item['id'] == reply_id), None)
                
                if reply_data:
                    # リプライ削除処理を実行
                    await self.cog.process_unreply(interaction, reply_data)
                else:
                    await interaction.response.send_message("リプライデータが見つかりません。", ephemeral=True)
            else:
                await interaction.response.send_message("無効な選択です。", ephemeral=True)
                
        except discord.InteractionTimedOut:
            logger.warning("リプライ削除選択がタイムアウトしました")
            await interaction.response.send_message("タイムアウトしました。もう一度お試しください。", ephemeral=True)
        except discord.Forbidden:
            logger.error("リプライ削除選択権限がありません")
            await interaction.response.send_message("権限がありません。", ephemeral=True)
        except discord.NotFound:
            logger.error("リプライ削除選択でデータが見つかりません")
            await interaction.response.send_message("データが見つかりません。", ephemeral=True)
        except Exception as e:
            logger.error(f"リプライ削除選択エラー: {e}")
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
