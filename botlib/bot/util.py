import json
import gspread
from discord.utils import get

# 1. Give access to the service account for the spreadsheet you want to use
# 2. Edit string values below to reflect name of the spreadsheet/worksheet used
sa = gspread.service_account(filename="spreadsheets/service_account/service_account.json")
sh_bc = sa.open("Overview Blockchain minor 2021 Blok 3 & 4")
sh_trade = sa.open("Overview Trading minor 2021 Blok 3 & 4")

with open("./data/public/spreadsheetData.json", encoding="utf8") as json_file:
    spreadsheet_data = json.load(json_file)


async def get_correct_wks(args):
    wks = 404
    if "blockchain" in args:
        if "15" in args:
            if "1" in args:
                wks = sh_bc.worksheet(spreadsheet_data["blockchainSheets"][0]["bc_block_A"])
            elif "2" in args:
                wks = sh_bc.worksheet(spreadsheet_data["blockchainSheets"][0]["bc_block_B_15"])
            elif "3" in args:
                wks = sh_bc.worksheet(spreadsheet_data["blockchainSheets"][0]["bc_block_C"])
            elif "4" in args:
                wks = sh_bc.worksheet(spreadsheet_data["blockchainSheets"][0]["bc_block_D_15"])
        elif "30" in args:
            if "1" in args:
                wks = sh_bc.worksheet(spreadsheet_data["blockchainSheets"][0]["bc_block_A"])
            elif "2" in args:
                wks = sh_bc.worksheet(spreadsheet_data["blockchainSheets"][0]["bc_block_B_30"])
            elif "3" in args:
                wks = sh_bc.worksheet(spreadsheet_data["blockchainSheets"][0]["bc_block_C"])
            elif "4" in args:
                wks = sh_bc.worksheet(spreadsheet_data["blockchainSheets"][0]["bc_block_D_30"])
    elif "tdfa" in args:
        if "1" in args:
            wks = sh_trade.worksheet(spreadsheet_data["tradingSheets"][0]["tdfa_fit_block_A"])
        elif "2" in args:
            wks = sh_trade.worksheet(spreadsheet_data["tradingSheets"][0]["tdfa_block_B"])
        elif "3" in args:
            wks = sh_trade.worksheet(spreadsheet_data["tradingSheets"][0]["tdfa_fit_block_C"])
        elif "4" in args:
            wks = sh_trade.worksheet(spreadsheet_data["tradingSheets"][0]["tdfa_block_D"])
    elif "fit" in args:
        if "1" in args:
            wks = sh_trade.worksheet(spreadsheet_data["tradingSheets"][0]["tdfa_fit_block_A"])
        elif "2" in args:
            wks = sh_trade.worksheet(spreadsheet_data["tradingSheets"][0]["fit_block_B"])
        elif "3" in args:
            wks = sh_trade.worksheet(spreadsheet_data["tradingSheets"][0]["tdfa_fit_block_C"])
        elif "4" in args:
            wks = sh_trade.worksheet(spreadsheet_data["tradingSheets"][0]["fit_block_D"])
    return wks


async def get_user(ctx, name: str):
    name = name.split("#")
    user = get(ctx.guild.members, name=name[0], discriminator=name[1])
    return user


async def check_lvl_rewards_message(message, lvl):
    if lvl >= 25:
        if (new_role := message.guild.get_role(809778267740569610)) not in message.author.roles:
            await message.author.add_roles(new_role)
            await message.channel.send(f"Congratulations {message.author.display_name}, you just became a {new_role.name}!")
    elif 10 <= lvl < 25:
        if (new_role := message.guild.get_role(809778063054733322)) not in message.author.roles:
            await message.author.add_roles(new_role)
            await message.channel.send(f"Congratulations {message.author.display_name}, you just became a {new_role.name}!")
    elif 5 <= lvl < 10:
        if (new_role := message.guild.get_role(809777804421365771)) not in message.author.roles:
            await message.author.add_roles(new_role)
            await message.channel.send(f"Congratulations {message.author.display_name}, you just became a {new_role.name}!")


async def check_lvl_rewards_command(ctx, member, lvl):
    if lvl >= 25:
        if (new_role := ctx.guild.get_role(809778267740569610)) not in member.roles:
            await member.add_roles(new_role)
            await ctx.send(f"Congratulations {member.display_name}, you just became a {new_role.name}!")

    elif 10 <= lvl < 25:
        if (new_role := ctx.guild.get_role(809778063054733322)) not in member.roles:
            await member.add_roles(new_role)
            await ctx.send(f"Congratulations {member.display_name}, you just became a {new_role.name}!")
        if (remove_role := ctx.guild.get_role(809778267740569610)) in member.roles:
            await member.remove_roles(remove_role)

    elif 5 <= lvl < 10:
        if (new_role := ctx.guild.get_role(809777804421365771)) not in member.roles:
            await member.add_roles(new_role)
            await ctx.send(f"Congratulations {member.display_name}, you just became a {new_role.name}!")
        if (remove_role := ctx.guild.get_role(809778063054733322)) in member.roles:
            await member.remove_roles(remove_role)
