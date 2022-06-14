from typing import Optional

from aiohttp import request
from discord.ext.commands import Cog, command, BadArgument, cooldown, BucketType, guild_only
from discord import File, Member, Embed

from random import choice, randint

from ..db import db


class Games(Cog):
    def __init__(self, bot):
        self.bot = bot

    @command(name="dice", aliasses=["roll"])
    @guild_only()
    @cooldown(1, 60, BucketType.user)
    async def roll_dice(self, ctx, die_string: str):
        dice, value = (int(term) for term in die_string.split("d"))
        if dice <= 25:
            rolls = [randint(1, value) for i in range(dice)]

            await ctx.send(" + ".join([str(r) for r in rolls]) + f"= {sum(rolls)}")

        else:
            await ctx.send("Can't roll that many dice. Try a lower number")

    @command(name="cat", brief="Fetches a random cat picture")
    @guild_only()
    async def cat_image(self, ctx):
        cat_url = "http://some-random-api.ml/img/cat"

        async with request("GET", cat_url, headers={}) as response:
            if response.status == 200:
                data = await response.json()
                image_link = data["link"]

                embed = Embed(title="Cat image")
                embed.set_image(url=image_link)

                await ctx.send(embed=embed)

            else:
                await ctx.send(f"API returned a {response.status}")

    @command(name="start_lottery", brief="Start an xp lottery")
    @guild_only()
    async def start_lottery(self, ctx):
        pass

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("games")


def setup(bot):
    bot.add_cog(Games(bot))