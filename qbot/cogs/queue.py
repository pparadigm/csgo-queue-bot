# queue.py

import discord
from discord.ext import commands


class Iconography:
    """ A group of attributes representing a command reaction. """

    def __init__(self, name, emoji, image_url):
        """ Set attributes. """
        self.name = name
        self.emoji = emoji
        self.image_url = image_url

BASE_URL = 'https://raw.githubusercontent.com/alrlchoa/acnh-water-bot/tree/master/assets/maps/images/'

watering_can = Iconography('Watering Can', '<:watering_can:707933922125676634>', f'{BASE_URL}watering_can.png')

class Announcement:
    """A group of attributes representing the current running post. Needed to keep track of current poster."""
    def __init__(self, message=None, host=None):
        self.message = message
        self.host = host

class QQueue:
    """ Queue class for the bot. """

    def __init__(self, active=None, capacity=10, timeout=None, last_msg=None):
        """ Set attributes. """
        # Assign empty lists inside function to make them unique to objects
        self.active = [] if active is None else active  # List of players in the queue
        self.capacity = capacity  # Max queue size
        # self.timeout = timeout  # Number of minutes of inactivity after which to empty the queue
        self.last_msg = last_msg  # Last sent confirmation message for the join command
        self.curr_post = Announcement()
        self.brownies = {} #Brownie point counter?
        self.old_brownies = {}

    @property
    def is_default(self):
        """ Indicate whether the QQueue has any non-default values. """
        return self.active == [] and self.capacity == 10


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
    
    def add_points(self,user):
        """Add a brownie point for volunteering to water"""
        queue = self.guild_queues[user.guild]
        if user.display_name in queue.brownies:
            if queue.brownies[user.display_name] < -3:
                queue.old_brownies[user.display_name] = queue.brownies[user.display_name]
                queue.brownies[user.display_name] += 3
            queue.brownies[user.display_name] += 2
        else:
            queue.old_brownies[user.display_name] = 0
            queue.brownies[user.display_name] = 0
        print("Added Points: ",queue.brownies[user.display_name])
        return
    
    def remove_points(self,user):
        """Add a brownie point for volunteering to water"""
        queue = self.guild_queues[user.guild]
        if user.display_name in queue.brownies:
            queue.old_brownies[user.display_name] = queue.brownies[user.display_name]
            queue.brownies[user.display_name] -= 1
            if queue.brownies[user.display_name] <= -3:
                self.clear_user(user)
        else:
            queue.old_brownies[user.display_name] = 0
            queue.brownies[user.display_name] = 0
        return
    
    def clear_user(self, user):
        queue = self.guild_queues[user.guild]
        brownies = queue.brownies[user.display_name]
        if brownies <= -6 and user.id != queue.active[0].id:
            self.queue_remove(user)
        else:
            self.warn_user(user, -2 - brownies)
        return
    
    def queue_remove(self, user):
        queue = self.guild_queues[user.guild]
        if user in queue.active:
            queue.active.remove(user)
            user.send("We are terribly sorry, but due to inactivity foound by the bot, we have been forced to remove you from the queue. Please contact a mod if this is a mistake.")        
        queue.brownies.pop(user.display_name, None)
        queue.old_brownies.pop(user.display_name, None) 
        return
    
    def warn_user(self, user, n):
        queue = self.guild_queues[user.guild]
        brownies = queue.brownies[user.display_name]
        if user.id == queue.active[0].id:
            user.send("Hi! We noticed it may be taking a while to water your flowers. need any help from the mods?")
        elif user in queue.active:
            user.send(f"Hi! We've noticed that you may be inactive in the queue. If you could, please help out water. Thank you! This counts as warning # {n}.")
        return
    
    def point_swipe(self):
        queue = self.guild_queues[user.guild]        
        for key in queue.brownies.keys():
            queue.brownies[user.display_name] -= 1
        print("I have collected the point tax.")
        return
    
    @commands.command(brief='Testing Private DMs')
    async def message(self, ctx):
        user = ctx.author
        print("Attempting to send private DM")
        await user.send("Imma slide in here for testing.")
        print("Did I do it?")
    
    @commands.command(brief='Penalize someone. For testing purposes only')
    @commands.has_permissions(administrator=True)
    async def penalty(self, ctx):
        user = ctx.author
        self.remove_points(user)
        queue = self.guild_queues[user.guild]
        print(queue.brownies[user.display_name])
    
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


    @commands.command(brief='Leave the queue')
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
            self.point_swipe()
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
        flag = False
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
            embed = discord.Embed(title=f' Islander: {islandee} \n Dodo Code: {dodo_code} \n Please react with {watering_can.emoji} to earmark you for going.', color=self.color)
            flag = True
        msg = await ctx.send(embed=embed)
        if flag:
            queue.curr_post.message = msg #Store Current Dodo Post as current listing
            queue.curr_post.host = ctx #Store Current Dodo Post as current listing
            await msg.add_reaction(watering_can.emoji)
    
    @commands.command(brief='Check brownie status. For testing only.')
    @commands.has_permissions(administrator=True)
    async def brownie(self, ctx):
        queue = self.guild_queues[ctx.guild]
        print(queue.brownies)
    
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """ Remove a map from the draft when a user reacts with the corresponding icon. """
        print("Garnered a reaction")
        if user == self.bot.user:
            return
            
        guild = user.guild
        queue = self.guild_queues[guild]

        if queue.curr_post.message is None or reaction.message.id != queue.curr_post.message.id:
            return
        
        if str(reaction.emoji) == watering_can.emoji: # Someone clicked water
            #Give them brownie points or something
            self.add_points(user)
            return
     
    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        """ Remove a map from the draft when a user reacts with the corresponding icon. """
        print("Garnered a reaction")
        if user == self.bot.user:
            return
            
        guild = user.guild
        queue = self.guild_queues[guild]

        if queue.curr_post.message is None or reaction.message.id != queue.curr_post.message.id:
            return
        
        if str(reaction.emoji) == watering_can.emoji: # Someone clicked water
            #Give them brownie points or something
            queue.brownies[user.display_name] = queue.old_brownies[user.display_name]
            print("Points = ",queue.brownies[user.display_name])
            return  