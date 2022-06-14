import os
from datetime import datetime
from asyncio import sleep, TimeoutError
from discord import Intents
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from discord.ext.commands import Bot as BotBase, BadArgument
from discord.ext.commands import CommandNotFound, Context, MissingRequiredArgument, MissingRole
from discord.errors import HTTPException, Forbidden
from ..db import db

PREFIX = "+"
OWNER_IDS = [128525332692074496]
# Windows
# COGS = [path.split("\\")[-1][:-3] for path in glob("./botlib/cogs/*.py")]

# Not super clean solution, but works for now
COGS = ["awarder", "exp", "help", "welcome", "redeem_xp", "games", "twitter"]

IGNORE_EXCEPTIONS = (CommandNotFound, BadArgument)
load_dotenv()


class Ready(object):
    def __init__(self):
        for cog in COGS:
            setattr(self, cog, False)

    def ready_up(self, cog):
        setattr(self, cog, True)
        print(f" {cog} cog ready")

    def all_ready(self):
        return all([getattr(self, cog) for cog in COGS])


class Bot(BotBase):
    def __init__(self):
        self.PREFIX = PREFIX
        self.ready = False
        self.cogs_ready = Ready()
        self.guild = None
        self.stdout = None
        self.scheduler = AsyncIOScheduler()

        db.autosave(self.scheduler)
        super().__init__(
            command_prefix=PREFIX,
            owner_ids=OWNER_IDS,
            intents=Intents.all()
        )

    def setup(self):
        for cog in COGS:
            self.load_extension(f"botlib.cogs.{cog}")
            print(f" {cog} cog loaded")

        print("Setup complete")

    def update_db(self):
        db.multiexec("INSERT OR IGNORE INTO exp (UserID) VALUES (?)",
                     ((member.id,) for member in self.guild.members))

        db.commit()

    def run(self, version):
        self.VERSION = version

        self.setup()

        self.TOKEN = os.getenv('DISCORD_TOKEN')

        print("Running bot...")
        super().run(self.TOKEN, reconnect=True)

    async def process_commands(self, message):
        ctx = await self.get_context(message, cls=Context)

        if not self.ready:
            await ctx.send("Not ready to receive commands yet, please wait a few seconds.")

        else:
            await self.invoke(ctx)

    async def on_connect(self):
        print("bot connected")

    async def on_disconnect(self):
        print("bot disconnected")

    async def on_error(self, err, *args, **kwargs):
        if err == "on_command_error":
            await args[0].send("Something went wrong.")

        raise

    async def on_command_error(self, ctx, exc):
        if any([isinstance(exc, error) for error in IGNORE_EXCEPTIONS]):
            pass

        elif isinstance(exc, MissingRequiredArgument):
            await ctx.send("One or more required arguments are missing")

        elif isinstance(exc, MissingRole):
            await ctx.send("You do not have the role required to do this")

        elif isinstance(exc.original, TimeoutError):
            await ctx.send("Timed out, please try again")

        elif isinstance(exc.original, HTTPException):
            await ctx.send("Unable to send message, you might have to enable DM's.")

        elif isinstance(exc.original, Forbidden):
            await ctx.send("No permission to do this")

        elif hasattr(exc, "original"):
            raise exc.original

        else:
            raise exc

    async def on_ready(self):
        if not self.ready:
            # Change to correct server id
            self.guild = self.get_guild(758719930383597608)
            self.stdout = self.get_channel(968110570643554344)

            self.update_db()

            # await self.stdout.send("Now online!")

            while not self.cogs_ready.all_ready():
                await sleep(0.5)

            self.ready = True

        else:
            print("bot connected")

    async def on_message(self, message):
        if not message.author.bot:
            await self.process_commands(message)


bot = Bot()
