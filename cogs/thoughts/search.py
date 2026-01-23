"""
Disgle検索機能 - 完全に動作するバージョン
Google風の検索インターフェースと完全な機能
"""

import logging
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime

import discord
from discord import app_commands, ui, Interaction, Embed
from discord.ext import commands

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
        import os
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'bot.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            if search_type == 'replies':
                # リプライ検索
                query = '''
                    SELECT r.id, r.content, r.created_at, r.display_name, r.user_id,
                           r.post_id, t.content as parent_content
                    FROM replies r
                    LEFT JOIN thoughts t ON r.post_id = t.id
                    WHERE 1=1
                '''
                params = []
                
                if keyword:
                    query += ' AND (r.content LIKE ? OR r.display_name LIKE ?)'
                    params.extend([f'%{keyword}%', f'%{keyword}%'])
                
                if user_id:
                    query += ' AND r.user_id = ?'
                    params.append(user_id)
                
                query += ' ORDER BY r.created_at DESC LIMIT ?'
                params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                return [
                    {
                        'id': row[0],
                        'content': row[1],
                        'created_at': row[2],
                        'display_name': row[3],
                        'user_id': row[4],
                        'post_id': row[5],
                        'parent_content': row[6] if row[6] else '元の投稿が見つかりません',
                        'type': 'reply'
                    }
                    for row in rows
                ]
            
            elif search_type == 'likes':
                # いいね検索
                query = '''
                    SELECT ar.target_id, ar.action_data, ar.created_at, t.content, t.display_name, t.user_id
                    FROM actions_user ar
                    LEFT JOIN thoughts t ON ar.target_id = t.id
                    WHERE ar.action_type = 'like'
                '''
                params = []
                
                if keyword:
                    query += ' AND (t.content LIKE ? OR t.display_name LIKE ?)'
                    params.extend([f'%{keyword}%', f'%{keyword}%'])
                
                if user_id:
                    query += ' AND ar.user_id = ?'
                    params.append(user_id)
                
                query += ' ORDER BY ar.created_at DESC LIMIT ?'
                params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                return [
                    {
                        'id': row[0],
                        'action_data': row[1],
                        'created_at': row[2],
                        'content': row[3] if row[3] else '投稿が見つかりません',
                        'display_name': row[4] if row[4] else '不明',
                        'user_id': row[5],
                        'type': 'like'
                    }
                    for row in rows
                ]
            
            else:
                # 通常の投稿検索
                query = '''
                    SELECT id, content, category, created_at, display_name, user_id,
                           is_anonymous, is_private, image_url
                    FROM thoughts
                    WHERE 1=1
                '''
                params = []
                
                # 検索条件を追加
                if keyword:
                    query += ' AND (content LIKE ? OR category LIKE ?)'
                    params.extend([f'%{keyword}%', f'%{keyword}%'])
                
                if category:
                    query += ' AND category = ?'
                    params.append(category)
                
                if user_id:
                    query += ' AND user_id = ?'
                    params.append(user_id)
                
                # 非公開投稿は自分のみ表示
                if current_user_id:
                    query += ' AND (is_private = 0 OR user_id = ?)'
                    params.append(current_user_id)
                else:
                    # ユーザーIDがない場合は公開投稿のみ
                    query += ' AND is_private = 0'
                
                query += ' ORDER BY created_at DESC LIMIT ?'
                params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                return [
                    {
                        'id': row[0],
                        'content': row[1],
                        'category': row[2],
                        'created_at': row[3],
                        'display_name': row[4],
                        'user_id': row[5],
                        'is_anonymous': bool(row[6]),
                        'is_private': bool(row[7]),
                        'image_url': row[8],
                        'type': 'post'
                    }
                    for row in rows
                ]
        
        except Exception as e:
            logger.error(f"投稿検索中にエラーが発生しました: {e}")
            return []
        
        finally:
            conn.close()
    
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
    async def search_command(self, interaction: Interaction) -> None:
        """Discord検索コマンド"""
        try:
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
        super().__init__(timeout=300)
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
            
            # ランダムな投稿を取得
            posts = self.search_cog._search_posts(limit=1, current_user_id=int(interaction.user.id))
            logger.info(f"検索結果: {len(posts)}件")
            
            if not posts:
                await interaction.followup.send(
                    "🎲 投稿が見つかりませんでした。\nまずは投稿を作成してみましょう！",
                    ephemeral=True
                )
                return
            
            post = posts[0]
            logger.info(f"選択された投稿: ID={post['id']}")
            
            # アクションを記録
            self._log_action(interaction.user.id, 'lucky', post['id'], {
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
    
    def _log_action(self, user_id: int, action_type: str, target_id: int, action_data: Dict[str, Any]) -> None:
        """アクションをデータベースに記録"""
        try:
            # 絶対パスでデータベースに接続
            import os
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'bot.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # テーブル存在確認
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='actions_user'")
            if cursor.fetchone():
                cursor.execute('''
                    INSERT INTO actions_user (user_id, action_type, target_id, action_data, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    action_type,
                    target_id,
                    str(action_data),
                    datetime.now().isoformat()
                ))
                conn.commit()
            
            conn.close()
            
        except Exception as e:
            logger.error(f"アクション記録中にエラーが発生しました: {e}")
    
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
                    # UTCをJSTに変換（+9時間）
                    jst_dt = dt + timedelta(hours=9)
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
        super().__init__(timeout=300)
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
        super().__init__(timeout=300)
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
            import os
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'bot.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, content, category, created_at, display_name, user_id,
                       is_anonymous, is_private, image_url
                FROM thoughts WHERE id = ?
            ''', (post_id,))
            post = cursor.fetchone()
            conn.close()
            
            if not post:
                await interaction.followup.send(
                    "📝 投稿が見つかりませんでした。",
                    ephemeral=True
                )
                return
            
            # 詳細Embedを作成
            embed = discord.Embed(
                title=f"📝 投稿詳細 (ID: {post[0]})",
                color=discord.Color.blue()
            )
            
            # 投稿者情報
            if post[6]:  # is_anonymous
                author_info = "匿名"
            else:
                author_info = post[4] or "名無し"
            
            embed.add_field(name="👤 投稿者", value=author_info, inline=True)
            
            # 投稿日時をフォーマット（JSTタイムゾーン）
            if post[3]:
                try:
                    # ISO形式からdatetimeオブジェクトに変換
                    from datetime import datetime, timedelta, timezone
                    if 'T' in post[3]:
                        dt = datetime.fromisoformat(post[3].replace('Z', '+00:00'))
                        # UTCをJSTに変換（+9時間）
                        jst_dt = dt + timedelta(hours=9)
                        formatted_date = jst_dt.strftime('%Y年%m月%d日 %H:%M')
                    else:
                        formatted_date = post[3][:10]  # フォールバック
                except:
                    formatted_date = post[3][:10]  # フォールバック
            else:
                formatted_date = "不明"
            
            embed.add_field(name="📅 投稿日時", value=formatted_date, inline=True)
            
            if post[2]:  # category
                embed.add_field(name="📁 カテゴリー", value=post[2], inline=True)
            
            if post[7]:  # is_private
                embed.add_field(name="🔒 公開設定", value="非公開", inline=True)
            else:
                embed.add_field(name="🔒 公開設定", value="公開", inline=True)
            
            # 投稿内容
            embed.add_field(
                name="📄 内容",
                value=f"```\n{post[1]}\n```",
                inline=False
            )
            
            # 画像
            if post[8]:  # image_url
                embed.set_image(url=post[8])
            
            embed.set_footer(text=f"ユーザーID: {post[5]}")
            
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
        super().__init__(timeout=300)
        self.post = post
        self.search_cog = search_cog
        
        # 詳細ボタンのみ
        detail_button = ui.Button(label="📝 詳細", style=discord.ButtonStyle.primary)
        detail_button.callback = self.show_detail
        self.add_item(detail_button)
    
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
    
    async def like_post(self, interaction: Interaction) -> None:
        """いいね処理"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # アクションを記録
            self.search_cog._log_action(interaction.user.id, 'like', self.post['id'], {
                'post_content': self.post['content'][:100],
                'post_user_id': self.post['user_id']
            })
            
            # チャンネル転送
            like_channel = discord.utils.get(interaction.guild.text_channels, name="いいねした投稿")
            
            if like_channel:
                await like_channel.send(
                    f"❤️ **いいねした投稿**\n\n"
                    f"> {self.post['content'][:200]}{'...' if len(self.post['content']) > 200 else ''}\n\n"
                    f"— {interaction.user.display_name}がいいね！"
                )
                
                await interaction.followup.send(
                    f"❤️ **いいねしました！**\n\n"
                    f"投稿にいいねしました。\n"
                    f"📢 「いいねした投稿」チャンネルに投稿されました！",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"❤️ **いいねしました！**\n\n"
                    f"投稿にいいねしました。\n"
                    f"※「いいねした投稿」チャンネルが見つかりません",
                    ephemeral=True
                )
            
        except Exception as e:
            logger.error(f"いいね処理中にエラーが発生しました: {e}")
            await interaction.followup.send(
                "エラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )
    
    async def reply_post(self, interaction: Interaction) -> None:
        """リプライ処理"""
        try:
            modal = ReplyModal(self.post, self.search_cog)
            await interaction.response.send_modal(modal)
        except Exception as e:
            logger.error(f"リプライ処理中にエラーが発生しました: {e}")
            await interaction.followup.send(
                "エラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )

class ReplyModal(ui.Modal, title="💬 リプライ"):
    """リプライ用モーダル"""
    
    def __init__(self, post: PostData, search_cog: Search):
        super().__init__(timeout=300)
        self.post = post
        self.search_cog = search_cog
        
        self.reply_input = ui.TextInput(
            label="💬 リプライ内容",
            placeholder="この投稿に返信します...",
            required=True,
            style=discord.TextStyle.paragraph,
            max_length=1000
        )
        self.add_item(self.reply_input)
    
    async def on_submit(self, interaction: Interaction) -> None:
        """リプライ投稿"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            reply_content = self.reply_input.value.strip()
            
            if not reply_content:
                await interaction.followup.send(
                    "リプライ内容を入力してください。",
                    ephemeral=True
                )
                return
            
            # アクションを記録
            self.search_cog._log_action(interaction.user.id, 'reply', self.post['id'], {
                'reply_content': reply_content[:100],
                'parent_id': self.post['id']
            })
            
            # リプライをデータベースに保存
            import os
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'bot.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO thoughts (user_id, content, category, is_private, parent_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                interaction.user.id,
                reply_content,
                'リプライ',
                0,  # 公開
                self.post['id'],  # 親投稿ID
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            # チャンネル転送
            reply_channel = discord.utils.get(interaction.guild.text_channels, name="リプライ")
            
            if reply_channel:
                await reply_channel.send(
                    f"💬 **転送されたリプライ**\n\n"
                    f"> {reply_content}\n\n"
                    f"— {interaction.user.display_name} (投稿ID: {self.post['id']}へのリプライ)"
                )
                
                await interaction.followup.send(
                    f"💬 **リプライを投稿しました！**\n\n"
                    f"投稿ID: {self.post['id']} に返信しました。\n"
                    f"📢 「リプライ」チャンネルに投稿されました！",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"💬 **リプライを投稿しました！**\n\n"
                    f"投稿ID: {self.post['id']} に返信しました。\n"
                    f"※「リプライ」チャンネルが見つかりません",
                    ephemeral=True
                )
            
        except Exception as e:
            logger.error(f"リプライ投稿中にエラーが発生しました: {e}")
            await interaction.followup.send(
                "エラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )

async def setup(bot: commands.Bot) -> None:
    """Cogをセットアップ"""
    await bot.add_cog(Search(bot))
    logger.info("Search cog がセットアップされました")
