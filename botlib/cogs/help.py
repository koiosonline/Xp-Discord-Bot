from typing import Optional

from discord import Embed
from discord.ext.commands import Cog, command, guild_only
from discord.ext.menus import MenuPages, ListPageSource
from discord.utils import get


def syntax(command):
    cmd_and_aliases = "|".join([str(command), *command.aliases])
    params = []

    for key, value in command.params.items():
        if key not in ("self", "ctx"):
            params.append(f"[{key}]" if "NoneType" in str(value) else f"<{key}>")

    params = " ".join(params)

    return f"```{cmd_and_aliases} {params}```"


class HelpMenu(ListPageSource):
    def __init__(self, ctx, data):
        self.ctx = ctx

        super().__init__(data, per_page=5)

    """
    Writes values to an embedded MenuPage
    
    :param menu: the menu pages object
    :param fields: array of fields to write to MenuPage
    """
    async def write_page(self, menu, fields=[]):
        offset = (menu.current_page*self.per_page) + 1
        len_data = len(self.entries)

        embed = Embed(title="Help",
                      description="Overview of commands",
                      colour=self.ctx.author.colour)
        embed.set_thumbnail(url=self.ctx.guild.me.avatar_url)
        embed.set_footer(text=f"{offset:,} - {min(len_data, offset+self.per_page-1):,} of {len_data:,} commands")

        for name, value in fields:
            embed.add_field(name=name, value=value, inline=False)

        return embed

    """
    Formats values for MenuPage

    :param menu: the menu pages object
    :param entries: list of unformatted entries
    """
    async def format_page(self, menu, entries):
        fields = []

        for entry in entries:
            fields.append((entry.brief or "No description", syntax(entry)))

        return await self.write_page(menu, fields)


class Help(Cog):
    """
    Initializes Cog

    :param bot: the bot object
    """
    def __init__(self, bot):
        self.bot = bot
        self.bot.remove_command("help")

    """
    Help overview if single command is given as input for the help command

    :param ctx: the context
    :param command: the command
    """
    async def cmd_help(self, ctx, command):
        embed = Embed(title=f"Help with `{command}`",
                      description=syntax(command),
                      colour=ctx.author.colour)
        embed.add_field(name="Command description", value=command.brief)
        await ctx.send(embed=embed)

    """
    Command to get an overview of command(s)

    :param ctx: the context
    :param cmd: optional, if given the help page will only give the description of given command. If empty a MenuPage of 
                all commands will be sent.
    """
    @command(name="help", brief="Overview of commands")
    @guild_only()
    async def show_help(self, ctx, cmd: Optional[str]):
        if cmd is None:
            commandlist = []
            for bot_command in list(self.bot.commands):
                if not bot_command.hidden:
                    commandlist.append(bot_command)
            menu = MenuPages(source=HelpMenu(ctx, commandlist),
                             delete_message_after=True,
                             timeout=60.0)
            await menu.start(ctx)
        
        else:
            if command := get(self.bot.commands, name=cmd):
                await self.cmd_help(ctx, command)

            else:
                await ctx.send("That command does not exist.")

    """
    Listener to ready up cog
    """
    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("help")


def setup(bot):
    bot.add_cog(Help(bot))