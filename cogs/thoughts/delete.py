import logging
import os
from typing import Dict, Any, List

import discord
from discord import app_commands, ui, Interaction, Embed
from discord.ext import commands

# マネージャーをインポート
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from managers.post_manager import PostManager
from managers.message_ref_manager import MessageRefManager

# ユーティリティをインポート
from .delete_utils import delete_discord_message, cleanup_message_ref

logger = logging.getLogger(__name__)

class Delete(commands.Cog):
    """投稿削除用Cog"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.post_manager = PostManager()
        self.message_ref_manager = MessageRefManager()
    
    @app_commands.command(name="delete", description="🗑️ 投稿を削除")
    async def delete_post(self, interaction: Interaction) -> None:
        """削除する投稿を選択するコマンド"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # ユーザーの投稿を取得
            posts = self.post_manager.search_posts(user_id=str(interaction.user.id))
            
            if not posts:
                await interaction.followup.send(
                    "❌ **投稿が見つかりません**\n\n"
                    "削除できる投稿がありません。",
                    ephemeral=True
                )
                return
            
            # 作成日時でソート
            posts.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            posts = posts[:25]  # 最大25件
            
            # 選択ビューを表示
            view = DeleteSelectView(posts, self)
            embed = discord.Embed(
                title="🗑️ 削除する投稿を選択",
                description="削除したい投稿を選択してください",
                color=discord.Color.red()
            )
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"deleteコマンド実行中にエラーが発生しました: {e}")
            await interaction.followup.send(
                "❌ **エラーが発生しました**\n\n"
                "投稿の取得に失敗しました。",
                ephemeral=True
            )

class DeleteSelectView(ui.View):
    """削除する投稿を選択するビュー"""
    
    def __init__(self, posts: List[Dict[str, Any]], cog: 'Delete'):
        super().__init__(timeout=None)
        self.posts = posts
        self.cog = cog
        
        # 選択肢を作成
        options = []
        for post in posts:
            content = post.get('content', '')[:50] + "..." if len(post.get('content', '')) > 50 else post.get('content', '')
            created_at = post.get('created_at', '不明')
            post_id = post.get('id', '不明')
            
            options.append(
                discord.SelectOption(
                    label=f"投稿ID: {post_id}",
                    description=f"{content} ({created_at})",
                    value=str(post_id)
                )
            )
        
        self.delete_select = ui.Select(
            placeholder="削除する投稿を選択してください",
            options=options
        )
        
        self.delete_select.callback = self.delete_select_callback
        self.add_item(self.delete_select)
    
    async def delete_select_callback(self, interaction: Interaction):
        """投稿選択時のコールバック"""
        selected_post_id = int(self.delete_select.values[0])
        
        # 選択された投稿データを取得
        post_data = next((post for post in self.posts if post['id'] == selected_post_id), None)
        
        if post_data:
            modal = DeleteConfirmModal(post_data, self.cog)
            await interaction.response.send_modal(modal)

class DeleteConfirmModal(ui.Modal, title="🗑️ 投稿削除確認"):
    """投稿削除確認用モーダル"""
    
    def __init__(self, post_data: Dict[str, Any], cog: 'Delete'):
        super().__init__(timeout=None)
        self.cog = cog
        self.post_data = post_data
        
        content = post_data.get('content', '')
        content_preview = content[:100] + "..." if len(content) > 100 else content
        
        self.confirm_input = ui.TextInput(
            label="🗑️ 削除確認",
            placeholder=f"本当に削除する場合は「delete」と入力",
            required=True,
            style=discord.TextStyle.short,
            max_length=10
        )
        
        self.add_item(self.confirm_input)
        
        # 確認メッセージを追加
        self.confirm_message = f"""
        **削除する投稿内容:**
        {content_preview}
        
        **投稿ID:** {post_data['id']}
        **作成日時:** {post_data.get('created_at', '不明')}
        """
    
    async def on_submit(self, interaction: Interaction):
        """投稿削除を実行"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # 削除確認
            if self.confirm_input.value.strip().lower() != "delete":
                await interaction.followup.send(
                    "❌ **削除がキャンセルされました**\n\n"
                    "確認キーワードが正しくありません。「delete」と入力してください。",
                    ephemeral=True
                )
                return
            
            post_id = self.post_data['id']
            
            # 投稿の存在と権限を確認
            post = self.cog.post_manager.get_post(post_id, str(interaction.user.id))
            if not post:
                logger.error(f"投稿の削除に失敗しました: 投稿ID={post_id}, 権限なしまたは存在しない")
                await interaction.followup.send(
                    "❌ **投稿が見つかりません**\n\n"
                    "投稿が存在しないか、削除権限がありません。",
                    ephemeral=True
                )
                return
            
            # 投稿ファイルを削除
            success = self.cog.post_manager.delete_post(post_id, str(interaction.user.id))
            if not success:
                logger.error(f"投稿の削除に失敗しました: 投稿ID={post_id}")
                await interaction.followup.send(
                    "❌ **投稿が見つかりません**\n\n"
                    "投稿ファイルが存在しません。",
                    ephemeral=True
                )
                return
            
            logger.info(f"投稿を削除しました: 投稿ID={post_id}")
            
            # まず成功メッセージを送信（速度改善）
            await interaction.followup.send(
                f"✅ **投稿を削除しました**\n\n"
                f"投稿ID: {post_id} と関連データを削除しました。",
                ephemeral=True
            )
            
            # 関連データ削除をバックグラウンドで実行
            
            # Discordメッセージを削除
            message_ref_data = self.cog.message_ref_manager.get_message_ref(post_id)
            if message_ref_data:
                message_id = message_ref_data.get('message_id')
                channel_id = message_ref_data.get('channel_id')
                
                await delete_discord_message(interaction, message_id, channel_id, self.cog.message_ref_manager)
            else:
                logger.warning(f"⚠️ メッセージ参照が見つかりません: 投稿ID={post_id}")
            
            # メッセージ参照を削除
            cleanup_message_ref(post_id, self.cog.message_ref_manager)
            
            # GitHubに保存する処理
            from utils.github_sync import sync_to_github
            await sync_to_github("delete post", interaction.user.name, post_id)
            
        except Exception as e:
            logger.error(f"投稿削除中にエラーが発生しました: {e}")
            await interaction.followup.send(
                "❌ **エラーが発生しました**\n\n"
                "投稿の削除に失敗しました。",
                ephemeral=True
            )
