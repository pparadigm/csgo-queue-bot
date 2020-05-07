# qbot.py

from discord.ext import commands
import cogs

BOT_COLOR = 0x0DA0B7
DATA_PATH = 'guild_data.json'


def run(discord_token, dbl_token=None, donate_url=None, generic=False):
    """ Create the bot, add the cogs and run it. """
    bot = commands.Bot(command_prefix=('t?', 'T?'), case_insensitive=True)
    bot.add_cog(cogs.CacherCog(bot, DATA_PATH))
    bot.add_cog(cogs.ConsoleCog(bot))
    bot.add_cog(cogs.HelpCog(bot, BOT_COLOR))
    bot.add_cog(cogs.QueueCog(bot, BOT_COLOR))

    if not generic:
        bot.add_cog(cogs.MapDraftCog(bot, BOT_COLOR))
        bot.remove_command('cap')

    if dbl_token:
        bot.add_cog(cogs.DblCog(bot, dbl_token))

    bot.run(discord_token)
