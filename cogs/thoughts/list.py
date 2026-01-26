import logging
import os
from typing import Dict, Any, List

import discord
from discord import app_commands, Interaction, Embed
from discord.ext import commands

# ファイルマネージャーをインポート
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from file_manager import FileManager

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
        self.file_manager = FileManager()
        logger.info("List cog が初期化されました")

    @app_commands.command(name='list', description='📋 投稿一覧を表示')
    async def list_posts(self, interaction: Interaction, 
                         category: str = None, 
                         limit: int = 10) -> None:
        """
        投稿一覧を表示するコマンド
        
        Args:
            interaction: Discordインタラクション
            category: フィルタリングするカテゴリー（任意）
            limit: 表示件数（デフォルト10件）
        """
        try:
            await interaction.response.defer(ephemeral=True)
            
            # 投稿を取得
            posts = self.file_manager.get_all_posts()
            
            if not posts:
                embed = Embed(
                    title="📋 投稿一覧",
                    description="投稿がありません。",
                    color=discord.Color.blue()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # カテゴリーでフィルタリング
            if category:
                posts = [post for post in posts if post.get('category') == category]
            
            if not posts:
                embed = Embed(
                    title=f"📋 カテゴリー「{category}」の投稿一覧",
                    description="指定されたカテゴリーの投稿がありません。",
                    color=discord.Color.blue()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # 作成日時でソート
            posts.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            # 件数制限
            posts = posts[:limit]
            
            # Embedを作成
            embed = Embed(
                title="📋 投稿一覧",
                description=f"全{len(posts)}件の投稿を表示",
                color=discord.Color.blue()
            )
            
            for post in posts:
                # 投稿者情報
                if post.get('is_anonymous'):
                    author = "匿名"
                else:
                    author = post.get('display_name') or "名無し"
                
                # 投稿内容（短く）
                content = post.get('content', '')
                content_preview = content[:100] + "..." if len(content) > 100 else content
                
                # 公開/非公開ステータス
                status = "🔒 非公開" if post.get('is_private') else "🌐 公開"
                
                # カテゴリー
                cat = post.get('category') or "未分類"
                
                # フィールドを追加
                embed.add_field(
                    name=f"ID: {post['id']} - {author} ({status})",
                    value=f"**カテゴリー:** {cat}\n**内容:** {content_preview}",
                    inline=False
                )
            
            embed.set_footer(text=f"最新{limit}件を表示")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"listコマンド実行中にエラーが発生しました: {e}", exc_info=True)
            error_embed = Embed(
                title="❌ エラーが発生しました",
                description="投稿一覧の取得中にエラーが発生しました。もう一度お試しください。",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)

    @app_commands.command(name='my_posts', description='📝 自分の投稿一覧を表示')
    async def my_posts(self, interaction: Interaction, limit: int = 10) -> None:
        """
        自分の投稿一覧を表示するコマンド
        
        Args:
            interaction: Discordインタラクション
            limit: 表示件数（デフォルト10件）
        """
        try:
            await interaction.response.defer(ephemeral=True)
            
            # ユーザーの投稿を取得
            posts = self.file_manager.search_posts(user_id=str(interaction.user.id))
            
            if not posts:
                embed = Embed(
                    title="📝 自分の投稿一覧",
                    description="あなたの投稿がありません。",
                    color=discord.Color.blue()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # 作成日時でソート
            posts.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            # 件数制限
            posts = posts[:limit]
            
            # Embedを作成
            embed = Embed(
                title="📝 自分の投稿一覧",
                description=f"あなたの投稿全{len(posts)}件を表示",
                color=discord.Color.blue()
            )
            
            for post in posts:
                # 投稿内容（短く）
                content = post.get('content', '')
                content_preview = content[:100] + "..." if len(content) > 100 else content
                
                # 公開/非公開ステータス
                status = "🔒 非公開" if post.get('is_private') else "🌐 公開"
                
                # カテゴリー
                cat = post.get('category') or "未分類"
                
                # フィールドを追加
                embed.add_field(
                    name=f"ID: {post['id']} ({status})",
                    value=f"**カテゴリー:** {cat}\n**内容:** {content_preview}",
                    inline=False
                )
            
            embed.set_footer(text=f"最新{limit}件を表示")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"my_postsコマンド実行中にエラーが発生しました: {e}", exc_info=True)
            error_embed = Embed(
                title="❌ エラーが発生しました",
                description="自分の投稿一覧の取得中にエラーが発生しました。もう一度お試しください。",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)

    @app_commands.command(name='categories', description='📁 カテゴリー一覧を表示')
    async def list_categories(self, interaction: Interaction) -> None:
        """
        カテゴリー一覧を表示するコマンド
        
        Args:
            interaction: Discordインタラクション
        """
        try:
            await interaction.response.defer(ephemeral=True)
            
            # 全投稿を取得
            posts = self.file_manager.get_all_posts()
            
            if not posts:
                embed = Embed(
                    title="📁 カテゴリー一覧",
                    description="投稿がありません。",
                    color=discord.Color.blue()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # カテゴリーを集計
            category_counts = {}
            for post in posts:
                cat = post.get('category') or "未分類"
                category_counts[cat] = category_counts.get(cat, 0) + 1
            
            if not category_counts:
                embed = Embed(
                    title="📁 カテゴリー一覧",
                    description="カテゴリーがありません。",
                    color=discord.Color.blue()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Embedを作成
            embed = Embed(
                title="📁 カテゴリー一覧",
                description=f"全{len(category_counts)}個のカテゴリー",
                color=discord.Color.blue()
            )
            
            # カテゴリーを投稿数でソート
            sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
            
            for category, count in sorted_categories:
                embed.add_field(
                    name=f"📁 {category}",
                    value=f"{count}件の投稿",
                    inline=True
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"categoriesコマンド実行中にエラーが発生しました: {e}", exc_info=True)
            error_embed = Embed(
                title="❌ エラーが発生しました",
                description="カテゴリー一覧の取得中にエラーが発生しました。もう一度お試しください。",
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
