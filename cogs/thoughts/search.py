"""
Disgle検索機能 - 完全に動作するバージョン
Google風の検索インターフェースと完全な機能
"""

import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

import discord
from discord import app_commands, ui, Interaction, Embed
from discord.ext import commands

# マネージャーをインポート
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from managers.post_manager import PostManager
from managers.reply_manager import ReplyManager
from managers.like_manager import LikeManager
from managers.message_ref_manager import MessageRefManager
from managers.action_manager import ActionManager
from config import get_channel_id, extract_channel_id

# ロガー設定
logger = logging.getLogger(__name__)

# 定数
MAX_SEARCH_RESULTS = 50
ITEMS_PER_PAGE = 3

# 型定義
PostData = Dict[str, Any]

class Search(commands.Cog):
    """投稿検索機能を提供するCog"""
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.post_manager = PostManager()
        self.reply_manager = ReplyManager()
        self.like_manager = LikeManager()
        self.message_ref_manager = MessageRefManager()
        self.action_manager = ActionManager()
        logger.info("Search cog が初期化されました")
    
    def _search_posts(
        self,
        keyword: Optional[str] = None,
        category: Optional[str] = None,
        user_id: Optional[int] = None,
        current_user_id: Optional[int] = None,
        limit: int = 10,
        search_type: str = 'posts'
    ) -> List[Dict[str, Any]]:
        """投稿を検索（リプライといいねも対応）"""
        
        try:
            if search_type == 'posts':
                # 投稿検索
                posts = self.post_manager.search_posts(
                    keyword=keyword,
                    category=category,
                    user_id=str(user_id) if user_id else None
                )
                
                # 非公開投稿のフィルタリング
                if current_user_id:
                    posts = [p for p in posts if not p.get('is_private') or p.get('user_id') == str(current_user_id)]
                else:
                    posts = [p for p in posts if not p.get('is_private')]
                
                return posts[:limit]
            
            elif search_type == 'replies':
                # リプライ検索 - 全投稿のリプライを検索
                all_posts = self.post_manager.get_all_posts()
                all_replies = []
                
                for post in all_posts:
                    replies = self.reply_manager.get_replies(post['id'])
                    
                    for reply in replies:
                        # キーワードフィルタリング
                        if keyword:
                            keyword_lower = keyword.lower()
                            if (keyword_lower not in reply.get('content', '').lower() and 
                                keyword_lower not in reply.get('display_name', '').lower()):
                                continue
                        
                        # ユーザーIDフィルタリング
                        if user_id and reply.get('user_id') != str(user_id):
                            continue
                        
                        # 親投稿情報を追加
                        reply['parent_content'] = post.get('content', '元の投稿が見つかりません')
                        all_replies.append(reply)
                
                # 作成日時でソート
                all_replies.sort(key=lambda x: x.get('created_at', ''), reverse=True)
                return all_replies[:limit]
            
            elif search_type == 'likes':
                # いいね検索 - 全投稿のいいねを検索
                all_posts = self.post_manager.get_all_posts()
                all_likes = []
                
                for post in all_posts:
                    likes = self.like_manager.get_likes(post['id'])
                    
                    for like in likes:
                        # キーワードフィルタリング
                        if keyword:
                            keyword_lower = keyword.lower()
                            if keyword_lower not in like.get('display_name', '').lower():
                                continue
                        
                        # ユーザーIDフィルタリング
                        if user_id and like.get('user_id') != str(user_id):
                            continue
                        
                        # 親投稿情報を追加
                        like['parent_content'] = post.get('content', '元の投稿が見つかりません')
                        all_likes.append(like)
                
                # 作成日時でソート
                all_likes.sort(key=lambda x: x.get('created_at', ''), reverse=True)
                return all_likes[:limit]
            
            return []
            
        except Exception as e:
            logger.error(f"検索中にエラーが発生しました: {e}")
            return []
    
    def _create_post_embed(self, post: PostData, title: str) -> Embed:
        """投稿Embedを作成"""
        embed = Embed(
            title=title,
            color=discord.Color.blue()
        )
        
        # 投稿者情報
        if post['is_anonymous']:
            author = "匿名"
        else:
            author = post['display_name'] or "名無し"
        
        embed.add_field(name="👤 投稿者", value=author, inline=True)
        embed.add_field(name="📁 カテゴリー", value=post['category'] or '未分類', inline=True)
        
        # 投稿日時をフォーマット（JSTタイムゾーン）
        if post['created_at']:
            try:
                # ISO形式からdatetimeオブジェクトに変換
                from datetime import datetime, timedelta, timezone
                if 'T' in post['created_at']:
                    dt = datetime.fromisoformat(post['created_at'].replace('Z', '+00:00'))
                    # タイムゾーン情報がある場合はJSTに変換、ない場合はJSTとして扱う
                    if dt.tzinfo is None:
                        # タイムゾーン情報がない場合はJSTとして扱う
                        jst_dt = dt.replace(tzinfo=timezone(timedelta(hours=9)))
                    else:
                        # UTCからJSTに変換
                        jst_dt = dt.astimezone(timezone(timedelta(hours=9)))
                    created_at_str = jst_dt.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    created_at_str = post['created_at']
                embed.add_field(name="📅 投稿日時", value=created_at_str, inline=True)
            except Exception as e:
                logger.warning(f"日時フォーマットエラー: {e}")
                embed.add_field(name="📅 投稿日時", value=post['created_at'] or '不明', inline=True)
        
        # 投稿内容
        content = post['content']
        embed.description = content
        
        # 投稿ID
        embed.set_footer(text=f"投稿ID: {post['id']}")
        
        return embed
    
    async def _create_embeds(self, interaction: Interaction, posts: List[PostData], keyword: str, search_type: str = 'posts') -> List[Embed]:
        """検索結果のEmbedを作成します"""
        embeds = []
        
        type_names = {
            'posts': '投稿',
            'replies': 'リプライ',
            'likes': 'いいね'
        }
        
        type_icons = {
            'posts': '📝',
            'replies': '💬',
            'likes': '❤️'
        }
        
        for i in range(0, len(posts), ITEMS_PER_PAGE):
            embed = Embed(
                title=f"🔍 Disgle検索結果",
                description=f"キーワード: 「{keyword}」 - {type_names[search_type]}検索",
                color=discord.Color.blue()
            )
            
            page_posts = posts[i:i + ITEMS_PER_PAGE]
            for j, post in enumerate(page_posts):
                if search_type == 'posts':
                    # 投稿検索
                    author = "匿名" if post['is_anonymous'] else (post['display_name'] or "名無し")
                    content = post['content'][:100]
                    if len(post['content']) > 100:
                        content += "..."
                    
                    embed.add_field(
                        name=f"{type_icons[search_type]} {author}の投稿",
                        value=f"カテゴリー: {post['category'] or '未分類'}\n{content}",
                        inline=False
                    )
                
                elif search_type == 'replies':
                    # リプライ検索
                    author = post['display_name'] or "名無し"
                    content = post['content'][:100]
                    if len(post['content']) > 100:
                        content += "..."
                    
                    parent_content = post['parent_content'][:50]
                    if len(post['parent_content']) > 50:
                        parent_content += "..."
                    
                    embed.add_field(
                        name=f"{type_icons[search_type]} {author}のリプライ",
                        value=f"元の投稿: {parent_content}\nリプライ: {content}",
                        inline=False
                    )
                
                elif search_type == 'likes':
                    # いいね検索
                    author = post['display_name'] or "不明"
                    content = post['content'][:100]
                    if len(post['content']) > 100:
                        content += "..."
                    
                    embed.add_field(
                        name=f"{type_icons[search_type]} {author}がいいねした投稿",
                        value=f"内容: {content}",
                        inline=False
                    )
            
            embed.set_footer(text=f"ページ {i//ITEMS_PER_PAGE + 1}/{(len(posts)-1)//ITEMS_PER_PAGE + 1}")
            embeds.append(embed)
        
        return embeds
    
    @app_commands.command(name="search", description="🔍 投稿を検索")
    @app_commands.guild_only()
    async def search_command(self, interaction: Interaction) -> None:
        """Discord検索コマンド - 検索チャンネル限定"""
        try:
            # 検索チャンネルかチェック
            search_channel_url = get_channel_id('search')
            search_channel_id = extract_channel_id(search_channel_url)
            
            if interaction.channel.id != search_channel_id:
                await interaction.response.send_message(
                    "❌ **このコマンドは検索チャンネルでのみ使用できます**\n\n"
                    f"検索チャンネル: <#{search_channel_id}>",
                    ephemeral=True
                )
                return
            # DiscordロゴEmbed
            embed = Embed(
                title=None,
                description="",
                color=discord.Color.blue()
            )
            
            # Discordロゴ
            embed.set_thumbnail(
                url="https://cdn.discordapp.com/attachments/958663922901217280/1463461574156222538/2026-01-21_18-13-35.png?ex=6971ea4d&is=697098cd&hm=b786c68476db53c8dcebcb1eb5882ad9fc5f4c5f5899bd0d7cb5d7cc9ba6a420&"
            )
            
            embed.add_field(
                name="🔍 Discord検索",
                value="下のボタンから検索を開始できます",
                inline=False
            )
            
            embed.set_footer(text="Discord - あなたの思考を整理する")
            
            view = SearchView(self)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"searchコマンド実行中にエラーが発生しました: {e}")
            await interaction.response.send_message(
                "エラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )

class SearchView(ui.View):
    """Google風の検索ビュー"""
    
    def __init__(self, search_cog: Search):
        try:
            super().__init__(timeout=None)
            self.search_cog = search_cog
            
            # 検索ボタン
            search_button = ui.Button(
                label="Disgle検索",
                style=discord.ButtonStyle.primary,
                emoji="🔍"
            )
            search_button.callback = self.open_search_modal
            self.add_item(search_button)
            
            # ラッキーボタン
            lucky_button = ui.Button(
                label="I'm Feeling Lucky",
                style=discord.ButtonStyle.secondary,
                emoji="🎲"
            )
            lucky_button.callback = self.feeling_lucky
            self.add_item(lucky_button)
            
        except RuntimeError as e:
            # イベントループがない場合のエラーハンドリング
            logger.warning(f"SearchView初期化エラー（非同期環境外）: {e}")
            self.search_cog = search_cog
            self.initialized = False
        except Exception as e:
            logger.error(f"SearchView初期化エラー: {e}")
            raise
    
    async def open_search_modal(self, interaction: Interaction) -> None:
        """検索モーダルを開く"""
        try:
            logger.info(f"検索モーダル開始: user={interaction.user.id}")
            modal = SearchModal(self.search_cog)
            await interaction.response.send_modal(modal)
            logger.info("検索モーダル送信完了")
        except Exception as e:
            logger.error(f"検索モーダル開始中にエラーが発生しました: {e}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "エラーが発生しました。もう一度お試しください。",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "エラーが発生しました。もう一度お試しください。",
                    ephemeral=True
                )
    
    async def feeling_lucky(self, interaction: Interaction) -> None:
        """I'm Feeling Lucky - ランダムな投稿を表示"""
        try:
            logger.info(f"I'm Feeling Lucky開始: user={interaction.user.id}")
            await interaction.response.defer(ephemeral=True)
            
            # Viewが初期化されていない場合のチェック
            if hasattr(self, 'initialized') and not self.initialized:
                await interaction.followup.send(
                    "🎲 検索機能が初期化されていません。もう一度お試しください。",
                    ephemeral=True
                )
                return
            
            # ランダムな投稿を取得
            posts = self.search_cog._search_posts(current_user_id=int(interaction.user.id))
            logger.info(f"検索結果: {len(posts)}件")
            
            if not posts:
                await interaction.followup.send(
                    "🎲 投稿が見つかりませんでした。\nまずは投稿を作成してみましょう！",
                    ephemeral=True
                )
                return
            
            # ランダムに1件選択
            import random
            post = random.choice(posts)
            logger.info(f"ランダム選択された投稿: ID={post['id']}")
            
            # アクションを記録
            self.search_cog.action_manager.save_action_record('lucky', str(interaction.user.id), str(post['id']), {
                'post_content': post['content'][:100],
                'category': post['category']
            })
            
            # 投稿Embedを作成
            embed = self._create_post_embed(post, "🎲 I'm Feeling Lucky!")
            
            # アクションボタン
            view = PostActionView(post, self)  # selfを渡す
            
            await interaction.followup.send(
                embed=embed,
                view=view,
                ephemeral=True
            )
            logger.info("I'm Feeling Lucky完了")
            
        except Exception as e:
            logger.error(f"I'm Feeling Lucky実行中にエラーが発生しました: {e}", exc_info=True)
            await interaction.followup.send(
                "🎲 エラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )
    
    def _create_post_embed(self, post: PostData, title: str) -> Embed:
        """投稿Embedを作成"""
        embed = Embed(
            title=title,
            color=discord.Color.blue()
        )
        
        # 投稿者情報
        if post['is_anonymous']:
            author = "匿名"
        else:
            author = post['display_name'] or "名無し"
        
        embed.add_field(name="👤 投稿者", value=author, inline=True)
        embed.add_field(name="📁 カテゴリー", value=post['category'] or '未分類', inline=True)
        
        # 投稿日時をフォーマット（JSTタイムゾーン）
        if post['created_at']:
            try:
                # ISO形式からdatetimeオブジェクトに変換
                from datetime import datetime, timedelta, timezone
                if 'T' in post['created_at']:
                    dt = datetime.fromisoformat(post['created_at'].replace('Z', '+00:00'))
                    # タイムゾーン情報がある場合はJSTに変換、ない場合はJSTとして扱う
                    if dt.tzinfo is None:
                        # タイムゾーン情報がない場合はJSTとして扱う
                        jst_dt = dt.replace(tzinfo=timezone(timedelta(hours=9)))
                    else:
                        # UTCからJSTに変換
                        jst_dt = dt.astimezone(timezone(timedelta(hours=9)))
                    formatted_date = jst_dt.strftime('%Y年%m月%d日 %H:%M')
                else:
                    formatted_date = post['created_at'][:10]  # フォールバック
            except:
                formatted_date = post['created_at'][:10]  # フォールバック
        else:
            formatted_date = "不明"
        
        embed.add_field(name="📅 投稿日時", value=formatted_date, inline=True)
        
        # 投稿内容
        embed.add_field(
            name="📄 内容",
            value=f"```\n{post['content']}\n```",
            inline=False
        )
        
        # 画像
        if post['image_url']:
            embed.set_image(url=post['image_url'])
        
        embed.set_footer(text=f"投稿ID: {post['id']}")
        return embed

class SearchModal(ui.Modal, title="Disgle検索"):
    """Disgle検索用モーダル"""
    
    def __init__(self, search_cog: Search):
        super().__init__(timeout=None)
        self.search_cog = search_cog
        
        self.search_input = ui.TextInput(
            label="🔍 検索キーワード",
            placeholder="検索したいキーワードを入力...",
            required=True,
            style=discord.TextStyle.paragraph,
            max_length=200
        )
        
        self.search_type_input = ui.TextInput(
            label="📝 検索タイプ",
            placeholder="posts（投稿）, replies（リプライ）, likes（いいね）",
            required=False,
            style=discord.TextStyle.short,
            max_length=10,
            default="posts"
        )
        
        self.add_item(self.search_input)
        self.add_item(self.search_type_input)
    
    async def on_submit(self, interaction: Interaction) -> None:
        """検索実行"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            keyword = self.search_input.value.strip()
            search_type = self.search_type_input.value.strip().lower()
            
            if not keyword:
                await interaction.followup.send(
                    "検索キーワードを入力してください。",
                    ephemeral=True
                )
                return
            
            # 検索タイプのバリデーション
            valid_types = ['posts', 'replies', 'likes']
            if search_type not in valid_types:
                search_type = 'posts'
            
            # 検索実行
            posts = self.search_cog._search_posts(
                keyword=keyword, 
                current_user_id=int(interaction.user.id),
                search_type=search_type
            )
            
            if not posts:
                type_names = {
                    'posts': '投稿',
                    'replies': 'リプライ',
                    'likes': 'いいね'
                }
                await interaction.followup.send(
                    f"「{keyword}」に一致する{type_names[search_type]}は見つかりませんでした。",
                    ephemeral=True
                )
                return
            
            # 結果を表示
            embeds = await self.search_cog._create_embeds(interaction, posts, keyword, search_type)
            view = PaginationView(embeds, posts, self.search_cog)
            
            type_names = {
                'posts': '投稿',
                'replies': 'リプライ',
                'likes': 'いいね'
            }
            
            await interaction.followup.send(
                f"「{keyword}」の{type_names[search_type]}検索結果 ({len(posts)}件)",
                embed=embeds[0],
                view=view,
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"検索実行中にエラーが発生しました: {e}")
            await interaction.followup.send(
                "エラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )

class PaginationView(ui.View):
    """ページネーションビュー"""
    
    def __init__(self, embeds: List[Embed], posts: List[PostData], search_cog: Search):
        super().__init__(timeout=None)
        self.embeds = embeds
        self.posts = posts
        self.search_cog = search_cog
        self.current_page = 0
        
        self.update_buttons()
    
    async def button_callback(self, interaction: Interaction) -> None:
        """ボタンの共通コールバック処理"""
        custom_id = interaction.data["custom_id"]
        
        # ページネーションボタン
        if custom_id in ['first', 'prev', 'next', 'last']:
            if custom_id == 'first':
                self.current_page = 0
            elif custom_id == 'prev':
                self.current_page = max(0, self.current_page - 1)
            elif custom_id == 'next':
                self.current_page = min(len(self.embeds) - 1, self.current_page + 1)
            elif custom_id == 'last':
                self.current_page = len(self.embeds) - 1
            
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
        # 詳細ボタンのみ
        elif custom_id.startswith("detail_"):
            post_id = int(custom_id.split("_")[1])
            await self.show_post_detail(interaction, post_id)
    
    def update_buttons(self) -> None:
        """ボタンの状態を更新"""
        self.clear_items()
        
        # ページネーションボタン
        if self.current_page > 0:
            prev_button = ui.Button(label="◀", style=discord.ButtonStyle.secondary)
            prev_button.callback = self.button_callback
            self.add_item(prev_button)
        
        page_label = ui.Button(
            label=f"{self.current_page + 1}/{len(self.embeds)}",
            style=discord.ButtonStyle.secondary,
            disabled=True
        )
        self.add_item(page_label)
        
        if self.current_page < len(self.embeds) - 1:
            next_button = ui.Button(label="▶", style=discord.ButtonStyle.secondary)
            next_button.callback = self.button_callback
            self.add_item(next_button)
        
        # アクションボタン（現在のページの投稿に対して）
        if self.posts and self.current_page < len(self.posts):
            # 現在のページの投稿を取得（1ページに複数投稿の場合）
            start_idx = self.current_page * 3  # ITEMS_PER_PAGE = 3
            end_idx = min(start_idx + 3, len(self.posts))
            page_posts = self.posts[start_idx:end_idx]
            
            # 最初の投稿にのみ詳細ボタンを表示
            if page_posts:
                current_post = page_posts[0]  # 最初の投稿
                
                # 詳細ボタンのみ
                detail_button = ui.Button(
                    label="📝 詳細",
                    style=discord.ButtonStyle.primary,
                    custom_id=f"detail_{current_post['id']}"
                )
                detail_button.callback = self.button_callback
                self.add_item(detail_button)
    
    async def show_post_detail(self, interaction: Interaction, post_id: int) -> None:
        """投稿詳細を表示"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # 投稿情報を取得
            post = self.search_cog.post_manager.get_post(post_id)
            
            if not post:
                await interaction.followup.send(
                    "📝 投稿が見つかりませんでした。",
                    ephemeral=True
                )
                return
            
            # 詳細Embedを作成
            embed = discord.Embed(
                title=f"📝 投稿詳細 (ID: {post['id']})",
                color=discord.Color.blue()
            )
            
            # 投稿者情報
            if post.get('is_anonymous'):
                author_info = "匿名"
            else:
                author_info = post.get('display_name') or "名無し"
            
            embed.add_field(name="👤 投稿者", value=author_info, inline=True)
            
            # 投稿日時をフォーマット（JSTタイムゾーン）
            if post.get('created_at'):
                try:
                    # ISO形式からdatetimeオブジェクトに変換
                    from datetime import datetime, timedelta, timezone
                    if 'T' in post['created_at']:
                        dt = datetime.fromisoformat(post['created_at'].replace('Z', '+00:00'))
                        # タイムゾーン情報がある場合はJSTに変換、ない場合はJSTとして扱う
                        if dt.tzinfo is None:
                            # タイムゾーン情報がない場合はJSTとして扱う
                            jst_dt = dt.replace(tzinfo=timezone(timedelta(hours=9)))
                        else:
                            # UTCからJSTに変換
                            jst_dt = dt.astimezone(timezone(timedelta(hours=9)))
                        formatted_date = jst_dt.strftime('%Y年%m月%d日 %H:%M')
                    else:
                        formatted_date = post['created_at'][:10]  # フォールバック
                except:
                    formatted_date = post['created_at'][:10]  # フォールバック
            else:
                formatted_date = "不明"
            
            embed.add_field(name="📅 投稿日時", value=formatted_date, inline=True)
            embed.add_field(name="📁 カテゴリー", value=post.get('category') or '未分類', inline=True)
            
            # 投稿内容
            embed.add_field(
                name="📄 内容",
                value=f"```\n{post['content']}\n```",
                inline=False
            )
            
            # 画像
            if post.get('image_url'):
                embed.set_image(url=post['image_url'])
            
            embed.set_footer(text=f"投稿ID: {post['id']}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"詳細表示中にエラーが発生しました: {e}")
            await interaction.followup.send(
                "エラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )

class PostActionView(ui.View):
    """投稿アクションボタンビュー"""
    
    def __init__(self, post: PostData, search_cog: 'Search'):
        try:
            super().__init__(timeout=None)
            self.post = post
            self.search_cog = search_cog
            
            # 詳細ボタンのみ
            detail_button = ui.Button(label="📝 詳細", style=discord.ButtonStyle.primary)
            detail_button.callback = self.show_detail
            self.add_item(detail_button)
            
        except RuntimeError as e:
            # イベントループがない場合のエラーハンドリング
            logger.warning(f"PostActionView初期化エラー（非同期環境外）: {e}")
            self.post = post
            self.search_cog = search_cog
            self.initialized = False
        except Exception as e:
            logger.error(f"PostActionView初期化エラー: {e}")
            raise
    
    async def show_detail(self, interaction: Interaction) -> None:
        """投稿詳細を表示"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            embed = self.search_cog._create_post_embed(self.post, f"📝 投稿詳細 (ID: {self.post['id']})")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"詳細表示中にエラーが発生しました: {e}")
            await interaction.followup.send(
                "エラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )

async def setup(bot: commands.Bot) -> None:
    """Cogをセットアップ"""
    await bot.add_cog(Search(bot))
    logger.info("Search cog がセットアップされました")
