import json
from typing import Optional

from discord import Reaction, Member, Embed
from discord.ext.commands import Cog, command, has_role, guild_only
from random import randint
from datetime import datetime, timedelta
from discord.ext.menus import MenuPages, ListPageSource

from ..bot import util
from ..db import db

# Assign XP types
Message_Posted, Add_Reaction, Remove_Reaction = "Message", "Add_Reaction", "Remove_Reaction"

class Leaderboard(ListPageSource):
    def __init__(self, ctx, data):
        self.ctx = ctx

        super().__init__(data, per_page=10)

    async def write_page(self, menu, offset, fields=[]):
        len_data = len(self.entries)

        embed = Embed(title="XP Leaderboard",
                      colour=self.ctx.author.colour)
        embed.set_thumbnail(url=self.ctx.guild.me.avatar_url)
        embed.set_footer(text=f"{offset:,} - {min(len_data, offset + self.per_page - 1):,} of {len_data:,} members")

        for name, value in fields:
            embed.add_field(name=name, value=value, inline=False)

        return embed

    async def format_page(self, menu, entries):
        offset = (menu.current_page * self.per_page) + 1
        fields = []
        table = ("\n".join(f"{idx+offset}. {self.ctx.bot.guild.get_member(entry[0]).display_name} (nectar: {entry[4]} "
                           f"| Level: {entry[3]})"
                           for idx, entry in enumerate(entries)))

        fields.append(("Ranks", table))

        return await self.write_page(menu, offset, fields)


