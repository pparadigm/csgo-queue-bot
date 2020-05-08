# qbot.py

from discord.ext import commands
import cogs

BOT_COLOR = 0x0DA0B7
DATA_PATH = 'guild_data.json'


def run(discord_token, generic=False):
    """ Create the bot, add the cogs and run it. """
    bot = commands.Bot(command_prefix=('q!', 'Q!'), case_insensitive=True)
    bot.add_cog(cogs.CacherCog(bot, DATA_PATH))
    bot.add_cog(cogs.ConsoleCog(bot))
    bot.add_cog(cogs.HelpCog(bot, BOT_COLOR))
    bot.add_cog(cogs.QueueCog(bot, BOT_COLOR))

    if not generic:
        bot.remove_command('cap')

    bot.run(discord_token)
