import os
from sqlite3 import IntegrityError
from discord import Member
from discord.ext.commands import Cog, command, guild_only, has_role
from discord.ext import tasks
from dotenv import load_dotenv
import tweepy

from ..db import db
load_dotenv()
bearer = os.getenv('TWITTER_BEARER')
client = tweepy.Client(bearer_token=bearer)


class Twitter(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("twitter")
        self.check_new_tweets.start()
        self.check_new_likes.start()
        self.check_new_retweets.start()
        self.check_new_followers.start()

    """
    Check for new tweets every 3 hours
    """
    @tasks.loop(hours=3)
    async def check_new_tweets(self):
        user_id = 1121036692700454912
        latest_id = db.records("SELECT TweetID FROM latest_tweet_id")
        if not latest_id:
            latest_id = None
        else:
            latest_id = latest_id[0][0]

        response = client.get_users_tweets(user_id, tweet_fields="in_reply_to_user_id")

        for tweet in response.data:
            if tweet.in_reply_to_user_id is None:
                if latest_id is None:
                    db.execute("INSERT OR IGNORE INTO latest_tweet_id (TweetID) VALUES (?)", tweet.id)
                    await self.bot.stdout.send(f"new tweet: {tweet}")
                    db.commit()
                elif latest_id != tweet.id:
                    db.execute("UPDATE latest_tweet_id SET TweetID = ? WHERE TweetID = (?)", tweet.id, latest_id)
                    db.execute("DELETE FROM latest_tweet_likes")
                    db.execute("DELETE FROM latest_tweet_retweets")
                    db.commit()
                    await self.bot.stdout.send(f"new tweet: {tweet}")
                break

    """
    Check for new likes on latest tweet every hour
    """
    @tasks.loop(hours=1)
    async def check_new_likes(self):
        registered_users = db.records("SELECT TwitterName FROM twitter")
        rewarded_users = db.records("SELECT TwitterName FROM latest_tweet_likes")
        registered_users_array = []
        rewarded_users_array = []
        for reg_users in registered_users:
            registered_users_array.append(reg_users[0])

        for rew_users in rewarded_users:
            rewarded_users_array.append(rew_users[0])

        latest_id = db.records("SELECT TweetID FROM latest_tweet_id")
        if not latest_id or not registered_users_array:
            return
        else:
            latest_id = latest_id[0][0]
        users = client.get_liking_users(latest_id)
        if users.data is None:
            return

        for user in users.data:
            if user.username in registered_users_array and user.username not in rewarded_users_array:
                db.execute("INSERT OR IGNORE INTO latest_tweet_likes (TwitterName) VALUES (?)", user.username)
                user_id = db.record("SELECT UserID FROM twitter WHERE TwitterName = (?)", user.username)
                db.execute("UPDATE exp SET XP = XP + ? WHERE UserID = (?)",
                           250, user_id[0])
                await self.bot.stdout.send(f"Rewarded 250 to {self.bot.get_user(user_id[0]).name}, "
                                           f"for liking the latest Koios tweet")
                db.commit()

    """
    Check for new retweets on latest tweet every hour
    """
    @tasks.loop(hours=1)
    async def check_new_retweets(self):
        registered_users = db.records("SELECT TwitterName FROM twitter")
        rewarded_users = db.records("SELECT TwitterName FROM latest_tweet_retweets")
        registered_users_array = []
        rewarded_users_array = []
        for reg_users in registered_users:
            registered_users_array.append(reg_users[0])

        for rew_users in rewarded_users:
            rewarded_users_array.append(rew_users[0])

        latest_id = db.records("SELECT TweetID FROM latest_tweet_id")
        if not latest_id or not registered_users_array:
            return
        else:
            latest_id = latest_id[0][0]
        users = client.get_retweeters(latest_id)
        if users.data is None:
            return

        for user in users.data:
            if user.username in registered_users_array and user.username not in rewarded_users_array:
                db.execute("INSERT OR IGNORE INTO latest_tweet_retweets (TwitterName) VALUES (?)", user.username)
                user_id = db.record("SELECT UserID FROM twitter WHERE TwitterName = (?)", user.username)
                db.execute("UPDATE exp SET XP = XP + ? WHERE UserID = (?)",
                           500, user_id[0])
                await self.bot.stdout.send(f"Rewarded 500 to {self.bot.get_user(user_id[0]).name}, "
                                           f"for retweeting the latest Koios tweet")
                db.commit()

    """
    Check for new followers every 6 hours
    """
    @tasks.loop(hours=6)
    async def check_new_followers(self):
        user_id = 1121036692700454912
        registered_users = db.records("SELECT TwitterName FROM twitter")
        rewarded_users = db.records("SELECT TwitterName FROM followers")
        registered_users_array = []
        rewarded_users_array = []
        for reg_users in registered_users:
            registered_users_array.append(reg_users[0])

        for rew_users in rewarded_users:
            rewarded_users_array.append(rew_users[0])

        if not registered_users_array:
            return

        users = client.get_users_followers(user_id, max_results=1000)
        if users.data is None:
            return

        for user in users.data:
            if user.username in registered_users_array and user.username not in rewarded_users_array:
                db.execute("INSERT OR IGNORE INTO followers (TwitterName) VALUES (?)", user.username)
                user_id = db.record("SELECT UserID FROM twitter WHERE TwitterName = (?)", user.username)
                db.execute("UPDATE exp SET XP = XP + ? WHERE UserID = (?)",
                           3000, user_id[0])
                await self.bot.stdout.send(f"Rewarded 3000 to {self.bot.get_user(user_id[0]).name}, "
                                           f"for following the Koios twitter account!")
                db.commit()

    """
       Command to add twitter username

       :param ctx: the context
    """
    @command(name="add_twitter",  brief="Add twitter name to your account")
    @guild_only()
    async def set_twitter_name(self, ctx):
        twitter_name = db.record("SELECT TwitterName FROM twitter WHERE UserID = (?)", ctx.author.id)
        if twitter_name is not None:
            await ctx.send("You already set your Twitter account, if you want to change it use the `change_twitter`"
                           " command.")

        else:
            await ctx.send("Await instructions in DM")

            # DM user and listen for an answer for a minute, when listening the bot can't open another DM channel, which
            # is why the time is limited.
            await ctx.author.send("Hi, please answer to this message with only your twitter handle. Do not include the "
                                  "'@'! You have 60 seconds to respond.")
            msg = await self.bot.wait_for('message', check=lambda x: x.channel == ctx.author.dm_channel
                                                                     and x.author == ctx.author, timeout=60)

            if len(msg.content) > 15:
                await ctx.author.send("That is not a valid twitter handle, please restart the process.")

            else:
                try:
                    db.execute("INSERT OR IGNORE INTO twitter (UserID) VALUES (?)", ctx.author.id)
                    db.execute("UPDATE twitter SET TwitterName = ? WHERE UserID = (?)",
                               msg.content, ctx.author.id)
                    await ctx.author.send(f"Your Twitter name has been set to {msg.content}")
                    db.commit()
                except IntegrityError:
                    await ctx.author.send("That handle has already been registered, if this was not you please contact"
                                          " an admin.")

    """
       Command to change twitter username

       :param ctx: the context
    """
    @command(name="change_twitter", brief="Add twitter name to your account")
    @guild_only()
    async def change_twitter_name(self, ctx):
        twitter_name = db.record("SELECT TwitterName FROM twitter WHERE UserID = (?)", ctx.author.id)
        if twitter_name is None:
            await ctx.send("You have not set your twitter name, you can do this with the `add_twitter` command.")

        else:
            await ctx.send("Await instructions in DM")

            # DM user and listen for an answer for a minute, when listening the bot can't open another DM channel, which
            # is why the time is limited.
            await ctx.author.send(f"Hi, your current twitter name is set to {twitter_name[0]}, do you want to change this? "
                                  f"(yes/no)")
            msg = await self.bot.wait_for('message', check=lambda x: x.channel == ctx.author.dm_channel
                                                                     and x.author == ctx.author, timeout=30)
            if msg.content == "yes" or msg.content == "Yes":
                await ctx.author.send("Hi, please answer to this message with only your twitter handle. "
                                      "You have 60 seconds to respond.")
                msg = await self.bot.wait_for('message', check=lambda x: x.channel == ctx.author.dm_channel
                                                                         and x.author == ctx.author, timeout=60)
                if len(msg.content) > 15:
                    await ctx.author.send("That is not a valid twitter handle, please restart the process.")

                else:
                    try:
                        db.execute("UPDATE twitter SET TwitterName = ? WHERE UserID = (?)",
                                   msg.content, ctx.author.id)
                        await ctx.author.send(f"Your Twitter name has been updated to {msg.content}")
                        db.commit()
                    except IntegrityError:
                        await ctx.author.send(
                            "That handle has already been registered, if this was not you please contact"
                            " an admin.")
            else:
                await ctx.author.send("Keeping Twitter name as it is.")

    @command(name="get_twitter_from_user", hidden=True, brief="Admin command to get registered twitter name for user")
    @guild_only()
    @has_role(848930805052866600)
    async def get_twitter_from_user(self, ctx, member: Member):
        twitter_name = db.record("SELECT TwitterName FROM twitter WHERE UserID = (?)", member.id)
        if twitter_name is None:
            await ctx.send("There is no Twitter handle registered for that user")
        else:
            await ctx.author.send(f"That user's Twitter name is {twitter_name[0]}")

    @command(name="get_user_from_twitter", hidden=True, brief="Admin command to get user that registered a twitter handle")
    @guild_only()
    @has_role(848930805052866600)
    async def get_user_from_twitter(self, ctx, handle: str):
        user_id = db.record("SELECT UserID FROM twitter WHERE TwitterName = (?)", handle)
        if user_id is None:
            await ctx.send("There is no Twitter handle registered for that user")
        else:
            await ctx.author.send(f"That user's Twitter name is {user_id[0].name}")

    @command(name="delete_twitter", hidden=True,
             brief="Admin command to remove twitter handle from user")
    @guild_only()
    @has_role(848930805052866600)
    async def remove_twitter_handle(self, ctx, member: Member):
        twitter_name = db.record("SELECT TwitterName FROM twitter WHERE UserID = (?)", member.id)
        if twitter_name is None:
            await ctx.send("There is no Twitter handle registered for that user")
        else:
            db.execute("DELETE FROM twitter WHERE UserID = (?)", member.id)
            await ctx.send("Twitter for user deleted")


def setup(bot):
    bot.add_cog((Twitter(bot)))