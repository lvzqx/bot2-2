import logging
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any

import discord
from discord import app_commands, ui, Interaction, Embed
from discord.ext import commands

# ファイルマネージャーをインポート
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from file_manager import FileManager
from config import get_channel_id, DEFAULT_AVATAR

# ロガーの設定
logger = logging.getLogger(__name__)

class Post(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.file_manager = FileManager()
        logger.info("Post cog が初期化されました")

    class VisibilitySelect(ui.Select):
        def __init__(self):
            options = [
                discord.SelectOption(label='公開', value='public', description='誰でも見ることができます', emoji='👥'),
                discord.SelectOption(label='非公開', value='private', description='自分と管理者のみが削除できます', emoji='🔒')
            ]
            super().__init__(
                placeholder='公開設定を選択...',
                min_values=1,
                max_values=1,
                options=options
            )
            self.value = 'public'  # デフォルト値
            
        async def callback(self, interaction: discord.Interaction):
            self.value = self.values[0]
            await interaction.response.defer()
    
    class PostModal(ui.Modal, title='新規投稿'):
        def __init__(self, cog=None) -> None:
            super().__init__(timeout=None)  # 無制限に設定
            self.cog = cog
            self.is_public = True  # デフォルトは公開
            
            self.message = ui.TextInput(
                label='📝 投稿内容',
                placeholder='ここに投稿内容を入力...',
                required=True,
                style=discord.TextStyle.paragraph,
                max_length=2000
            )
            
            self.category = ui.TextInput(
                label='📁 カテゴリー',
                placeholder='カテゴリー（任意）',
                required=False,
                style=discord.TextStyle.short,
                max_length=50
            )
            
            self.image_url = ui.TextInput(
                label='🖼️ 画像URL',
                placeholder='画像URL（任意）',
                required=False,
                style=discord.TextStyle.short,
                max_length=500
            )
            
            self.visibility = self.VisibilitySelect()
            
            self.anonymous = ui.TextInput(
                label='👤 匿名設定',
                placeholder='匿名にする場合は「匿名」と入力',
                required=False,
                style=discord.TextStyle.short,
                max_length=10,
                default='表示'
            )
            self.add_item(self.message)
            self.add_item(self.category)
            self.add_item(self.image_url)
            self.add_item(self.visibility)
            self.add_item(self.anonymous)

        async def on_submit(self, interaction: Interaction) -> None:
            """投稿内容をデータベースに保存"""
            try:
                await interaction.response.defer(ephemeral=True)
            except discord.InteractionResponded:
                pass  # 既に応答済みの場合は無視
            
            # extract_channel_idをインポート
            from config import extract_channel_id
            
            try:
                # メッセージからデータを抽出
                message = self.message.value
                category = self.category.value if self.category.value else None
                image_url = self.image_url.value if self.image_url.value else None
                visibility_value = (self.visibility.value or "").strip().lower()
                if visibility_value in {"公開", "public"}:
                    is_public = True
                elif visibility_value in {"非公開", "private"}:
                    is_public = False
                else:
                    await interaction.followup.send(
                        "❌ 公開設定が無効です。「公開」または「非公開」を選択してください。",
                        ephemeral=True
                    )
                    return
                is_anonymous = self.anonymous.value.lower() == '匿名'
                
                # データベースに保存
                try:
                    # 最初のPost cogを取得
                    post_cog = self.cog if hasattr(self, 'cog') else None
                    if not post_cog:
                        # interaction.clientからPost cogを取得
                        post_cog = interaction.client.get_cog('Post')
                    
                    if not post_cog:
                        await interaction.followup.send(
                            "❌ エラーが発生しました。Post cogが見つかりません。",
                            ephemeral=True
                        )
                        return
                    
                    post_id = post_cog.file_manager.save_post(
                        user_id=str(interaction.user.id),
                        content=message,
                        category=category,
                        image_url=image_url,
                        is_anonymous=is_anonymous,
                        is_private=not is_public,
                        display_name=interaction.user.display_name
                    )
                except Exception as e:
                    logger.error(f"データベース保存中にエラー: {e}", exc_info=True)
                    await interaction.followup.send(
                        f"❌ 投稿の保存中にエラーが発生しました: {str(e)}",
                        ephemeral=True
                    )
                    return
                
                # 公開・非公開で処理を分ける
                if is_public:
                    # 公開チャンネルに投稿
                    channel_url = get_channel_id('public')
                    channel_id = extract_channel_id(channel_url)
                    channel = interaction.guild.get_channel(channel_id)
                    if not channel:
                        raise ValueError("公開チャンネルが見つかりません")
                    
                    # メッセージを作成
                    embed = discord.Embed(
                        description=message,
                        color=discord.Color.blue()
                    )
                    
                    # 投稿者情報を設定
                    if is_anonymous:
                        embed.set_author(name="匿名ユーザー", icon_url=DEFAULT_AVATAR)
                    else:
                        embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)
                    
                    # 画像URLがあれば設定
                    if image_url:
                        embed.set_image(url=image_url)

                    footer_parts = []
                    if category:
                        footer_parts.append(f"カテゴリー: {category}")
                    footer_parts.append(f"投稿ID: {post_id}")
                    # UIDは表示しない
                    embed.set_footer(text=" | ".join(footer_parts))
                    
                    # メッセージを送信
                    sent_message = await channel.send(embed=embed)
                else:
                    # 非公開チャンネルに投稿
                    private_channel_url = get_channel_id('private')
                    private_channel_id = extract_channel_id(private_channel_url)
                    private_channel = interaction.guild.get_channel(private_channel_id)
                    if not private_channel:
                        raise ValueError("非公開チャンネルが見つかりません")
                    
                    # 非公開投稿はユーザー専用のスレッドを作成
                    thread_prefix = f"非公開投稿 - {interaction.user.id}"
                    target_thread: Optional[discord.Thread] = None

                    # アクティブスレッドから検索
                    for t in private_channel.threads:
                        if t.name.startswith(thread_prefix):
                            target_thread = t
                            break

                    # アーカイブされたスレッドからも検索
                    if target_thread is None:
                        try:
                            async for t in private_channel.archived_threads(private=True, limit=50):
                                if t.name.startswith(thread_prefix):
                                    target_thread = t
                                    break
                        except Exception as e:
                            logger.warning(f"アーカイブスレッドの検索中にエラー: {e}")

                    if target_thread is not None:
                        thread = target_thread
                        try:
                            if thread.archived:
                                await thread.edit(archived=False, locked=False)
                        except Exception as e:
                            logger.warning(f"スレッドの復元中にエラー: {e}")
                    else:
                        # 新しく作成
                        thread_name = f"{thread_prefix} ({interaction.user.name})"
                        try:
                            thread = await private_channel.create_thread(
                                name=thread_name[:100],
                                type=discord.ChannelType.private_thread,
                                reason=f"非公開投稿用スレッド作成 - {interaction.user.id}",
                                invitable=False
                            )
                        except discord.Forbidden:
                            await interaction.followup.send(
                                "❌ 非公開スレッドを作成する権限がありません。管理者に連絡してください。",
                                ephemeral=True
                            )
                            return
                        except discord.HTTPException as e:
                            logger.error(f"スレッド作成中にエラー: {e}", exc_info=True)
                            await interaction.followup.send(
                                "❌ スレッドの作成中にエラーが発生しました。",
                                ephemeral=True
                            )
                            return
                    
                    await thread.add_user(interaction.user)

                    # 非公開投稿用ロールを作成
                    private_role = discord.utils.get(interaction.guild.roles, name="非公開")
                    if not private_role:
                        private_role = await interaction.guild.create_role(
                            name="非公開",
                            reason="非公開投稿用ロール作成"
                        )

                    # 投稿者にロールを付与
                    member = interaction.guild.get_member(interaction.user.id)
                    if member and private_role not in member.roles:
                        await member.add_roles(private_role, reason="非公開投稿権限付与")

                    # 非公開投稿用ロールをスレッドに追加
                    for role_member in private_role.members:
                        try:
                            await thread.add_user(role_member)
                        except discord.HTTPException:
                            pass
                    
                    embed = discord.Embed(
                        description=message,
                        color=discord.Color.dark_grey()
                    )
                    
                    if is_anonymous:
                        embed.set_author(name="匿名ユーザー", icon_url=DEFAULT_AVATAR)
                    else:
                        embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)
                    
                    if image_url:
                        embed.set_image(url=image_url)

                    footer_parts = []
                    if category:
                        footer_parts.append(f"カテゴリー: {category}")
                    footer_parts.append(f"投稿ID: {post_id}")
                    # UIDは表示しない
                    embed.set_footer(text=" | ".join(footer_parts))
                    
                    sent_message = await thread.send(embed=embed)
                    
                    # DBにはスレッドIDを保存
                    channel = thread
                
                # メッセージ参照をファイルに保存
                message_ref_data = {
                    "post_id": post_id,
                    "message_id": sent_message.id,
                    "channel_id": channel.id,
                    "user_id": interaction.user.id,
                    "created_at": datetime.now().isoformat()
                }
                
                message_ref_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                               'data', f'message_ref_{post_id}.json')
                with open(message_ref_file, 'w', encoding='utf-8') as f:
                    import json
                    json.dump(message_ref_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"メッセージ参照を保存しました: 投稿ID={post_id}")
                
                # 公開投稿の場合のみ完了メッセージを送信（非公開は既に送信済み）
                if is_public:
                    embed = discord.Embed(
                        title="✅ 投稿が完了しました！",
                        description=f"[メッセージにジャンプ]({sent_message.jump_url})",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="ID", value=f"`{post_id}`", inline=True)
                    if category:
                        embed.add_field(name="カテゴリ", value=f"`{category}`", inline=True)
                    embed.add_field(name="表示名", value=f"`{'匿名' if is_anonymous else '表示'}`", inline=True)
                    
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    
                    # GitHubに保存する処理
                    from .github_sync import sync_to_github
                    await sync_to_github("new post", interaction.user.name, post_id)
                
            except Exception as e:
                logger.error(f"フォーム送信中にエラーが発生しました: {e}", exc_info=True)
                error_message = f"❌ 投稿中にエラーが発生しました。\n詳細: {str(e)}\n\nエラータイプ: {type(e).__name__}"
                try:
                    await interaction.followup.send(
                        error_message,
                        ephemeral=True
                    )
                except discord.InteractionResponded:
                    pass  # 既に応答済みの場合は無視

    @app_commands.command(name="post", description="📝 投稿を作成")
    @app_commands.guild_only()
    async def post(self, interaction: discord.Interaction) -> None:
        """投稿を作成するコマンド"""
        try:
            logger.info(f"post コマンドが実行されました: ユーザー: {interaction.user}")
            
            # メッセージのインスタンスを作成
            try:
                modal = self.PostModal(cog=self)
                logger.info("モーダルのインスタンス作成に成功しました")
            except Exception as e:
                logger.error(f"モーダルのインスタンス作成中にエラー: {e}", exc_info=True)
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "❌ エラーが発生しました。もう一度お試しください。",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        "❌ エラーが発生しました。もう一度お試しください。",
                        ephemeral=True
                    )
                return
            
            # モーダルを送信
            try:
                await interaction.response.send_modal(modal)
                logger.info("モーダルの送信に成功しました")
            except discord.InteractionResponded:
                logger.warning("既に応答済みのため、モーダルを送信できません")
                await interaction.followup.send(
                    "❌ 既に応答済みです。もう一度お試しください。",
                    ephemeral=True
                )
            except Exception as e:
                logger.error(f"モーダルの送信中にエラー: {e}", exc_info=True)
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "❌ エラーが発生しました。もう一度お試しください。",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        "❌ エラーが発生しました。もう一度お試しください。",
                        ephemeral=True
                    )
        
        except Exception as e:
            logger.error(f"postコマンド実行中に予期しないエラーが発生しました: {e}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"予期しないエラーが発生しました: {str(e)}",
                    ephemeral=True
                )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Post(bot))
    logger.info("Post cog が読み込まれました")
