import logging
import os
import sys

import discord
from discord.ext import commands

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ThoughtBot(commands.Bot):
    """メインボットクラス"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix=commands.when_mentioned_or(),
            intents=intents,
            help_command=None,
            application_id=os.getenv('APPLICATION_ID'),
            activity=discord.Game(name="/help でヘルプを表示")
        )
    
    async def setup_hook(self):
        """起動時の初期化処理"""
        logger.info("ボットの初期化を開始します...")
        
        # Cogの読み込み
        await self.load_cogs()
        
        logger.info("ボットの初期化が完了しました")
    
    async def load_cogs(self):
        """Cogを読み込む"""
        cogs_dir = "cogs"
        
        if not os.path.exists(cogs_dir):
            logger.warning(f"Cogディレクトリが見つかりません: {cogs_dir}")
            return
        
        # thoughtsサブディレクトリも含めて探索
        for root, dirs, files in os.walk(cogs_dir):
            for filename in files:
                if filename.endswith(".py") and not filename.startswith("__"):
                    # Cogファイルのみを読み込む（utils, modal, paginationなどは除外）
                    if any(exclude in filename for exclude in ['utils', 'modal', 'pagination', 'embed', 'validation', 'type_view', 'search_posts', 'search_replies']):
                        logger.info(f"ユーティリティファイルをスキップ: {filename}")
                        continue
                    
                    # 相対パスをモジュールパスに変換
                    rel_path = os.path.relpath(root, cogs_dir)
                    if rel_path == ".":
                        cog_path = f"cogs.{filename[:-3]}"
                    else:
                        cog_path = f"cogs.{rel_path.replace(os.sep, '.')}.{filename[:-3]}"
                    
                    try:
                        await self.load_extension(cog_path)
                        logger.info(f"Cogを読み込みました: {cog_path}")
                    except Exception as e:
                        logger.error(f"Cogの読み込みに失敗しました: {cog_path} - {e}")
    
    async def on_ready(self):
        """ボット準備完了時の処理"""
        logger.info(f"ボットがログインしました: {self.user}")
        logger.info(f"サーバー数: {len(self.guilds)}")
        
        # スラッシュコマンドを同期
        try:
            synced = await self.tree.sync()
            logger.info(f"スラッシュコマンドを同期しました: {len(synced)}個")
        except Exception as e:
            logger.error(f"スラッシュコマンドの同期に失敗しました: {e}")
    
    async def on_guild_join(self, guild):
        """サーバー参加時の処理"""
        logger.info(f"新しいサーバーに参加しました: {guild.name} (ID: {guild.id})")
        
        # スラッシュコマンドを同期
        try:
            synced = await self.tree.sync(guild=guild)
            logger.info(f"サーバー {guild.name} でスラッシュコマンドを同期しました: {len(synced)}個")
        except Exception as e:
            logger.error(f"サーバー {guild.name} でのスラッシュコマンド同期に失敗しました: {e}")
    
    async def on_command_error(self, ctx, error):
        """コマンドエラー時の処理"""
        if isinstance(error, commands.CommandNotFound):
            return
        
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("このコマンドを実行する権限がありません。")
            return
        
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("必要な引数が不足しています。")
            return
        
        logger.error(f"コマンドエラー: {error}")
        await ctx.send("コマンドの実行中にエラーが発生しました。")
    
    async def on_error(self, event_method, *args, **kwargs):
        """イベントエラー時の処理"""
        logger.error(f"イベントエラー: {event_method} - {args} - {kwargs}")

def main():
    """メイン関数"""
    # 環境変数の確認
    if not os.getenv('DISCORD_TOKEN'):
        logger.error("DISCORD_TOKEN環境変数が設定されていません")
        return
    
    if not os.getenv('APPLICATION_ID'):
        logger.error("APPLICATION_ID環境変数が設定されていません")
        return
    
    # ボットの起動
    bot = ThoughtBot()
    
    try:
        bot.run(os.getenv('DISCORD_TOKEN'))
    except KeyboardInterrupt:
        logger.info("ボットを停止します")
    except Exception as e:
        logger.error(f"ボットの起動中にエラーが発生しました: {e}")

if __name__ == "__main__":
    main()
