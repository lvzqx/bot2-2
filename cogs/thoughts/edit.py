import discord
from discord import app_commands, ui, Interaction
from discord.ext import commands
import sqlite3
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class Edit(commands.Cog):
    """投稿を編集するコマンド"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db_path = 'bot.db'
    
    def _get_db_connection(self):
        """データベース接続を取得"""
        return sqlite3.connect(self.db_path)
    
    @app_commands.command(name='edit', description='📝 投稿を編集')
    async def edit(self, interaction: discord.Interaction):
        """編集する投稿を選択するコマンド"""
        try:
            # 即座に応答を開始
            await interaction.response.defer(ephemeral=True)
            
            # データベース接続を確立
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # ユーザーの投稿を取得
            cursor.execute('''
                SELECT t.id, t.content, t.is_private, t.is_anonymous, t.category, t.image_url, 
                       m.message_id, m.channel_id
                FROM thoughts t
                LEFT JOIN message_references m ON t.id = m.post_id
                WHERE t.user_id = ?
                ORDER BY t.id DESC
                LIMIT 25
            ''', (str(interaction.user.id),))
            
            items = cursor.fetchall()
            conn.close()
            
            if not items:
                await interaction.followup.send("編集可能な投稿が見つかりませんでした。", ephemeral=True)
                return
            
            # 結果を辞書のリストに変換
            items_list = []
            for item in items:
                items_list.append({
                    'type': 'post',
                    'id': item[0],
                    'content': item[1],
                    'is_private': bool(item[2]),
                    'is_anonymous': bool(item[3]),
                    'category': item[4],
                    'image_url': item[5],
                    'message_id': item[6],
                    'channel_id': item[7]
                })
            
            # 選択ビューを作成
            view = EditSelectView(items_list, self)
            
            await interaction.followup.send("編集する投稿を選択してください:", view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"編集コマンド実行中にエラーが発生しました: {e}", exc_info=True)
            await interaction.followup.send("エラーが発生しました。もう一度お試しください。", ephemeral=True)


class EditSelectView(ui.View):
    """編集する投稿を選択するビュー"""
    
    def __init__(self, items: List[Dict[str, Any]], cog: 'Edit'):
        super().__init__(timeout=300)
        self.items = items
        self.cog = cog
        
        # 投稿選択メニューを作成
        options = []
        for item in items[:25]:  # Discordの制限に合わせて25件まで
            content_preview = item['content'][:50] + "..." if len(item['content']) > 50 else item['content']
            options.append(
                discord.SelectOption(
                    label=f"投稿 ID: {item['id']}",
                    description=f"{content_preview} ({'公開' if not item['is_private'] else '非公開'})",
                    value=f"post_{item['id']}"
                )
            )
        
        self.select_menu = ui.Select(
            placeholder="編集する投稿を選択...",
            options=options,
            min_values=1,
            max_values=1
        )
        self.select_menu.callback = self.select_callback
        self.add_item(self.select_menu)
    
    async def select_callback(self, interaction: Interaction):
        """選択された投稿を編集"""
        try:
            selected_value = self.select_menu.values[0]
            
            if selected_value.startswith('post_'):
                # 投稿編集
                post_id = int(selected_value.split('_')[1])
                item = next((item for item in self.items if item['type'] == 'post' and item['id'] == post_id), None)
                if item:
                    modal = PostEditModal(item, self.cog)
                    await interaction.response.send_modal(modal)
            
        except Exception as e:
            logger.error(f"選択コールバック中にエラーが発生しました: {e}")
            await interaction.response.send_message("エラーが発生しました。もう一度お試しください。", ephemeral=True)


class PostEditModal(ui.Modal, title="投稿を編集"):
    """投稿編集用モーダル"""
    
    def __init__(self, post_data: Dict[str, Any], cog: 'Edit'):
        super().__init__(timeout=300)
        self.post_data = post_data
        self.cog = cog
        
        self.content_input = ui.TextInput(
            label='📝 投稿内容',
            placeholder='編集後の投稿内容を入力...',
            required=True,
            style=discord.TextStyle.paragraph,
            max_length=2000,
            default=post_data['content'][:1000]  # Discordの制限に合わせる
        )
        
        self.category_input = ui.TextInput(
            label='📂 カテゴリー',
            placeholder='カテゴリーを入力...',
            required=False,
            style=discord.TextStyle.short,
            max_length=50,
            default=post_data.get('category', '')
        )
        
        self.image_url_input = ui.TextInput(
            label='🖼️ 画像URL（任意）',
            placeholder='画像のURLを入力（https://...）',
            required=False,
            style=discord.TextStyle.short,
            max_length=500,
            default=post_data.get('image_url', '')
        )
        
        self.add_item(self.content_input)
        self.add_item(self.category_input)
        self.add_item(self.image_url_input)
    
    async def on_submit(self, interaction: Interaction):
        """投稿編集を実行"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            new_content = self.content_input.value.strip()
            new_category = self.category_input.value.strip() or None
            new_image_url = self.image_url_input.value.strip() or None
            
            # データベースを更新
            conn = self.cog._get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE thoughts 
                SET content = ?, category = ?, image_url = ?, updated_at = datetime('now')
                WHERE id = ? AND user_id = ?
            ''', (new_content, new_category, new_image_url, self.post_data['id'], str(interaction.user.id)))
            
            conn.commit()
            conn.close()
            
            # Discordメッセージも更新
            if self.post_data.get('message_id') and self.post_data.get('channel_id'):
                try:
                    channel = interaction.guild.get_channel(int(self.post_data['channel_id']))
                    if channel:
                        message = await channel.fetch_message(int(self.post_data['message_id']))
                        if message.embeds:
                            embed = message.embeds[0]
                            # post.pyと同じ構造に更新
                            embed.description = new_content
                            if new_image_url:
                                embed.set_image(url=new_image_url)
                            else:
                                # 画像URLが削除された場合は画像をクリア
                                embed.set_image(url=None)
                            
                            # Footerを更新（post.pyと同じ形式）
                            footer_parts = []
                            if new_category:
                                footer_parts.append(f"カテゴリ: {new_category}")
                            footer_parts.append(f"投稿ID: {self.post_data['id']}")
                            embed.set_footer(text=" | ".join(footer_parts))
                            
                            await message.edit(embed=embed)
                except Exception as e:
                    logger.error(f"Discordメッセージ更新中にエラー: {e}")
            
            await interaction.followup.send(
                f"✅ **投稿を編集しました！**\n\n"
                f"投稿ID: {self.post_data['id']} を更新しました。",
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"投稿編集中にエラーが発生しました: {e}")
            await interaction.followup.send("編集中にエラーが発生しました。もう一度お試しください。", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    """Cogをセットアップ"""
    try:
        await bot.add_cog(Edit(bot))
        logger.info("Edit cog がセットアップされました")
    except Exception as e:
        logger.error(f"Edit cog のセットアップ中にエラーが発生しました: {e}", exc_info=True)
        raise
