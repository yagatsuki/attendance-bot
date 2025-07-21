import os
import discord
from discord.ext import tasks, commands
import dotenv
import datetime

from server import server_thread

dotenv.load_dotenv()

TOKEN = os.environ.get("TOKEN")
# .envファイルにCHANNEL_ID, REACTION_CHANNEL_IDを追加
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", 0))
REACTION_CHANNEL_ID = int(os.environ.get("REACTION_CHANNEL_ID", 0))

intents = discord.Intents.default()
intents.reactions = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# 前回投稿したメッセージのID保持
# Botが再起動すると失われる
latest_message_id = None

# JSTの木曜日 10:00 (UTCの木曜日 01:00) に設定
# POST_TIME = datetime.time(hour=1, minute=0, tzinfo=datetime.timezone.utc)

# 1時間置きに設定 for Debug
@tasks.loop(hours=1)
# @tasks.loop(time=POST_TIME)
async def weekly_task():
    """
    毎週木曜日のJST 10:00に実行されるタスク。
    1. 前回の投稿のリアクションを集計して報告
    2. 新しい週の投稿を行う
    """
    global latest_message_id

    # 現在時刻が木曜日でなければ処理をしない
    # if datetime.datetime.now(datetime.timezone.utc).weekday() != 3: # 0:Mon, 1:Tue, 2:Wed, 3:Thu
        # return

    # --- リアクション集計処理 ---
    if latest_message_id:
        reaction_channel = bot.get_channel(REACTION_CHANNEL_ID)
        post_channel = bot.get_channel(CHANNEL_ID)

        if not reaction_channel:
            print(f"Error: Reaction channel with ID {REACTION_CHANNEL_ID} not found.")
        elif not post_channel:
            print(f"Error: Post channel with ID {CHANNEL_ID} not found.")
        else:
            try:
                message = await post_channel.fetch_message(latest_message_id)
                
                if not message.reactions:
                    await reaction_channel.send("前回の投稿にはリアクションがありませんでした。")
                else:
                    reacted_users = set()
                    for reaction in message.reactions:
                        async for user in reaction.users():
                            if not user.bot:
                                reacted_users.add(user)

                    if not reacted_users:
                        await reaction_channel.send("前回の投稿にユーザーからのリアクションはありませんでした。")
                    else:
                        reacted_members = set()
                        for user in reacted_users:
                            member = post_channel.guild.get_member(user.id)
                            if member:
                                reacted_members.add(member)
                        
                        if not reacted_members:
                            await reaction_channel.send("前回の投稿にユーザーからのリアクションはありませんでした。")
                        else:
                            user_names = [member.display_name for member in reacted_members]
                            response = f"前回のリアクション集計結果（{len(reacted_members)}名）：\n{', '.join(user_names)}"
                        
                        if len(response) > 2000:
                            await reaction_channel.send("メッセージが長すぎるため、表示できません。")
                        else:
                            await reaction_channel.send(response)

            except discord.NotFound:
                print(f"Warning: Message with ID {latest_message_id} not found. Skipping reaction collection.")
            except Exception as e:
                print(f"An error occurred during reaction collection: {e}")

    # --- 新規投稿処理 ---
    post_channel = bot.get_channel(CHANNEL_ID)
    if post_channel:
        new_message = await post_channel.send("今週の出勤確認です。出勤した方はリアクションをお願いします。")
        latest_message_id = new_message.id
        print(f"Posted a new message with ID: {latest_message_id}")
    else:
        print(f"Error: Post channel with ID {CHANNEL_ID} not found.")


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    weekly_task.start()

# Koyeb用 サーバー立ち上げ
server_thread()
bot.run(TOKEN)