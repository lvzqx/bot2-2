"""
リプライ編集UIコンポーネント
"""

import discord
from discord import app_commands, ui, Interaction
from discord.ext import commands
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ReplyEditSelectView(ui.View):
    """リプライ選択用ビュー"""
    
    def __init__(self, items: List[Dict[str, Any]], cog):
        super().__init__(timeout=None)
        self.items = items
        self.cog = cog
        
        # リプライ選択メニューを作成
        options = []
        for item in items[:25]:  # Discordの制限で25件まで
            content_preview = item['content'][:50] + "..." if len(item['content']) > 50 else item['content']
            options.append(
                discord.SelectOption(
                    label=f"リプライ ID: {item['id']}",
                    description=f"{content_preview} (投稿ID: {item['post_id']})",
                    value=f"reply_{item['id']}"
                )
            )
        
        self.select_menu = ui.Select(
            placeholder="編集するリプライを選択...",
            options=options,
            min_values=1,
            max_values=1
        )
        self.select_menu.callback = self.select_callback
        self.add_item(self.select_menu)
    
    async def select_callback(self, interaction: Interaction):
        """選択されたリプライを編集"""
        try:
            selected_value = self.select_menu.values[0]
            
            if selected_value.startswith("reply_"):
                reply_id = int(selected_value.split("_")[1])
                reply_data = next((item for item in self.items if item['id'] == reply_id), None)
                
                if reply_data:
                    modal = ReplyEditModal(reply_data, self.cog)
                    await interaction.response.send_modal(modal)
                else:
                    await interaction.response.send_message("リプライデータが見つかりません。", ephemeral=True)
            else:
                await interaction.response.send_message("無効な選択です。", ephemeral=True)
                
        except Exception as e:
            logger.error(f"リプライ選択エラー: {e}")
            await interaction.response.send_message("エラーが発生しました。もう一度お試しください。", ephemeral=True)


class ReplyEditModal(ui.Modal, title="リプライを編集"):
    """リプライ編集用モーダル"""
    
    def __init__(self, reply_data: Dict[str, Any], cog: 'EditReply'):
        super().__init__(timeout=None)
        self.cog = cog
        self.reply_data = reply_data
        
        # 現在の内容をプレフィルド
        self.message = ui.TextInput(
            label='💬 リプライ内容',
            placeholder='リプライ内容を入力...',
            required=True,
            style=discord.TextStyle.paragraph,
            max_length=2000,
            default=reply_data.get('content', '')
        )
        
        self.add_item(self.message)
    
    async def on_submit(self, interaction: Interaction):
        """編集内容を送信"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # フォームデータを取得
            message = self.message.value.strip()
            
            # 入力検証
            if len(message) < 1:
                await interaction.followup.send("リプライ内容を入力してください。", ephemeral=True)
                return
            
            # リプライを更新
            success = await self.cog.update_reply(
                interaction=interaction,
                reply_id=self.reply_data['id'],
                message=message
            )
            
            if success:
                await interaction.followup.send(
                    f"✅ リプライを更新しました！\n\n"
                    f"リプライID: {self.reply_data['id']}",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ リプライの更新に失敗しました。",
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"リプライ編集送信エラー: {e}")
            await interaction.followup.send(
                "❌ エラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )
