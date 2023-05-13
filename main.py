import discord
from discord.ext import commands
import json
import random
from typing import Union
from typing import Any, Dict
from discord import option
import logging
import asyncio
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.FileHandler('logs.txt'), logging.StreamHandler()])

class DiscordBot:
    def __init__(self):
        self.config = self._config
        
        self.totalChanges = 0
        
        self.last_message_time = {}

    @property
    def _config(self):
        with open("config.json") as file:
            return json.load(file)
    
    @property
    def get_case_names(self):
        cases = self.config["cases"]
        sorted_cases = sorted(cases.items(), key=lambda x: x[1]["case_cost"])
        return [f"{case_name} (${'{:,}'.format(case_data['case_cost'])})" for case_name, case_data in sorted_cases]
    
    def generate_case_result(self, case_data):
        card_previews = case_data['card_previews']
        probabilities = [preview['probability'] for preview in card_previews]
        values = [preview['value'] for preview in card_previews]
        item_names = [preview['card_preview'] for preview in card_previews]
        result_index = random.choices(range(len(card_previews)), probabilities, k=1)[0]
        result = card_previews[result_index].copy()
        result['item_value'] = values[result_index]
        result['item_name'] = item_names[result_index]
        return result

    def run(self):
        intents = discord.Intents.all()
        bot = commands.Bot(command_prefix="/", intents=intents)
        
        class functions():
            async def write_file(self):
                with open('config.json', 'w') as f: json.dump(self.config, f, indent=4)
            
            async def check_profile(self, user):
                if not str(user.id) in self.config.get("currency", {}):
                    self.config["currency"][str(user.id)] = {}
                    self.config["currency"][str(user.id)]['balance'] = 0
                    self.config["currency"][str(user.id)]['full_name'] = f"{user.name}#{user.discriminator}"
                    await functions.write_file(self)
                return self.config['currency'][str(user.id)]['balance']
            
            async def add_cash(self, user, user_balance: int, amount: int, isAdmin:bool=None, giver_id:str=None, author_balance:int=None):
                self.config["currency"][str(user.id)]['balance'] = user_balance + amount
                if isAdmin is not None and not isAdmin and giver_id is not None:
                    self.config["currency"][str(giver_id)]['balance'] = author_balance - amount
                    
                await functions.write_file(self)
                return self.config['currency'][str(user.id)]['balance']
            
        @bot.event
        async def on_ready():
            print("Bot ready")
        
        @bot.event
        async def on_message(ctx):
            cooldown = 10
            if ctx.author.bot: return
            
            current_time = asyncio.get_event_loop().time()
            author_id = str(ctx.author.id)
            if author_id in self.last_message_time and (current_time - self.last_message_time[author_id]) < cooldown: return
            await functions.check_profile(self, ctx.author)
            
            self.config["currency"][str(ctx.author.id)]['balance'] = 1 + int(self.config["currency"][str(ctx.author.id)]['balance'])
            
            self.totalChanges += 1
            
            self.last_message_time[author_id] = current_time
            
            if self.totalChanges % 10 == 0:
                await functions.write_file(self)
             
        @bot.event
        async def on_application_command_completion(ctx):
            server_id = ctx.guild.id if ctx.guild else "DM"
            user_id = ctx.author.id
            command_name = ctx.command.name
            logging.info(f"Server ID: {server_id} | User ID: {user_id} | Command: {command_name}")
        
        @commands.cooldown(1, 60, commands.BucketType.user)
        @bot.slash_command(description="Give a user a amount of cash")
        @option("user", discord.User, description="Select a User to send the cash to")
        @option("amount", int, description="Provide the amount to send", min_value=1)
        async def give_cash(ctx, user: discord.User, amount: int):
            
            if ctx.author.id in self.config["discord"]['owners']:
                user_balance = await functions.check_profile(self, user)
                user_total = await functions.add_cash(self, user, user_balance, amount*0.95, isAdmin=True)
                embed = discord.Embed(title=random.choice(self.config['messages']['give_cash']['title']), description=random.choice(self.config['messages']['give_cash']['messages']).format(user_mention=user.mention, amount=f"`{'{:,}'.format(amount)}`", user_total=f"`{'{:,}'.format(user_total)}`"),color=discord.Color.random())
                return await ctx.respond(embed=embed)
            
            if amount < 1:
                embed = discord.Embed(title=random.choice(self.config['messages']['send_negative_cash']['title']), description=random.choice(self.config['messages']['send_negative_cash']['messages']).format(user_mention=ctx.author.mention),color=discord.Color.random())
                return await ctx.respond(embed=embed, ephemeral=True)
            
            if ctx.author == user:
                embed = discord.Embed(title=random.choice(self.config['messages']['send_cash_self']['title']), description=random.choice(self.config['messages']['send_cash_self']['messages']).format(user_mention=user.mention),color=discord.Color.random())
                return await ctx.respond(embed=embed, ephemeral=True)
            
            author_balance = await functions.check_profile(self, ctx.author)
            if not amount < author_balance:
                embed = discord.Embed(title=random.choice(self.config['messages']['not_enough_balance']['title']), description=random.choice(self.config['messages']['not_enough_balance']['messages']), color=discord.Color.red())
                return await ctx.respond(embed=embed, ephemeral=True)
            
            user_balance = await functions.check_profile(self, user)
            user_total = await functions.add_cash(self, user, user_balance, amount, isAdmin=False, giver_id=ctx.author.id, author_balance=author_balance)
            
            embed = discord.Embed(title=random.choice(self.config['messages']['give_cash']['title']), description=random.choice(self.config['messages']['give_cash']['messages']).format(user_mention=user.mention, amount=f"`{'{:,}'.format(amount)}`", user_total=f"`{'{:,}'.format(user_total)}`"),color=discord.Color.random())
            return await ctx.respond(embed=embed)
            
            
            
        @commands.cooldown(1, 5, commands.BucketType.user)             
        @bot.slash_command(description="Get information about the users profile")
        @option("user", discord.User, description="Select a User to get information From", required=False)
        async def profile(ctx, user: discord.User):
            if user is not None:
                amount = await functions.check_profile(self, user)
                embed = discord.Embed(title=f"{user.name}#{user.discriminator} profile", color=discord.Color.random())
            else:
                amount = await functions.check_profile(self, ctx.author)
                embed = discord.Embed(title=f"{ctx.author.name}#{ctx.author.discriminator} profile", color=discord.Color.random())
            
            embed.add_field(name="Balance", value="{:,}".format(amount))
            await ctx.respond(embed=embed)
        
        @commands.cooldown(1, 30, commands.BucketType.user)
        @bot.slash_command(description="Show the global leaderboard")
        @option("page", int, description="Select the leaderboard page", required=False)
        async def leaderboard(ctx, page:int=1):
            sorted_data = sorted(self.config['currency'].items(), key=lambda x: x[1]["balance"], reverse=True)
            total_pages = (len(sorted_data) - 1) // 10 + 1
            
            if page < 1 or page > total_pages: page = total_pages
            
            start_index = (page - 1) * 10
            end_index = start_index + 10
            
            embed = discord.Embed(title="Leaderboard", color=discord.Color.random())
            
            leaderboard_page = sorted_data[start_index:end_index]
            leaderboard_page = sorted_data[start_index:end_index]
            total_not_found = 0
            for index, (user_id, user_data) in enumerate(leaderboard_page, start=start_index + 1):
                try:
                    balance = user_data["balance"]
                    full_name = user_data['full_name']
                    embed.add_field(name=f"#{index - total_not_found} User: {full_name}", value=f"Balance: {'{:,}'.format(balance)}", inline=False)
                except discord.NotFound:
                    total_not_found += 1
            
            await functions.check_profile(self, ctx.author)
            author_id = str(ctx.author.id)
            for index, (user_id, _) in enumerate(sorted_data):
                 if user_id == author_id:
                     rank = index + 1
                     break
                 
            embed.set_footer(text=f"Your Rank: #{rank} | Page: {page}/{total_pages}")
            await ctx.respond(embed=embed)
        
        @commands.cooldown(1, 120, commands.BucketType.user)
        @bot.slash_command(description="beg for money")
        @option("beg_method", description="Choose your beg method", choices=["Normal beg", "Super beg", "Advanced beg", "Millionaire beg"])
        async def beg(ctx, beg_method: str):
            user_balance = await functions.check_profile(self, ctx.author)
            if beg_method == "Normal beg":
                multiplier = 1
                chance = 2
            elif beg_method == "Super beg":
                multiplier = 2
                chance = 4
            elif beg_method == "Advanced beg":
                multiplier = 4  
                chance = 8
            elif beg_method == "Millionaire beg":
                multiplier = 50
                chance = 100
                
            number = random.randint(1, chance)
            if number == 1:
                amount = random.randint(1, 1000) * multiplier
                
                total_amount = await functions.add_cash(self, ctx.author, user_balance, amount, isAdmin=True)
                
                embed = discord.Embed(title=random.choice(self.config['messages']['successful_beg']['title']), description=random.choice(self.config['messages']['successful_beg']['messages']).format(user_mention=ctx.author.mention, amount=f"`{'{:,}'.format(amount)}`", total_amount=f"`{'{:,}'.format(total_amount)}`"),color=discord.Color.random())
                
                return await ctx.respond(embed=embed)
            
            embed = discord.Embed(title=random.choice(self.config['messages']['failed_beg']['title']), description=random.choice(self.config['messages']['failed_beg']['messages']).format(user_mention=ctx.author.mention),color=discord.Color.random())
            await ctx.respond(embed=embed)
       
        @commands.cooldown(1, 300, commands.BucketType.user)
        @bot.slash_command(description="Rob other people")
        @option("user", discord.User, description="Select a User ro rob")
        async def rob(ctx, user: discord.User):

            if ctx.author == user:
                embed = discord.Embed(title=random.choice(self.config['messages']['failed_robbery_self']['title']), description=random.choice(self.config['messages']['failed_robbery_self']['messages']).format(user_mention=ctx.author.mention),color=discord.Color.random())
                return await ctx.respond(embed=embed, ephemeral=True)

            user_balance = await functions.check_profile(self, ctx.author)
            if user_balance < 1000:
                embed = discord.Embed(title=random.choice(self.config['messages']['failed_rob_not_enough_author_money']['title']), description=random.choice(self.config['messages']['failed_rob_not_enough_author_money']['messages']).format(user_mention=ctx.author.mention),color=discord.Color.random())
                return await ctx.respond(embed=embed, ephemeral=True)
            
            target_balance = await functions.check_profile(self, user)
            
            if target_balance < 1000:
                embed = discord.Embed(title=random.choice(self.config['messages']['failed_rob_not_enough_target_money']['title']), description=random.choice(self.config['messages']['failed_rob_not_enough_target_money']['messages']).format(user_mention=ctx.author.mention),color=discord.Color.random())
                return await ctx.respond(embed=embed, ephemeral=True)
            
            calculated_chance = target_balance / user_balance
            
            if random.randint(1, 2 if calculated_chance < 2 else round(calculated_chance) if calculated_chance < 10 else 10) == 1:
                amount = random.randint(1, target_balance)
                await functions.add_cash(self, ctx.author, user_balance, amount, isAdmin=False, giver_id=user.id, author_balance=target_balance)
                embed = discord.Embed(title=random.choice(self.config['messages']['success_robbery']['title']), description=random.choice(self.config['messages']['success_robbery']['messages']).format(user_mention=ctx.author.mention, cash_stolen=f"`{'{:,}'.format(amount)}`"),color=discord.Color.random())
                await user.send(f"Get online {ctx.author.mention} just robbed you `{'{:,}'.format(amount)}` cash")
                return await ctx.respond(embed=embed)
            
            amount2 = random.randint(1, user_balance)
            await functions.add_cash(self, user, target_balance, amount2, isAdmin=False, giver_id=ctx.author.id, author_balance=user_balance)
            embed = discord.Embed(title=random.choice(self.config['messages']['failed_robbery']['title']), description=random.choice(self.config['messages']['failed_robbery']['messages']).format(user_mention=ctx.author.mention, cash_lost=f"`{'{:,}'.format(amount2)}`"),color=discord.Color.random())
            await user.send(f"Get online {ctx.author.mention} tried to rob you but failed and lost `{'{:,}'.format(amount2)}` cash")
            return await ctx.respond(embed=embed)
        
        @commands.cooldown(1, 60, commands.BucketType.user)
        @bot.slash_command(description="Gamble your money against the bot")
        @option("amount", int, min_value=100)
        async def gamble(ctx, amount):
            user_balance = await functions.check_profile(self, ctx.author)
            
            if not user_balance > amount:
                embed = discord.Embed(title=random.choice(self.config['messages']['insufficient_funds']['title']), description=random.choice(self.config['messages']['insufficient_funds']['messages']).format(user_mention=ctx.author.mention),color=discord.Color.random())
                return await ctx.respond(embed=embed, ephemeral=True)
            
            player_roll = random.randint(1, 6)
            bot_roll = random.randint(1, 6)
            if player_roll > bot_roll:
                winnings = amount * 2
                await functions.add_cash(self, ctx.author, user_balance, winnings, isAdmin=True)
                embed = discord.Embed(title=random.choice(self.config['messages']['dice_won']['title']), description=random.choice(self.config['messages']['dice_won']['messages']).format(user_mention=ctx.author.mention, player_roll=f"`{player_roll}`", winnings=f"`{'{:,}'.format(winnings)}`", bot_roll=f"`{bot_roll}`"),color=discord.Color.random())
                await ctx.respond(embed=embed)  
            elif bot_roll > player_roll:
                losses = -amount
                await functions.add_cash(self, ctx.author, user_balance, losses, isAdmin=True)
                embed = discord.Embed(title=random.choice(self.config['messages']['dice_lost']['title']), description=random.choice(self.config['messages']['dice_lost']['messages']).format(user_mention=ctx.author.mention, player_roll=f"`{player_roll}`", bot_roll=f"`{bot_roll}`", loss=f"`{'{:,}'.format(amount)}`"),color=discord.Color.random())
                await ctx.respond(embed=embed)
            else:
                embed = discord.Embed(title=random.choice(self.config['messages']['dice_tie']['title']), description=random.choice(self.config['messages']['dice_tie']['messages']).format(user_mention=ctx.author.mention, player_roll=f"`{player_roll}`", bot_roll=f"`{bot_roll}`"),color=discord.Color.random())
                await ctx.respond(embed=embed)
        
        @commands.cooldown(1, 10, commands.BucketType.user)
        @bot.slash_command(description="Info of a Case")
        @option("case", choices=self.get_case_names, description="Choose a Case to display")
        async def case_info(ctx, case: str):
            case = case.split(" (")[0]
            embed = discord.Embed(title=f"Case Info: {case}", color=discord.Color.random())
            embed.add_field(name="Case Cost", value='{:,}'.format(self.config['cases'][case]['case_cost']), inline=False)
            
            card_previews = ""
            for card_preview in self.config['cases'][case]["card_previews"]:
                card_name = card_preview["card_preview"]
                card_probability = card_preview["probability"]
                card_value = card_preview["value"]
                card_previews += f"**{card_name}** - Probability: {card_probability}%\nValue: {'{:,}'.format(card_value)}\n\n"
                
            embed.add_field(name="Card Previews", value=card_previews, inline=False)
            await ctx.respond(embed=embed)
            
        @commands.cooldown(1, 60, commands.BucketType.user)
        @bot.slash_command(description="Open a case and try your luck")
        @option("case", choices=self.get_case_names, description="Choose a Case to open")
        @option("case_amount", choices=[1, 2, 4], description="Choose amount of cases to open", required=False) 
        @option("against_bot", choices=[1, 2, 4], description="Choose amount of bots to play", required=False)
        async def open_case(ctx, case: str, case_amount: int=1, against_bot:int=False):
            total_cash_flow = 0
            
            user_balance = await functions.check_profile(self, ctx.author)
            
            case_data = case.split(" (")[0]
            
            if not user_balance > int(self.config['cases'][case_data]['case_cost']) * case_amount:
                embed = discord.Embed(title=random.choice(self.config['messages']['insufficient_funds']['title']), description=random.choice(self.config['messages']['insufficient_funds']['messages']).format(user_mention=ctx.author.mention),color=discord.Color.random())
                return await ctx.respond(embed=embed, ephemeral=True)
            
            user_total = await functions.add_cash(self, ctx.author, user_balance, -(int(self.config['cases'][case_data]['case_cost']) * case_amount), isAdmin=True)
            
            results = {}
            players = ["You"]
            
            if against_bot:
                for i in range(1, against_bot + 1):
                    players.append(f"Bot {i}")
                
            for player in players:
                player_results = []
                total_value = 0
                for _ in range(case_amount):
                    result = self.generate_case_result(self.config['cases'][case_data])
                    player_results.append(result)
                    total_value += result['item_value']
                total_cash_flow += total_value
                results[player] = {'items': player_results, 'total_value': total_value}
            
            embed = discord.Embed(title="Case Opening Results", description=f"Opened {case_amount} cases from {case}:", color=discord.Color.random())
            
            max_value_player = max(results, key=lambda x: results[x]['total_value'])
            
            for player, player_data in results.items():
                item_field = ""
                for result in player_data['items']:
                    item_name = result['item_name']
                    item_value = result['item_value']
                    item_field += f"Item: **{item_name}** ({'{:,}'.format(item_value)})\n"
                
                total_value = player_data['total_value']
                embed.add_field(name=player, value=f"Total Value: {'{:,}'.format(total_value)}\n\n{item_field}", inline=False)
            
            embed.set_footer(text=f"Winner: {max_value_player}")
            
            if max_value_player == "You":
                await functions.add_cash(self, ctx.author, user_total, total_cash_flow, isAdmin=True)
                
            await ctx.respond(embed=embed)

        @bot.slash_command(description="Every Command")
        async def help(ctx):
            embed = discord.Embed(title="Xolos Commands", color=discord.Color.random())
            embed.add_field(name="profile", value="Will show your profile information", inline=False)
            embed.add_field(name="leaderboard", value="Will show the users with the most coins", inline=False)
            embed.add_field(name="give_cash", value="Gives a user a amount of cash", inline=False)
            embed.add_field(name="beg", value="Beg for money", inline=False)
            embed.add_field(name="rob", value="Rob users money", inline=False)
            embed.add_field(name="gamble", value="Gamble your money", inline=False)
            embed.add_field(name="case_info", value="Info about a case with the items", inline=False)
            embed.add_field(name="open_case", value="Open a case", inline=False)
            await ctx.respond(embed=embed)
        
        @bot.event
        async def on_application_command_error(ctx, error):
            if isinstance(error, commands.CommandOnCooldown):
                        cooldown_time = "{:.2f}".format(float(error.retry_after))
                        embed = discord.Embed(title=random.choice(self.config['messages']['cooldown']['title']), description=random.choice(self.config['messages']['cooldown']['messages']).format(cooldown_time=cooldown_time), color=discord.Color.orange())
                        return await ctx.respond(embed=embed, ephemeral=True)
            await ctx.respond(f"A error occurred: ```{error}```", ephemeral=True)

        @bot.event
        async def on_application_command_error(ctx, error):
            if isinstance(error, commands.CommandOnCooldown):
                        cooldown_time = "{:.2f}".format(float(error.retry_after))
                        embed = discord.Embed(title=random.choice(self.config['messages']['cooldown']['title']), description=random.choice(self.config['messages']['cooldown']['messages']).format(cooldown_time=cooldown_time), color=discord.Color.orange())
                        return await ctx.respond(embed=embed, ephemeral=True)
            await ctx.respond(f"A error occurred: ```{error}```", ephemeral=True)
                                    
        bot.run(self.config.get("discord", {}).get("token", None))

DiscordBot().run()
