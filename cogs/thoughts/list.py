import logging
import os
from typing import Dict, Any, List

import discord
from discord import app_commands, Interaction, Embed
from discord.ext import commands

# マネージャーをインポート
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from managers.post_manager import PostManager

# ロガーの設定
logger = logging.getLogger(__name__)

# 型定義
PostData = Dict[str, Any]  # 投稿データの型

class List(commands.Cog):
    """投稿一覧を表示するためのCog"""
    
    def __init__(self, bot: commands.Bot) -> None:
        """
        List cogの初期化
        
        Args:
            bot: Discord Bot インスタンス
        """
        self.bot: commands.Bot = bot
        self.post_manager = PostManager()
        logger.info("List cog が初期化されました")

    @app_commands.command(name='list', description='📋 あなたの投稿一覧を表示')
    async def list_posts(self, interaction: Interaction) -> None:
        """
        自分の投稿一覧を表示するコマンド
        
        Args:
            interaction: Discordインタラクション
        """
        try:
            await interaction.response.defer(ephemeral=True)
            
            # 自分の投稿を取得
            my_posts = self.post_manager.search_posts(user_id=str(interaction.user.id))
            
            if not my_posts:
                embed = Embed(
                    title="📋 あなたの投稿一覧",
                    description="投稿がありません。",
                    color=discord.Color.blue()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # 作成日時でソート
            my_posts.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            # Embedを作成
            embed = Embed(
                title="📋 あなたの投稿一覧",
                description=f"全{len(my_posts)}件の投稿",
                color=discord.Color.blue()
            )
            
            for post in my_posts:
                # 投稿内容（文字数制限なし）
                content = post.get('content', '')
                
                # 公開/非公開ステータス
                status = "🔒 非公開" if post.get('is_private') else "🌐 公開"
                
                # フィールドを追加
                embed.add_field(
                    name=f"ID: {post['id']} ({status})",
                    value=content,
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"listコマンド実行中にエラーが発生しました: {e}", exc_info=True)
            error_embed = Embed(
                title="❌ エラーが発生しました",
                description="投稿一覧の取得中にエラーが発生しました。もう一度お試しください。",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    """Cogをセットアップ"""
    try:
        await bot.add_cog(List(bot))
        logger.info("List cog がセットアップされました")
    except Exception as e:
        logger.error(f"List cog セットアップ中にエラーが発生しました: {e}", exc_info=True)
        raise
