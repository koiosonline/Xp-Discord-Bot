import json
import os
from typing import Optional
from web3 import Web3
from discord import Embed, Member
from discord.ext.commands import Cog, command, guild_only
from discord.ext.menus import MenuPages, ListPageSource
from dotenv import load_dotenv
from ..bot import util
from ..db import db

REWARDS = [("Lottery Ticket", 5000),
           ("Titan Token", 50000)]

with open("./data/web3/abi.json", encoding="utf8") as abi_json_file:
    ABI = json.load(abi_json_file)
load_dotenv()
p_key = os.getenv('WALLET_PK')
alchemy_url = os.getenv('ALCHEMY_KEY')
web3 = Web3(Web3.HTTPProvider(alchemy_url))
contract_address = "0xB49750AD82d11C12209A837210AB753AB09115a7"
public_key = "0xa79b4F8B62AC26C1b4429874d1690aa68af30254"
contract = web3.eth.contract(contract_address, abi=ABI)


class RewardCostPage(ListPageSource):
    def __init__(self, ctx, data):
        self.ctx = ctx

        super().__init__(data, per_page=5)

    async def write_page(self, menu, offset, fields=[]):
        len_data = len(self.entries)
        embed = Embed(title="Overview of available nectar rewards",
                      colour=self.ctx.author.colour)
        embed.set_thumbnail(url=self.ctx.guild.me.avatar_url)
        embed.set_footer(text=f"{offset:,} - {min(len_data, offset + self.per_page - 1):,} of {len_data:,} rewards")

        for name, value in fields:
            embed.add_field(name=name, value=value, inline=False)

        return embed

    async def format_page(self, menu, entries):
        offset = (menu.current_page * self.per_page) + 1
        fields = []
        table = (
            "\n".join(f"{idx + offset} (Reward: {entry[0]} | Cost: {entry[1]})"
                      for idx, entry in enumerate(entries)))

        fields.append(("Available rewards", table))

        return await self.write_page(menu, offset, fields)


