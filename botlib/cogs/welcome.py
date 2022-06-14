from discord.ext.commands import Cog, command

from ..db import db


class Welcome(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("welcome")

    """
    Listener for new members

    :param member: the new member
    """
    @Cog.listener()
    async def on_member_join(self, member):
        db.execute("INSERT OR IGNORE INTO exp (UserID) VALUES (?)", member.id)
        print(f"User {member.id} Joined")
        db.commit()

    """
    Listener for leaving members

    :param member: the leaving member
    """
    @Cog.listener()
    async def on_member_remove(self, member):
        db.execute("DELETE FROM exp WHERE UserID = (?)", member.id)
        print(f"User {member.id} Left")
        db.commit()


def setup(bot):
    bot.add_cog((Welcome(bot)))