class Exp(Cog):
    def __init__(self, bot):
        self.bot = bot

    async def level_embed(self):
        pass

    async def process_xp(self, message, xp_type):
        xp, xp_spent, lvl, xplock = db.record("SELECT XP, XPSpent, Level, XPLock FROM exp WHERE UserID = (?)", message.author.id)
        total_user_xp = xp + xp_spent

        if xp_type == Message_Posted:
            if datetime.utcnow() > datetime.fromisoformat(xplock):
                await self.add_xp_message(message, total_user_xp, lvl)

        elif xp_type == Add_Reaction:
            await self.add_xp_reaction(message, total_user_xp, lvl, True)

        elif xp_type == Remove_Reaction:
            await self.add_xp_reaction(message, total_user_xp, lvl, False)

    async def add_xp_message(self, message, xp, lvl):
        xp_to_add = randint(5, 15)

        new_lvl = int(((xp + xp_to_add) // 94) ** 0.53)

        db.execute("UPDATE exp SET XP = XP + ?, Level = ?, XPLock = ? WHERE UserID = (?)",
                   xp_to_add, new_lvl, (datetime.utcnow() + timedelta(seconds=60)).isoformat(), message.author.id)

        if new_lvl > lvl:
            await util.check_lvl_rewards_message(message, new_lvl)

        db.commit()

    async def add_xp_reaction(self, message, xp, lvl, reaction_added):
        if reaction_added:
            xp_to_add = 100

        else:
            xp_to_add = -100

        new_lvl = int(((xp + xp_to_add) // 94) ** 0.53)

        db.execute("UPDATE exp SET XP = XP + ?, Level = ? WHERE UserID = (?)",
                   xp_to_add, new_lvl, message.author.id)

        if new_lvl > lvl:
            await util.check_lvl_rewards_message(message, new_lvl)

        db.commit()

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("exp")

    @Cog.listener()
    async def on_message(self, message):
        if not message.author.bot:
            await self.process_xp(message, Message_Posted)

    @Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if str(reaction.emoji) == "💯":
            if user != reaction.message.author and not reaction.message.author.bot:
                await self.process_xp(reaction.message, Add_Reaction)

    @Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        if str(reaction.emoji) == "💯":
            if user != reaction.message.author and not reaction.message.author.bot:
                await self.process_xp(reaction.message, Remove_Reaction)

    @command(name="tip", aliases=["give"], brief="Tip nectar to another user")
    @guild_only()
    async def tip_xp(self, ctx, member: Member, amount_to_tip: int, *, reason: Optional[str] = ""):
        xp_tipper = db.record("SELECT XP FROM exp WHERE UserID = (?)", ctx.author.id)

        if amount_to_tip > 0:
            if member != ctx.author and not member.bot:
                if int(xp_tipper[0]) >= amount_to_tip:
                    xp, xp_spent_receiver, lvl = db.record("SELECT XP, XPSpent, Level FROM exp WHERE UserID = (?)", member.id)

                    new_lvl = int(((xp + xp_spent_receiver + amount_to_tip) // 94) ** 0.53)

                    db.execute("UPDATE exp SET XP = XP + ?, Level = ? WHERE UserID = (?)",
                               amount_to_tip, new_lvl, member.id)

                    db.execute("UPDATE exp SET XP = XP - ?, XPSpent = XPSpent + ? WHERE UserID = (?)",
                               amount_to_tip, amount_to_tip, ctx.author.id)

                    await ctx.send(f"{ctx.author.mention} has tipped {amount_to_tip} nectar to {member.mention} {reason}!")

                    if new_lvl > lvl:
                        await util.check_lvl_rewards_command(ctx, member, new_lvl)

                    db.commit()

                else:
                    await ctx.send("You do not have enough nectar to tip that much!")
            else:
                await ctx.send("You can't tip yourself or a bot!")
        else:
            await ctx.send("You can't tip nothing or a negative amount!")

    @command(name="level", aliases=["nectar"], brief="Get your level")
    @guild_only()
    async def display_level(self, ctx, target: Optional[Member]):
        target = target or ctx.author

        xp, xp_spent, lvl = db.record("SELECT XP, XPSpent, Level FROM exp WHERE UserID = ?", target.id) or (None, None)

        if lvl is not None:
            embed = Embed(title=f"Statistics of {target.display_name}",
                          colour=ctx.author.colour)
            embed.set_thumbnail(url=target.avatar_url)
            fields = [("Level ", lvl, True),
                      (" <:nectarfull:973863435030917121> ", xp, True),
                      (" <:nectardepleted:973863422133407755> ", xp_spent, True)]
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)
            await ctx.send(embed=embed)

        else:
            await ctx.send("That member is not tracked by the experience system.")

    @command(name="rank", brief="Get your rank")
    @guild_only()
    async def display_rank(self, ctx, target: Optional[Member]):
        target = target or ctx.author

        ids = db.column("SELECT UserID, (XP + XPSpent) AS XPTotal FROM exp ORDER BY XPTotal DESC")

        try:
            await ctx.send(f"{target.display_name} is rank {ids.index(target.id) + 1} of {len(ids)}")

        except ValueError:
            await ctx.send("That user is not tracked by the experience system.")

    @command(name="leaderboard", aliases=["lb"], brief="Get leaderboard")
    @guild_only()
    async def display_leaderboard(self, ctx):
        records = db.records("SELECT UserID, XP, XPSpent, Level, (XP + XPSpent) AS XPTotal FROM exp "
                             "ORDER BY XPTotal DESC")
        menu = MenuPages(source=Leaderboard(ctx, records),
                         clear_reactions_after=True,
                         timeout=60.0)
        await menu.start(ctx)

    @command(name="restore_nectar", aliases=["restore"], hidden=True,
             brief="Admin command to restore depleted nectar in case of unexpected error")
    @guild_only()
    @has_role(848930805052866600)
    async def restore_xp(self, ctx, member: Member, amount_to_restore: int):
        xp, xp_spent, lvl = db.record("SELECT XP, XPSpent, Level FROM exp WHERE UserID = (?)", member.id)

        if amount_to_restore <= xp_spent:
            db.execute("UPDATE exp SET XP = XP + ?, XPSpent = XPSpent - ? WHERE UserID = (?)",
                       amount_to_restore, amount_to_restore, member.id)
            await ctx.send(f"{member.display_name} got {amount_to_restore} nectar restored!")
            db.commit()
        else:
            await ctx.send("Not enough depleted nectar to restore!")

    @command(name="delete_nectar", aliases=["punish"], hidden=True, brief="Admin command, remove nectar in case of mistake")
    @guild_only()
    @has_role(848930805052866600)
    async def delete_xp(self, ctx, member: Member, amount_to_remove: int):
        xp, xp_spent, lvl = db.record("SELECT XP, XPSpent, Level FROM exp WHERE UserID = (?)", member.id)

        new_lvl = int(((xp + xp_spent - amount_to_remove) // 94) ** 0.53)

        if amount_to_remove > xp:
            amount_to_remove = amount_to_remove - xp
            db.execute("UPDATE exp SET XP = ?, XPSpent = XPSpent - ?, Level = ? WHERE UserID = (?)",
                       0, amount_to_remove, new_lvl, member.id)
            await ctx.send(f"Removed all XP and {amount_to_remove} spent XP from {member.mention}!")
        else:
            db.execute("UPDATE exp SET XP = XP - ?, Level = ? WHERE UserID = (?)", amount_to_remove, new_lvl, member.id)
            await ctx.send(f"Removed {amount_to_remove} nectar from {member.mention}!")

        if new_lvl < lvl:
            await util.check_lvl_rewards_command(ctx, member, new_lvl)

        db.commit()

    @command(name="mint_nectar", aliases=["mint"], hidden=True, brief="Admin command to add nectar for a user")
    @guild_only()
    @has_role(760426815155732500)
    async def mint_xp(self, ctx, member: Member, amount_to_add: int):
        if amount_to_add > 0:
            xp, xp_spent, lvl = db.record("SELECT XP, XPSpent, Level FROM exp WHERE UserID = (?)", member.id)

            new_lvl = int(((xp + xp_spent + amount_to_add) // 94) ** 0.53)

            db.execute("UPDATE exp SET XP = XP + ?, Level = ? WHERE UserID = (?)",
                       amount_to_add, new_lvl, member.id)

            await ctx.send(f"Added {amount_to_add} nectar for {member.mention}!")

            if new_lvl > lvl:
                await util.check_lvl_rewards_command(ctx, member, new_lvl)

            db.commit()
        else:
            await ctx.send("Negative amounts are not possible!")

    @command(name="airdrop_nectar", aliases=["airdrop"], hidden=True, brief="Admin command to airdrop nectar to everyone")
    @guild_only()
    @has_role(848930805052866600)
    async def airdrop_xp(self, ctx, amount: int):
        if amount > 0:
            member_ids = db.records("SELECT UserID FROM exp")
            for member in member_ids:
                xp, xp_spent, lvl = db.record("SELECT XP, XPSpent, Level FROM exp WHERE UserID = (?)", member[0])

                new_lvl = int(((xp + xp_spent + amount) // 94) ** 0.53)

                db.execute("UPDATE exp SET XP = XP + ?, Level = ? WHERE UserID = (?)",
                           amount, new_lvl, member[0])
            await ctx.send(f"Gave everyone {amount} nectar!")
            db.commit()
        else:
            await ctx.send("Negative amounts are not possible!")


def setup(bot):
    bot.add_cog(Exp(bot))