class RedeemXp(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.remove_command("redeem_xp")

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("redeem_xp")

    """
    Command which sends a message with an overview of available rewards and associated costs

    :param ctx: the context
    """
    @command(name="reward_overview", brief="Get overview of exchange rates")
    @guild_only()
    async def reward_overview(self, ctx):
        menu = MenuPages(source=RewardCostPage(ctx, REWARDS),
                         clear_reactions_after=True,
                         timeout=300.0)
        await menu.start(ctx)

    """
    Command to buy a lottery ticket

    :param ctx: the context
    :param target: optional argument if you want to buy a ticket for someone else
    :param *args: string arguments containing the minor and block
    """
    @command(name="redeem_ticket", brief="Redeem xp for a book lottery ticket (minor-specific)")
    @guild_only()
    async def redeem_ticket(self, ctx, target: Optional[Member], *args):
        target = target or ctx.author
        wks = await util.get_correct_wks(args)
        if wks == 404:
            await ctx.send("The correct sheet was not found, please check if you filled in the following information:"
                           "- Your minorname (fit, tdfa, blockchain 15, blockchain 30)"
                           "- The current block (either a number between 1-4 or a letter between a-d)")
            return

        xp, xp_spent = db.record("SELECT XP, XPSpent FROM exp WHERE UserID = (?)", ctx.author.id)

        for rewards in REWARDS:
            if rewards[0] == "Lottery Ticket":
                price = rewards[1]

        if int(xp) < price:
            await ctx.send("You have insufficient nectar!")
            return

        ticket_cell = wks.find("# Tickets")
        name_cell = wks.find(f"{target.name}#{target.discriminator}")

        if name_cell is not None:
            if wks.cell(name_cell.row, ticket_cell.col).value is None:
                wks.update_cell(name_cell.row, ticket_cell.col, 1)
                db.execute("UPDATE exp SET XP = XP - ?, XPSpent = XPSpent + ? WHERE UserID = (?)",
                           price, price, ctx.author.id)
                await ctx.send(f"Bought a ticket for {price} nectar!")
                db.commit()
            elif int(wks.cell(name_cell.row, ticket_cell.col).value) < 2:
                wks.update_cell(name_cell.row, ticket_cell.col, 2)
                db.execute("UPDATE exp SET XP = XP - ?, XPSpent = XPSpent + ? WHERE UserID = (?)",
                           price, price, ctx.author.id)
                await ctx.send(f"Bought another ticket for {price} nectar!")
                db.commit()
            else:
                await ctx.send("You already reached the maximum amount of tickets!")
        else:
            await ctx.send("You have not registered your current Discord name in the minor typeform")

    """
    Command to buy a token

    :param ctx: the context
    """
    @command(name="redeem_token", aliases=["redeem_titan"], brief="Redeem nectar for a Titan token")
    @guild_only()
    async def redeem_token(self, ctx):
        xp, xp_spent = db.record("SELECT XP, XPSpent FROM exp WHERE UserID = (?)", ctx.author.id)

        for rewards in REWARDS:
            if rewards[0] == "Titan Token":
                price = rewards[1]

        if int(xp) >= price:
            await ctx.send("Await instructions in DM")

            # DM user and listen for an answer for a minute, when listening the bot can't open another DM channel, which
            # is why the time is limited.
            await ctx.author.send("Hi, please answer to this message with your public key, "
                                      "the token will be sent here. You have 60 seconds to respond.")
            msg = await self.bot.wait_for('message', check=lambda x: x.channel == ctx.author.dm_channel
                                                                     and x.author == ctx.author, timeout=60)
            # Check if valid address
            if web3.isAddress(msg.content):
                to_address = msg.content
                nonce = web3.eth.get_transaction_count(public_key)
                # Check if bot address has tokens, then build the transaction, fees may differ for different chains.
                # Possible TODO: Add function to retrieve current fees for chosen chain in stead of fixed maxFee
                if int(contract.functions.balanceOf(public_key).call()) >= 10 ** 18:
                    titan_tx = contract.functions.transfer(
                        to_address,
                        10 ** 18,
                    ).buildTransaction({
                        'chainId': 137,
                        'gas': 70000,
                        'maxFeePerGas': web3.toWei('1000', 'gwei'),
                        'maxPriorityFeePerGas': web3.toWei('1000', 'gwei'),
                        'nonce': nonce,
                    })
                    # Sign transaction using private key
                    signed_tx = web3.eth.account.sign_transaction(titan_tx, private_key=p_key)
                    await ctx.author.send("Waiting for the transaction to complete")

                    # Wait until transaction is completed, if it fails the receipt status will be 0. If value error is
                    # triggered fees may be too low or address given may be wrong
                    try:
                        web3.eth.send_raw_transaction(signed_tx.rawTransaction)
                        receipt = web3.eth.wait_for_transaction_receipt(web3.toHex(web3.keccak(signed_tx.rawTransaction)))
                        if receipt.status == 0:
                            await ctx.author.send("The transaction failed, please contact an admin")
                            return
                    except ValueError:
                        await ctx.author.send("The transaction values are incorrect, please contact an admin")
                        return

                    # If tx is successful send confirmation message containing the transaction hash
                    db.execute("UPDATE exp SET XP = XP - ?, XPSpent = XPSpent + ? WHERE UserID = (?)",
                               price, price, ctx.author.id)
                    await ctx.author.send(f"You bought a Titan Token for {price} nectar! The token should be in your wallet"
                                          f" at any moment. The hash will be at "
                                          f"https://polygonscan.com/tx/{web3.toHex(web3.keccak(signed_tx.rawTransaction))}")
                    db.commit()
                else:
                    await ctx.author.send("There is currently not enough tokens available, please contact an admin")

            else:
                await ctx.author.send("This is not a legitimate ethereum public key, please try again")

        else:
            await ctx.send("You have insufficient nectar for a Titan Token!")


def setup(bot):
    bot.add_cog(RedeemXp(bot))
