# queue.py

import discord
from discord.ext import commands


class QQueue:
    """ Queue class for the bot. """

    def __init__(self, active=None, capacity=10, bursted=None, timeout=None, last_msg=None):
        """ Set attributes. """
        # Assign empty lists inside function to make them unique to objects
        self.active = [] if active is None else active  # List of players in the queue
        self.capacity = capacity  # Max queue size
        self.bursted = [] if bursted is None else bursted  # Cached last filled queue
        # self.timeout = timeout  # Number of minutes of inactivity after which to empty the queue
        self.last_msg = last_msg  # Last sent confirmation message for the join command

    @property
    def is_default(self):
        """ Indicate whether the QQueue has any non-default values. """
        return self.active == [] and self.capacity == 10 and self.bursted == []


class QueueCog(commands.Cog):
    """ Cog to manage queues of players among multiple servers. """

    def __init__(self, bot, color):
        """ Set attributes. """
        self.bot = bot
        self.guild_queues = {}  # Maps Guild -> QQueue
        self.color = color

    @commands.Cog.listener()
    async def on_ready(self):
        """ Initialize an empty list for each guild the bot is in. """
        for guild in self.bot.guilds:
            if guild not in self.guild_queues:  # Don't add empty queue if guild already loaded
                self.guild_queues[guild] = QQueue()

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """ Initialize an empty list for guilds that are added. """
        self.guild_queues[guild] = QQueue()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        """ Remove queue list when a guild is removed. """
        self.guild_queues.pop(guild)

    async def cog_before_invoke(self, ctx):
        """ Trigger typing at the start of every command. """
        await ctx.trigger_typing()

    def queue_embed(self, guild, title=None):
        """"""
        queue = self.guild_queues[guild]

        if title:
            title += f' ({len(queue.active)}/{queue.capacity})'

        if queue.active != []:  # If there are users in the queue
            queue_str = ''.join(f'{e_usr[0]}. {e_usr[1].mention}\n' for e_usr in enumerate(queue.active, start=1))
        else:  # No users in queue
            queue_str = '_The queue is empty..._'

        embed = discord.Embed(title=title, description=queue_str, color=self.color)
        embed.set_footer(text='Players will receive a notification when the queue fills up')
        return embed

    def burst_queue(self, guild):
        queue = self.guild_queues[guild]
        queue.bursted = queue.active  # Save bursted queue for player draft
        queue.active = []  # Reset the player queue to empty
        user_mentions = ''.join(user.mention for user in queue.bursted)
        popflash_cog = self.bot.get_cog('PopflashCog')

        if popflash_cog:
            popflash_url = popflash_cog.get_popflash_url(guild)
            description = f'[Join the PopFlash lobby here]({popflash_url})'
        else:
            description = ''

        pop_embed = discord.Embed(title='Queue has filled up!', description=description, color=self.color)
        return pop_embed, user_mentions
    
    @commands.command(brief='Join the queue')
    async def join(self, ctx):
        """ Check if the member can be added to the guild queue and add them if so. """
        queue = self.guild_queues[ctx.guild]

        if ctx.author in queue.active:  # Author already in queue
            title = f'**{ctx.author.display_name}** is already in the queue'
        elif len(queue.active) >= queue.capacity:  # Queue full
            title = f'Unable to add **{ctx.author.display_name}**: Queue is full'
        else:  # Open spot in queue
            queue.active.append(ctx.author)
            title = f'**{ctx.author.display_name}** has been added to the queue'

        # Check and burst queue if full.
        embed = self.queue_embed(ctx.guild, title)

        if queue.last_msg:
            try:
                await queue.last_msg.delete()
            except discord.errors.NotFound:
                pass

        queue.last_msg = await ctx.send(embed=embed)


    @commands.command(brief='Leave the queue (or the bursted queue)')
    async def leave(self, ctx):
        """ Check if the member can be remobed from the guild and remove them if so. """
        queue = self.guild_queues[ctx.guild]
        flag = False    #Flag for checking if author is top of queue
        if ctx.author == queue.active[0]:
            flag = True
        if ctx.author in queue.active:
            queue.active.remove(ctx.author)
            title = f'**{ctx.author.display_name}** has been removed from the queue '
        else:
            title = f'**{ctx.author.display_name}** isn\'t in the queue '

        embed = self.queue_embed(ctx.guild, title)
        if queue.last_msg:
            try:
                await queue.last_msg.delete()
            except discord.errors.NotFound:
                pass

        queue.last_msg = await ctx.channel.send(embed=embed)
        if flag:
            if len(queue.active) > 0:
                mention = queue.active[0].id
                await ctx.send(f"<@{mention}>, you're good to go!")
            if len(queue.active) > 1:
                mention = queue.active[1].id
                await ctx.send(f"<@{mention}>, please be on deck with your Dodo Code!")

    @commands.command(brief='Display who is currently in the queue')
    async def view(self, ctx):
        """  Display the queue as an embed list of mentioned names. """
        queue = self.guild_queues[ctx.guild]
        embed = self.queue_embed(ctx.guild, 'Players in queue')
        if queue.last_msg:
            try:
                await queue.last_msg.delete()
            except discord.errors.NotFound:
                pass

        queue.last_msg = await ctx.send(embed=embed)

    @commands.command(usage='remove <user mention>',
                      brief='Remove the mentioned user from the queue (must have server kick perms)')
    @commands.has_permissions(kick_members=True)
    async def remove(self, ctx):
        try:
            removee = ctx.message.mentions[0]
        except IndexError:
            embed = discord.Embed(title='Mention a player in the command to remove them', color=self.color)
            await ctx.send(embed=embed)
        else:
            queue = self.guild_queues[ctx.guild]
            
            flag = False    #Flag for checking if removee is top of queue
            if removee == queue.active[0]:
                flag = True
                
            if removee in queue.active:
                queue.active.remove(removee)
                title = f'**{removee.display_name}** has been removed from the queue'
            elif queue.bursted and removee in queue.bursted:
                queue.bursted.remove(removee)

                if len(queue.active) >= 1:
                    # await ctx.trigger_typing()  # Need to retrigger typing for second send
                    saved_queue = queue.active.copy()
                    first_in_queue = saved_queue[0]
                    queue.active = queue.bursted + [first_in_queue]
                    queue.bursted = []
                    pop_embed, user_mentions = self.burst_queue(ctx.guild)
                    await ctx.send(user_mentions, embed=pop_embed)

                    if len(queue.active) > 1:
                        queue.active = saved_queue[1:]

                    return
                else:
                    queue.active = queue.bursted
                    queue.bursted = []
                    title = f'**{removee.display_name}** has been removed from the most recent filled queue'

            else:
                title = f'**{removee.display_name}** is not in the queue or the most recent filled queue'

            embed = self.queue_embed(ctx.guild, title)

            if queue.last_msg:
                try:
                    await queue.last_msg.delete()
                except discord.errors.NotFound:
                    pass

            queue.last_msg = await ctx.send(embed=embed)
            
            if flag:
                if len(queue.active) > 0:
                    mention = queue.active[0].id
                    await ctx.send(f"<@{mention}>, you're good to go!")
                if len(queue.active) > 1:
                    mention = queue.active[1].id
                    await ctx.send(f"<@{mention}>, please be on deck with your Dodo Code!")

    @commands.command(brief='Empty the queue (must have server kick perms)')
    @commands.has_permissions(kick_members=True)
    async def empty(self, ctx):
        """ Reset the guild queue list to empty. """
        queue = self.guild_queues[ctx.guild]
        queue.active.clear()
        embed = self.queue_embed(ctx.guild, 'The queue has been emptied')

        if queue.last_msg:
            try:
                await queue.last_msg.delete()
            except discord.errors.NotFound:
                pass

        queue.last_msg = await ctx.send(embed=embed)

    @remove.error
    @empty.error
    async def remove_error(self, ctx, error):
        """ Respond to a permissions error with an explanation message. """
        if isinstance(error, commands.MissingPermissions):
            await ctx.trigger_typing()
            missing_perm = error.missing_perms[0].replace('_', ' ')
            title = f'Cannot remove players without {missing_perm} permission!'
            embed = discord.Embed(title=title, color=self.color)
            await ctx.send(embed=embed)

    @commands.command(brief='Set the capacity of the queue (Must have admin perms)')
    @commands.has_permissions(administrator=True)
    async def cap(self, ctx, new_cap):
        """ Set the queue capacity. """
        try:
            new_cap = int(new_cap)
        except ValueError:
            embed = discord.Embed(title=f'{new_cap} is not an integer', color=self.color)
        else:
            if new_cap < 1 or new_cap > 100:
                embed = discord.Embed(title='Capacity is outside of valid range', color=self.color)
            else:
                self.guild_queues[ctx.guild].capacity = new_cap
                embed = discord.Embed(title=f'Queue capacity set to {new_cap}', color=self.color)

        await ctx.send(embed=embed)

    @cap.error
    async def cap_error(self, ctx, error):
        """ Respond to a permissions error with an explanation message. """
        if isinstance(error, commands.MissingPermissions):
            await ctx.trigger_typing()
            missing_perm = error.missing_perms[0].replace('_', ' ')
            title = f'Cannot change queue capacity without {missing_perm} permission!'
            embed = discord.Embed(title=title, color=self.color)
            await ctx.send(embed=embed)
    
    @commands.command(brief='Announce your Dodo Code to the world. Must be top of queue to do so.')
    async def dodo(self, ctx, dodo_code=None):
        queue = self.guild_queues[ctx.guild]
        watering_can = "<:watering_can:707933922125676634>" #Your custom watering can emoji. Will change every server
        #Goal: Makes an announcement by the Bot that said Islander is next.
        if len(queue.active) == 0: #Checks if queue is empty
            embed = discord.Embed(title='Wuh-oh! It seems like the queue is empty. please hit q!join to join the queue!', color=self.color)
        elif ctx.author != queue.active[0]: #Checks if person is top of queue.
            embed = discord.Embed(title='Wuh-oh! You are not first in line right now.', color=self.color)
        elif dodo_code == None: #Check if something resenbling a Dodo Code was actually enetered
            embed = discord.Embed(title='Wuh-oh! Please put your Dodo Code after the command', color=self.color)
        elif len(dodo_code) != 5:
            embed = discord.Embed(title='Wuh-oh! It seems you did not enter a Dodo Code', color=self.color)
        else: #Person is legitimate and good
            islandee = ctx.author.display_name
            '''Will need to edit this line later. Need to add watering_can emoji'''
            embed = discord.Embed(title=f' Islander: {islandee} \n Dodo Code: {dodo_code} \n Please react with {watering_can} to earmark you for going.', color=self.color)
            
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """ Remove a map from the draft when a user reacts with the corresponding icon. """
        if user == self.bot.user:
            return

        guild = user.guild
        mdraft_data = self.guild_mdraft_data[guild]

        if mdraft_data.message is None or reaction.message.id != mdraft_data.message.id:
            return

        for m in mdraft_data.maps_left.copy():  # Iterate over copy to modify original w/o consequences
            if str(reaction.emoji) == m.emoji:
                async for u in reaction.users():
                    await reaction.remove(u)

                mdraft_data.maps_left.remove(m)

                if len(mdraft_data.maps_left) == 1:
                    map_result = mdraft_data.maps_left[0]
                    await mdraft_data.message.clear_reactions()
                    embed_title = f'We\'re going to {map_result.name}! {map_result.emoji}'
                    embed = discord.Embed(title=embed_title, color=self.color)
                    embed.set_image(url=map_result.image_url)
                    embed.set_footer(text=f'Be sure to select {map_result.name} in the PopFlash lobby')
                    await mdraft_data.message.edit(embed=embed)
                    mdraft_data.maps_left = None
                    mdraft_data.message = None
                else:
                    embed_title = f'**{user.name}** has banned **{m.name}**'
                    embed = discord.Embed(title=embed_title, description=self.maps_left_str(guild), color=self.color)
                    embed.set_thumbnail(url=m.image_url)
                    embed.set_footer(text=MapDraftCog.footer)
                    await mdraft_data.message.edit(embed=embed)

                break