import logging
import os
import json
from typing import Dict, Any
from datetime import datetime

import discord
from discord import app_commands, ui, Interaction, Embed
from discord.ext import commands

# ファイルマネージャーをインポート
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from file_manager import FileManager
from config import get_channel_id, extract_channel_id

logger = logging.getLogger(__name__)

class LikeModal(ui.Modal, title="❤️ いいねする投稿"):
    """いいねする投稿IDを入力するモーダル"""
    
    def __init__(self):
        super().__init__(timeout=300)
        self.file_manager = FileManager()
        
        self.post_id_input = ui.TextInput(
            label="📝 投稿ID",
            placeholder="いいねする投稿のIDを入力...",
            required=True,
            style=discord.TextStyle.short,
            max_length=10
        )
        self.add_item(self.post_id_input)
    
    async def on_submit(self, interaction: Interaction) -> None:
        """いいね実行"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            post_id = int(self.post_id_input.value.strip())
            
            # 投稿情報を取得
            post = self.file_manager.get_post(post_id)
            
            if not post:
                await interaction.followup.send(
                    "投稿が見つかりませんでした。\n\n"
                    f"投稿ID: {post_id}\n"
                    "※正しい投稿IDを入力してください。",
                    ephemeral=True
                )
                return
            
            post_content = post.get('content', '')
            post_user_id = post.get('user_id', '')
            
            # いいねを保存
            like_id = self.file_manager.save_like(
                post_id=post_id,
                user_id=str(interaction.user.id),
                display_name=interaction.user.display_name
            )
            
            # いいね用チャンネルに投稿
            likes_channel_url = get_channel_id('likes')
            likes_channel_id = extract_channel_id(likes_channel_url)
            likes_channel = interaction.guild.get_channel(likes_channel_id)
            
            if likes_channel:
                # 元の投稿メッセージを取得して転送
                message_ref_file = os.path.join("data", f"message_ref_{post_id}.json")
                if os.path.exists(message_ref_file):
                    try:
                        with open(message_ref_file, 'r', encoding='utf-8') as f:
                            message_ref_data = json.load(f)
                            message_id = message_ref_data.get('message_id')
                            channel_id = message_ref_data.get('channel_id')
                        
                        if message_id and channel_id:
                            # 元の投稿メッセージを取得
                            original_channel = interaction.guild.get_channel(int(channel_id))
                            if original_channel:
                                original_message = await original_channel.fetch_message(int(message_id))
                                
                                # 元の投稿を転送
                                await original_message.forward(likes_channel)
                                
                                # いいねしたことを投稿
                                like_message = await likes_channel.send(f"❤️ いいね：{interaction.user.display_name}")
                                
                                # いいねファイルにメッセージIDを保存
                                self.file_manager.update_like_message_id(like_id, str(like_message.id), str(likes_channel.id))
                            else:
                                # チャンネルが見つからない場合は従来通り
                                like_embed = discord.Embed(
                                    title=f"❤️ いいね：{interaction.user.display_name}",
                                    description=f"**投稿ID: {post_id}**\n\n{post_content}",
                                    color=discord.Color.red()
                                )
                                like_embed.add_field(name="投稿者", value=post.get('display_name', '名無し'), inline=True)
                                like_embed.set_footer(text=f"いいねID: {like_id}")
                                like_message = await likes_channel.send(embed=like_embed)
                                self.file_manager.update_like_message_id(like_id, str(like_message.id), str(likes_channel.id))
                        else:
                            # メッセージ参照がない場合は従来通り
                            like_embed = discord.Embed(
                                title=f"❤️ いいね：{interaction.user.display_name}",
                                description=f"**投稿ID: {post_id}**\n\n{post_content}",
                                color=discord.Color.red()
                            )
                            like_embed.add_field(name="投稿者", value=post.get('display_name', '名無し'), inline=True)
                            like_embed.set_footer(text=f"いいねID: {like_id}")
                            like_message = await likes_channel.send(embed=like_embed)
                            self.file_manager.update_like_message_id(like_id, str(like_message.id), str(likes_channel.id))
                    except (json.JSONDecodeError, FileNotFoundError, discord.NotFound, discord.Forbidden):
                        # エラーの場合は従来通り
                        like_embed = discord.Embed(
                            title=f"❤️ いいね：{interaction.user.display_name}",
                            description=f"**投稿ID: {post_id}**\n\n{post_content}",
                            color=discord.Color.red()
                        )
                        like_embed.add_field(name="投稿者", value=post.get('display_name', '名無し'), inline=True)
                        like_embed.set_footer(text=f"いいねID: {like_id}")
                        like_message = await likes_channel.send(embed=like_embed)
                        self.file_manager.update_like_message_id(like_id, str(like_message.id), str(likes_channel.id))
                else:
                    # メッセージ参照ファイルがない場合は従来通り
                    like_embed = discord.Embed(
                        title=f"❤️ いいね：{interaction.user.display_name}",
                        description=f"**投稿ID: {post_id}**\n\n{post_content}",
                        color=discord.Color.red()
                    )
                    like_embed.add_field(name="投稿者", value=post.get('display_name', '名無し'), inline=True)
                    like_embed.set_footer(text=f"いいねID: {like_id}")
                    like_message = await likes_channel.send(embed=like_embed)
                    self.file_manager.update_like_message_id(like_id, str(like_message.id), str(likes_channel.id))
            
            # 専用チャンネルへの転送のみで完了
            await interaction.followup.send(
                f"❤️ **いいねしました！**\n\n"
                f"いいねチャンネルに投稿を転送しました。",
                ephemeral=True
            )
            
            # GitHubに保存する処理
            from .github_sync import sync_to_github
            await sync_to_github("like", interaction.user.name, post_id)
            
        except ValueError:
            await interaction.followup.send(
                "❤️ 投稿IDは数字で入力してください。",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"いいね処理中にエラーが発生しました: {e}")
            await interaction.followup.send(
                "❤️ エラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )
    
    async def _log_action(self, user_id: int, action_type: str, target_id: int, action_data: Dict[str, Any]) -> None:
        """アクションをファイルに記録"""
        try:
            import json
            action_record = {
                "user_id": user_id,
                "action_type": action_type,
                "target_id": target_id,
                "action_data": action_data,
                "created_at": datetime.now().isoformat()
            }
            
            # アクションファイルを作成
            action_filename = os.path.join("data", f"action_{action_type}_{user_id}_{target_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            os.makedirs("data", exist_ok=True)
            
            with open(action_filename, 'w', encoding='utf-8') as f:
                json.dump(action_record, f, ensure_ascii=False, indent=2)
            
            logger.info(f"アクション記録完了: {action_type} by user {user_id} on target {target_id}")
            
        except Exception as e:
            logger.error(f"アクション記録中にエラーが発生しました: {e}", exc_info=True)


class ReplyModal(ui.Modal, title="💬 リプライする投稿"):
    """リプライする投稿IDと内容を入力するモーダル"""
    
    def __init__(self):
        super().__init__(timeout=300)
        self.file_manager = FileManager()
        
        self.post_id_input = ui.TextInput(
            label="📝 投稿ID",
            placeholder="リプライする投稿のIDを入力...",
            required=True,
            style=discord.TextStyle.short,
            max_length=10
        )
        
        self.reply_input = ui.TextInput(
            label="💬 リプライ内容",
            placeholder="リプライの内容を入力...",
            required=True,
            style=discord.TextStyle.paragraph
        )
        
        self.add_item(self.post_id_input)
        self.add_item(self.reply_input)
    
    async def on_submit(self, interaction: Interaction) -> None:
        """リプライ実行"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            post_id = int(self.post_id_input.value.strip())
            reply_content = self.reply_input.value.strip()
            
            # 親投稿の存在確認
            parent_post = self.file_manager.get_post(post_id)
            
            if not parent_post:
                await interaction.followup.send(
                    "💬 指定された投稿が見つかりませんでした。",
                    ephemeral=True
                )
                return
            
            # アクションを記録
            await self._log_action(interaction.user.id, 'reply', post_id, {
                'reply_content': reply_content[:100],
                'parent_id': post_id
            })
            
            # リプライをファイルに保存
            reply_id = self.file_manager.save_reply(
                post_id=post_id,
                user_id=str(interaction.user.id),
                content=reply_content,
                display_name=interaction.user.display_name
            )
            
            # リプライ用チャンネルに投稿
            replies_channel_url = get_channel_id('replies')
            replies_channel_id = extract_channel_id(replies_channel_url)
            replies_channel = interaction.guild.get_channel(replies_channel_id)
            
            if replies_channel:
                # 元の投稿メッセージを取得して転送
                message_ref_file = os.path.join("data", f"message_ref_{post_id}.json")
                if os.path.exists(message_ref_file):
                    try:
                        with open(message_ref_file, 'r', encoding='utf-8') as f:
                            message_ref_data = json.load(f)
                            message_id = message_ref_data.get('message_id')
                            channel_id = message_ref_data.get('channel_id')
                        
                        if message_id and channel_id:
                            # 元の投稿メッセージを取得
                            original_channel = interaction.guild.get_channel(int(channel_id))
                            if original_channel:
                                original_message = await original_channel.fetch_message(int(message_id))
                                
                                # 元の投稿を転送
                                await original_message.forward(replies_channel)
                                
                                # リプライを投稿
                                reply_embed = discord.Embed(
                                    title=f"💬 リプライ：{interaction.user.display_name}",
                                    description=reply_content,
                                    color=discord.Color.green()
                                )
                                reply_embed.set_footer(text=f"リプライID: {reply_id}")
                                reply_message = await replies_channel.send(embed=reply_embed)
                                
                                # リプライファイルにメッセージIDを保存
                                self.file_manager.update_reply_message_id(reply_id, str(reply_message.id), str(replies_channel.id))
                            else:
                                # チャンネルが見つからない場合は従来通り
                                reply_embed = discord.Embed(
                                    title=f"💬 {interaction.user.display_name}がリプライしました",
                                    description=f"**投稿ID: {post_id}へのリプライ**\n\n{reply_content}",
                                    color=discord.Color.green()
                                )
                                reply_embed.add_field(name="投稿者", value=parent_post.get('display_name', '名無し'), inline=True)
                                reply_embed.set_footer(text=f"リプライID: {reply_id}")
                                reply_message = await replies_channel.send(embed=reply_embed)
                                self.file_manager.update_reply_message_id(reply_id, str(reply_message.id), str(replies_channel.id))
                        else:
                            # メッセージ参照がない場合は従来通り
                            reply_embed = discord.Embed(
                                title=f"💬 {interaction.user.display_name}がリプライしました",
                                description=f"**投稿ID: {post_id}へのリプライ**\n\n{reply_content}",
                                color=discord.Color.green()
                            )
                            reply_embed.add_field(name="投稿者", value=parent_post.get('display_name', '名無し'), inline=True)
                            reply_embed.set_footer(text=f"リプライID: {reply_id}")
                            reply_message = await replies_channel.send(embed=reply_embed)
                            self.file_manager.update_reply_message_id(reply_id, str(reply_message.id), str(replies_channel.id))
                    except (json.JSONDecodeError, FileNotFoundError, discord.NotFound, discord.Forbidden):
                        # エラーの場合は従来通り
                        reply_embed = discord.Embed(
                            title=f"💬 {interaction.user.display_name}がリプライしました",
                            description=f"**投稿ID: {post_id}へのリプライ**\n\n{reply_content}",
                            color=discord.Color.green()
                        )
                        reply_embed.add_field(name="投稿者", value=parent_post.get('display_name', '名無し'), inline=True)
                        reply_embed.set_footer(text=f"リプライID: {reply_id}")
                        reply_message = await replies_channel.send(embed=reply_embed)
                        self.file_manager.update_reply_message_id(reply_id, str(reply_message.id), str(replies_channel.id))
                else:
                    # メッセージ参照ファイルがない場合は従来通り
                    reply_embed = discord.Embed(
                        title=f"💬 {interaction.user.display_name}がリプライしました",
                        description=f"**投稿ID: {post_id}へのリプライ**\n\n{reply_content}",
                        color=discord.Color.green()
                    )
                    reply_embed.add_field(name="投稿者", value=parent_post.get('display_name', '名無し'), inline=True)
                    reply_embed.set_footer(text=f"リプライID: {reply_id}")
                    reply_message = await replies_channel.send(embed=reply_embed)
                    self.file_manager.update_reply_message_id(reply_id, str(reply_message.id), str(replies_channel.id))
            
            # 専用チャンネルへの転送のみで完了
            await interaction.followup.send(
                f"💬 **リプライしました！**\n\n"
                f"リプライチャンネルに投稿を転送しました。",
                ephemeral=True
            )
            
        except ValueError:
            await interaction.followup.send(
                "💬 投稿IDは数字で入力してください。",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"リプライ処理中にエラーが発生しました: {e}", exc_info=True)
            await interaction.followup.send(
                "💬 エラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )
    
    async def _log_action(self, user_id: int, action_type: str, target_id: int, action_data: Dict[str, Any]) -> None:
        """アクションをファイルに記録"""
        try:
            import json
            action_record = {
                "user_id": user_id,
                "action_type": action_type,
                "target_id": target_id,
                "action_data": action_data,
                "created_at": datetime.now().isoformat()
            }
            
            # アクションファイルを作成
            action_filename = os.path.join("data", f"action_{action_type}_{user_id}_{target_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            os.makedirs("data", exist_ok=True)
            
            with open(action_filename, 'w', encoding='utf-8') as f:
                json.dump(action_record, f, ensure_ascii=False, indent=2)
            
            logger.info(f"アクション記録完了: {action_type} by user {user_id} on target {target_id}")
            
        except Exception as e:
            logger.error(f"アクション記録中にエラーが発生しました: {e}", exc_info=True)


class Actions(commands.Cog):
    """いいね・リプライ機能を提供するCog"""
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        logger.info("Actions cog が初期化されました")
    
    @app_commands.command(name="like", description="❤️ いいねする")
    async def like_command(self, interaction: Interaction) -> None:
        """いいねコマンド"""
        try:
            logger.info(f"いいねコマンド実行: ユーザー {interaction.user.name} (ID: {interaction.user.id})")
            modal = LikeModal()
            await interaction.response.send_modal(modal)
        except Exception as e:
            logger.error(f"いいねコマンド実行中にエラーが発生しました: {e}", exc_info=True)
            try:
                await interaction.response.send_message(
                    "エラーが発生しました。もう一度お試しください。",
                    ephemeral=True
                )
            except:
                logger.error("いいねコマンドのエラーメッセージ送信に失敗しました")
    
    @app_commands.command(name="reply", description="💬 リプライする")
    async def reply_command(self, interaction: Interaction) -> None:
        """リプライコマンド"""
        try:
            logger.info(f"リプライコマンド実行: ユーザー {interaction.user.name} (ID: {interaction.user.id})")
            modal = ReplyModal()
            await interaction.response.send_modal(modal)
        except Exception as e:
            logger.error(f"リプライコマンド実行中にエラーが発生しました: {e}", exc_info=True)
            try:
                await interaction.response.send_message(
                    "エラーが発生しました。もう一度お試しください。",
                    ephemeral=True
                )
            except:
                logger.error("リプライコマンドのエラーメッセージ送信に失敗しました")
    
    @app_commands.command(name="unreply", description="🗑️ リプライを削除")
    async def unreply_command(self, interaction: Interaction) -> None:
        """リプライ削除コマンド"""
        try:
            logger.info(f"リプライ削除コマンド実行: ユーザー {interaction.user.name} (ID: {interaction.user.id})")
            modal = UnreplyModal()
            await interaction.response.send_modal(modal)
        except Exception as e:
            logger.error(f"リプライ削除コマンド実行中にエラーが発生しました: {e}", exc_info=True)
            try:
                await interaction.response.send_message(
                    "エラーが発生しました。もう一度お試しください。",
                    ephemeral=True
                )
            except:
                logger.error("リプライ削除コマンドのエラーメッセージ送信に失敗しました")
    
    @app_commands.command(name="unlike", description="💔 いいねを削除")
    async def unlike_command(self, interaction: Interaction) -> None:
        """いいね削除コマンド"""
        try:
            logger.info(f"いいね削除コマンド実行: ユーザー {interaction.user.name} (ID: {interaction.user.id})")
            modal = UnlikeModal()
            await interaction.response.send_modal(modal)
        except Exception as e:
            logger.error(f"いいね削除コマンド実行中にエラーが発生しました: {e}", exc_info=True)
            try:
                await interaction.response.send_message(
                    "エラーが発生しました。もう一度お試しください。",
                    ephemeral=True
                )
            except:
                logger.error("いいね削除コマンドのエラーメッセージ送信に失敗しました")


class UnlikeModal(ui.Modal, title="💔 いいねを削除"):
    """いいねを削除する投稿IDを入力するモーダル"""
    
    def __init__(self):
        super().__init__(timeout=300)
        self.file_manager = FileManager()
        
        self.post_id_input = ui.TextInput(
            label="📝 投稿ID",
            placeholder="いいねを削除する投稿のIDを入力...",
            required=True,
            style=discord.TextStyle.short,
            max_length=10
        )
        
        self.add_item(self.post_id_input)
    
    async def on_submit(self, interaction: Interaction) -> None:
        """いいね削除実行"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            post_id = int(self.post_id_input.value.strip())
            user_id = str(interaction.user.id)
            
            # 投稿の存在確認
            post = self.file_manager.get_post(post_id)
            if not post:
                await interaction.followup.send(
                    "❌ **投稿が見つかりません**\n\n"
                    f"投稿ID: {post_id} の投稿が存在しません。",
                    ephemeral=True
                )
                return
            
            # ユーザーのいいねを検索
            likes_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                    'data', 'likes')
            
            logger.info(f"いいね削除試行: 投稿ID={post_id}, ユーザーID={user_id}")
            logger.info(f"いいねディレクトリ: {likes_dir}")
            
            like_found = False
            like_file_path = None
            
            if os.path.exists(likes_dir):
                logger.info(f"いいねディレクトリが存在します")
                files = os.listdir(likes_dir)
                logger.info(f"いいねファイル一覧: {files}")
                
                for filename in files:
                    if filename.startswith(f'{post_id}_') and filename.endswith('.json'):
                        like_file_path = os.path.join(likes_dir, filename)
                        try:
                            with open(like_file_path, 'r', encoding='utf-8') as f:
                                like_data = json.load(f)
                            
                            logger.info(f"ファイル {filename} のデータ: {like_data}")
                            
                            # いいねしたユーザーが一致するか確認
                            if like_data.get('user_id') == user_id:
                                like_found = True
                                logger.info(f"いいねが見つかりました: {like_file_path}")
                                break
                        except (json.JSONDecodeError, FileNotFoundError) as e:
                            logger.error(f"ファイル読み込みエラー {filename}: {e}")
                            continue
            else:
                logger.warning(f"いいねディレクトリが存在しません: {likes_dir}")
            
            if not like_found:
                logger.warning(f"いいねが見つかりませんでした: 投稿ID={post_id}, ユーザーID={user_id}")
                await interaction.followup.send(
                    "❌ **いいねが見つかりません**\n\n"
                    f"投稿ID: {post_id} にあなたのいいねが見つかりません。",
                    ephemeral=True
                )
                return
            
            # いいねファイルを削除
            if like_file_path and os.path.exists(like_file_path):
                # ファイルからメッセージIDを取得して削除
                try:
                    with open(like_file_path, 'r', encoding='utf-8') as f:
                        like_data = json.load(f)
                        message_id = like_data.get('message_id')
                        channel_id = like_data.get('channel_id')
                    
                    if message_id and channel_id:
                        # いいねチャンネルのメッセージを削除
                        likes_channel = interaction.guild.get_channel(int(channel_id))
                        if likes_channel:
                            try:
                                like_message = await likes_channel.fetch_message(int(message_id))
                                await like_message.delete()
                                logger.info(f"いいねメッセージを削除しました: メッセージID={message_id}")
                            except (discord.NotFound, discord.Forbidden):
                                logger.warning(f"いいねメッセージの削除に失敗しました: {message_id}")
                except (json.JSONDecodeError, FileNotFoundError):
                    pass
                
                # ファイルを削除
                os.remove(like_file_path)
                logger.info(f"いいねを削除しました: 投稿ID={post_id}, ユーザーID={user_id}")
            else:
                logger.error(f"いいねファイルが見つかりません: {like_file_path}")
                await interaction.followup.send(
                    "❌ **エラーが発生しました**\n\n"
                    "いいねファイルが見つかりません。",
                    ephemeral=True
                )
                return
            
            await interaction.followup.send(
                f"💔 **いいねを削除しました**\n\n"
                f"投稿ID: {post_id} のいいねを削除しました。",
                ephemeral=True
            )
            
            # GitHubに保存する処理
            from .github_sync import sync_to_github
            await sync_to_github("unlike", interaction.user.name, post_id)
            
        except ValueError:
            await interaction.followup.send(
                "❌ **エラーが発生しました**\n\n"
                "投稿IDは数字で入力してください。",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"いいね削除処理中にエラーが発生しました: {e}")
            await interaction.followup.send(
                "💔 エラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )


class UnreplyModal(ui.Modal, title="🗑️ リプライを削除"):
    """リプライを削除するリプライIDを入力するモーダル"""
    
    def __init__(self):
        super().__init__(timeout=300)
        self.file_manager = FileManager()
        
        self.reply_id_input = ui.TextInput(
            label="💬 リプライID",
            placeholder="削除するリプライのIDを入力...",
            required=True,
            style=discord.TextStyle.short,
            max_length=10
        )
        
        self.add_item(self.reply_id_input)
    
    async def on_submit(self, interaction: Interaction) -> None:
        """リプライ削除実行"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            reply_id = self.reply_id_input.value.strip()
            user_id = str(interaction.user.id)
            
            logger.info(f"リプライ削除試行: リプライID={reply_id}, ユーザーID={user_id}")
            
            # リプライファイルを検索
            replies_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                     'data', 'replies')
            
            logger.info(f"リプライディレクトリ: {replies_dir}")
            
            reply_found = False
            reply_file_path = None
            reply_data = None
            
            if os.path.exists(replies_dir):
                logger.info(f"リプライディレクトリが存在します")
                files = os.listdir(replies_dir)
                logger.info(f"リプライファイル一覧: {files}")
                
                for filename in files:
                    if filename.endswith('.json'):
                        reply_file_path = os.path.join(replies_dir, filename)
                        try:
                            with open(reply_file_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            
                            logger.info(f"ファイル {filename} のデータ: {data}")
                            
                            # リプライIDとユーザーが一致するか確認
                            if (data.get('id') == reply_id and 
                                data.get('user_id') == user_id):
                                reply_found = True
                                reply_data = data
                                logger.info(f"リプライが見つかりました: {reply_file_path}")
                                break
                        except (json.JSONDecodeError, FileNotFoundError) as e:
                            logger.error(f"ファイル読み込みエラー {filename}: {e}")
                            continue
            else:
                logger.warning(f"リプライディレクトリが存在しません: {replies_dir}")
            
            if not reply_found:
                logger.warning(f"リプライが見つかりませんでした: リプライID={reply_id}, ユーザーID={user_id}")
                await interaction.followup.send(
                    "❌ **リプライが見つかりません**\n\n"
                    f"リプライID: {reply_id} のリプライが見つからないか、あなたのリプライではありません。",
                    ephemeral=True
                )
                return
            
            # リプライファイルを削除
            if reply_file_path and os.path.exists(reply_file_path):
                # ファイルからメッセージIDを取得して削除
                try:
                    with open(reply_file_path, 'r', encoding='utf-8') as f:
                        reply_data = json.load(f)
                        message_id = reply_data.get('message_id')
                        channel_id = reply_data.get('channel_id')
                    
                    if message_id and channel_id:
                        # リプライチャンネルのメッセージを削除
                        replies_channel = interaction.guild.get_channel(int(channel_id))
                        if replies_channel:
                            try:
                                reply_message = await replies_channel.fetch_message(int(message_id))
                                await reply_message.delete()
                                logger.info(f"リプライメッセージを削除しました: メッセージID={message_id}")
                            except (discord.NotFound, discord.Forbidden):
                                logger.warning(f"リプライメッセージの削除に失敗しました: {message_id}")
                except (json.JSONDecodeError, FileNotFoundError):
                    pass
                
                # ファイルを削除
                os.remove(reply_file_path)
                logger.info(f"リプライを削除しました: リプライID={reply_id}, ユーザーID={user_id}")
            else:
                logger.error(f"リプライファイルが見つかりません: {reply_file_path}")
                await interaction.followup.send(
                    "❌ **エラーが発生しました**\n\n"
                    "リプライファイルが見つかりません。",
                    ephemeral=True
                )
                return
            
            await interaction.followup.send(
                f"🗑️ **リプライを削除しました**\n\n"
                f"リプライID: {reply_id} のリプライを削除しました。",
                ephemeral=True
            )
            
            # GitHubに保存する処理
            from .github_sync import sync_to_github
            await sync_to_github("unreply", interaction.user.name, reply_id)
            
        except Exception as e:
            logger.error(f"リプライ削除処理中にエラーが発生しました: {e}")
            await interaction.followup.send(
                "🗑️ エラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )


async def setup(bot: commands.Bot) -> None:
    """Cogをセットアップ"""
    try:
        logger.info("Actions cog のセットアップを開始します...")
        await bot.add_cog(Actions(bot))
        logger.info("Actions cog がセットアップされました")
        
        # コマンドが正常に登録されたか確認
        like_cmd = bot.tree.get_command('like')
        reply_cmd = bot.tree.get_command('reply')
        unlike_cmd = bot.tree.get_command('unlike')
        unreply_cmd = bot.tree.get_command('unreply')
        
        if like_cmd:
            logger.info("✅ /like コマンドが正常に登録されました")
        else:
            logger.error("❌ /like コマンドの登録に失敗しました")
            
        if reply_cmd:
            logger.info("✅ /reply コマンドが正常に登録されました")
        else:
            logger.error("❌ /reply コマンドの登録に失敗しました")
            
        if unlike_cmd:
            logger.info("✅ /unlike コマンドが正常に登録されました")
        else:
            logger.error("❌ /unlike コマンドの登録に失敗しました")
            
        if unreply_cmd:
            logger.info("✅ /unreply コマンドが正常に登録されました")
        else:
            logger.error("❌ /unreply コマンドの登録に失敗しました")
            
    except Exception as e:
        logger.error(f"Actions cog のセットアップ中にエラーが発生しました: {e}", exc_info=True)
        raise
