from discord import Embed
from discord.ext.commands import Cog, command, has_role, guild_only
from discord.ext.menus import MenuPages, ListPageSource
from ..bot import util
from ..db import db


class RewardPage(ListPageSource):
    def __init__(self, ctx, data):
        self.ctx = ctx

        super().__init__(data, per_page=25)

    async def write_page(self, menu, offset, fields=[]):
        len_data = len(self.entries)
        embed = Embed(title="Overview of awards",
                      colour=self.ctx.author.colour)
        embed.set_thumbnail(url=self.ctx.guild.me.avatar_url)
        embed.set_footer(text=f"{offset:,} - {min(len_data, offset + self.per_page - 1):,} of {len_data:,} rewards")

        for name, value in fields:
            embed.add_field(name=name, value=value, inline=False)

        return embed

    async def format_page(self, menu, entries):
        print(entries)
        offset = (menu.current_page * self.per_page) + 1
        fields = []
        table = ("\n".join(f"{idx+offset}. {self.ctx.bot.guild.get_member(entry[0]).display_name} (XP: {entry[1]})"
                           for idx, entry in enumerate(entries)))

        fields.append(("Weekly awards", table))

        return await self.write_page(menu, offset, fields)


class Awarder(Cog):
    def __init__(self, bot):
        self.bot = bot

    async def add_xp(self, ctx, user, xp_to_add):
        xp, xp_spent, lvl = db.record("SELECT XP, XPSpent, Level FROM exp WHERE UserID = (?)", user.id)

        xp_to_add = int(xp_to_add)
        new_lvl = int(((xp + xp_spent + xp_to_add) // 94) ** 0.53)

        db.execute("UPDATE exp SET XP = XP + ?, Level = ? WHERE UserID = (?)",
                   xp_to_add, new_lvl, user.id)

        if new_lvl > lvl:
            await util.check_lvl_rewards_command(ctx, user, new_lvl)

        db.commit()

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("awarder")

    @command(name="rewards", hidden=True, brief="Admin command to send out weekly minor rewards")
    @guild_only()
    @has_role(760426815155732500)
    async def send_rewards(self, ctx, *args):
        week_args = args[0:3]
        wks_select_args = args[3:]
        wks = await util.get_correct_wks(wks_select_args)
        if wks == 404:
            await ctx.send("The correct sheet was not found, please check if you filled in the following information:"
                           "- Your minorname (fit, tdfa, blockchain 15, blockchain 30)"
                           "- The current block (either a number between 1-4 or a letter between a-d)")
            return

        week_column = wks.find(" ".join(week_args))
        discord_names = wks.col_values(6)
        reward_values = wks.col_values(week_column.col)
        records =[]
        for i in range(2, len(discord_names)):
            if discord_names[i] != '#N/A':
                user = await util.get_user(ctx, discord_names[i])
                if user is not None:
                    await self.add_xp(ctx, user, reward_values[i])
                    records.append((user.id, int(reward_values[i])))

        menu = MenuPages(source=RewardPage(ctx, records),
                         clear_reactions_after=True,
                         timeout=60.0)
        await menu.start(ctx)


def setup(bot):
    bot.add_cog(Awarder(bot))
