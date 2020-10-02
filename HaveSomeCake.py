import discord
import re
import mysql.connector
from mysql.connector import Error
import urllib.request
import subprocess
import time
import requests
import random
from discord.utils import get
import discord.utils
from datetime import datetime
from discord import Webhook, RequestsWebhookAdapter, File
import csv
import json
import decimal
import asyncio


server_settings = { }
birthdays = { }
new_startup = True

client = discord.Client(heartbeat_timeout=600)

async def log_message(log_entry):
    current_time_obj = datetime.now()
    current_time_string = current_time_obj.strftime("%b %d, %Y-%H:%M:%S.%f")
    print(current_time_string + " - " + log_entry, flush = True)
    
async def commit_sql(sql_query, params = None):
    await log_message("Commit SQL: " + sql_query + "\n" + "Parameters: " + str(params))
    try:
        connection = mysql.connector.connect(host='localhost', database='Cake', user='REDACTED', password='REDACTED')    
        cursor = connection.cursor()
        result = cursor.execute(sql_query, params)
        connection.commit()
        return True
    except mysql.connector.Error as error:
        await log_message("Database error! " + str(error))
        return False
    finally:
        if(connection.is_connected()):
            cursor.close()
            connection.close()
            
                
async def select_sql(sql_query, params = None):
    if sql_query != 'SELECT UsersAllowed, CharName, PictureLink FROM Alts WHERE ServerId=%s AND Shortcut=%s;' and sql_query != 'SELECT Id,CharacterName,Currency,Experience FROM CharacterProfiles WHERE ServerId=%s AND UserId=%s;':
        await log_message("Select SQL: " + sql_query + "\n" + "Parameters: " + str(params))
    try:
        connection = mysql.connector.connect(host='localhost', database='Cake', user='REDACTED', password='REDACTED')
        cursor = connection.cursor()
        result = cursor.execute(sql_query, params)
        records = cursor.fetchall()
        if sql_query != 'SELECT UsersAllowed, CharName, PictureLink FROM Alts WHERE ServerId=%s AND Shortcut=%s;' and sql_query != 'SELECT Id,CharacterName,Currency,Experience FROM CharacterProfiles WHERE ServerId=%s AND UserId=%s;':
            await log_message("Returned " + str(records))
        return records
    except mysql.connector.Error as error:
        await log_message("Database error! " + str(error))
        return None
    finally:
        if(connection.is_connected()):
            cursor.close()
            connection.close()

async def execute_sql(sql_query):
    try:
        connection = mysql.connector.connect(host='localhost', database='Cake', user='REDACTED', password='REDACTED')
        cursor = connection.cursor()
        result = cursor.execute(sql_query)
        return True
    except mysql.connector.Error as error:
        await log_message("Database error! " + str(error))
        return False
    finally:
        if(connection.is_connected()):
            cursor.close()
            connection.close()
            
async def direct_message(message, response, embed=None):
    channel = await message.author.create_dm()
    await log_message("replied to user " + message.author.name + " in DM with " + response)
    if embed:
        await channel.send(embed=embed)
    else:
        try:
            message_chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
            for chunk in message_chunks:
                await channel.send("" + chunk)
                await asyncio.sleep(1)
            
        except discord.errors.Forbidden:
            await dm_tracker[message.author.id]["commandchannel"].send("You have DMs off. Please reply with =answer <reply> in the server channel.\n" + response)
        
async def post_webhook(channel, name, response, picture):
    temp_webhook = await channel.create_webhook(name='Chara-Tron')
    await temp_webhook.send(content=response, username=name, avatar_url=picture)
    await temp_webhook.delete() 
    
    
async def reply_message(message, response):
    if not message.guild:
        channel_name = dm_tracker[message.author.id]["commandchannel"].name
        server_name = str(dm_tracker[message.author.id]["server_id"])
    else:
        channel_name = message.channel.name
        server_name = message.guild.name
        
    await log_message("Message sent back to server " + server_name + " channel " + channel_name + " in response to user " + message.author.name + "\n\n" + response)
    
    message_chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
    for chunk in message_chunks:
        await message.channel.send(">>> " + chunk)
        asyncio.sleep(1)

async def admin_check(userid):
    if (userid != 610335542780887050):
        await log_message(str(userid) + " tried to call an admin message!")
        return False
    else:
        return True
		
@client.event
async def on_ready():
    global server_settings
    global birthdays
    global new_startup
    
    current_time_obj = datetime.now()
    today_month = int(current_time_obj.strftime("%m"))
    today_day = int(current_time_obj.strftime("%d"))
 
    
    await log_message("Logged into Discord!")
    if new_startup:
        new_startup = False
        records = await select_sql("""SELECT ServerId,BirthdayChannelId,BirthdayRoleId FROM ServerSettings;""")
        for row in records:
            server_id = int(row[0])
            guild = client.get_guild(server_id)
            server_settings[server_id] = { }
            if row[1] is not None:
                try:
                    bday_channel = guild.get_channel(int(row[1]))
                except:
                    pass
            server_settings[server_id]["BirthdayChannel"] = bday_channel
            if row[2] is not None:
                try:
                    server_settings[server_id]["BirthdayRole"] = discord.utils.get(guild.roles, id=int(row[2]))
                except:
                    pass
            if guild is None:
                
                continue
            for user in guild.members:
                for role in user.roles:
                    try:
                        if role.id == server_settings[guild.id]["BirthdayRole"].id:
                            try:
                                await user.remove_roles(role)
                            except:
                                pass
                    except:
                        pass
            bday_records = await select_sql("""SELECT UserId, BirthMonth, BirthDay FROM Birthdays WHERE ServerId=%s;""",(str(guild.id),))
            for bday_row in bday_records:
                month = int(bday_row[1])
                day = int(bday_row[2])
                member_id = int(bday_row[0])
                try:
                    server = client.get_guild(server_id)
                except:
                    pass
                try:
                    member = discord.utils.get(server.members, id=member_id)
                    await log_message("User " + str(member) + "ID: " + str(member_id))
                    if month == today_month and day == today_day:
                        try:
                            await member.add_roles(server_settings[server_id]["BirthdayRole"])
                        except:
                            pass
                            
                        await server_settings[server_id]["BirthdayChannel"].send(">>> It is " + member.display_name + "'s birthday today. Please wish them a happy birthday!")
                except:
                    pass
        
        
    

@client.event
async def on_guild_join(guild):
    global server_settings
    await log_message("Joined guild " + guild.name + "!")
    server_settings[guild.id] = {} 
    result = await commit_sql("""INSERT INTO ServerSettings (ServerId) VALUES (%s);""",(str(guild.id),))
        

@client.event
async def on_guild_remove(guild):
    await log_message("Left guild " + guild.name + "!")
    

@client.event
async def on_member_join(member):
    await log_message("User " + member.name + " joined guild " + member.guild.name + "!")
    
@client.event
async def on_member_remove(member):
    await log_message("User " + member.name + " left guild " + member.guild.name + "!")

@client.event
async def on_message(message):
    
    if message.author == client.user:
        return
    if message.author.bot:
        return

    username = message.author.display_name
    server_name = message.guild.name
    user_id = message.author.id
    server_id = message.guild.id            
    if message.content.startswith('cake'):


        command_string = message.content.split(' ')
        command = command_string[1]
        parsed_string = message.content.replace("cake " + command,"")
        parsed_string = re.sub(r"^ ","",parsed_string)


        await log_message("Command " + message.content + " called by " + username + " from " + server_name)
        
        if command == 'setbdaychannel':
            if not message.channel_mentions:
                await reply_message(message, "No channel mentioned for birthday announcements!")
                return
                
            server_settings[message.guild.id]["BirthdayChannel"] = message.channel_mentions[0]
            result = await commit_sql("""UPDATE ServerSettings SET BirthdayChannelId=%s WHERE ServerId=%s;""",(str(message.channel_mentions[0].id),(str(message.guild.id))))
            await reply_message(message, "Birthday announcement channel set to " + message.channel_mentions[0].name + "!")
        elif command == 'setbdayrole':
            if not message.role_mentions:
                await reply_message(message, "No role mentioned for birthday recognition!")
                return
            server_settings[message.guild.id]["BirthdayRole"] = message.role_mentions[0]
            result = await commit_sql("""UPDATE ServerSettings SET BirthdayRoleId=%s WHERE ServerId=%s;""",(str(message.role_mentions[0].id),str(message.guild.id)))
            await reply_message(message, "Birthday recognition role set to " + message.role_mentions[0].name + "!")
        elif command == 'mybday':
            if not parsed_string:
                await reply_message(message, "You didn't set a birthday! Please enter your month and day as MM-DD!")
                return
            bday_re = re.compile(r"(?P<month>\d\d)-(?P<day>\d\d)")
            m = bday_re.search(parsed_string)
            if m:
                month = m.group('month')
                day = m.group('day')
            else:
                await reply_message(message, "Invalid date format! Please enter as your month and day as MM-DD!")
                return
            records = await select_sql("""SELECT BirthMonth,BirthDay FROM Birthdays WHERE ServerId=%s AND UserId=%s;""",(str(message.guild.id),str(message.author.id)))
            if not records:
                result = await commit_sql("""INSERT INTO Birthdays (ServerId, UserId, BirthMonth, BirthDay) VALUES (%s, %s, %s, %s);""",(str(message.guild.id),str(message.author.id), str(month), str(day)))
            else:
                result = await commit_sql("""UPDATE Birthdays SET BirthMonth=%s,BirthDay=%s WHERE ServerId=%s AND UserId=%s;""",(str(month),str(day),str(message.guild.id),str(message.author.id)))
            await reply_message(message, "Your birthday has been recorded as " + month + "-" + day + "!")
        elif command == 'deletemybday':
            result = await commit_sql("""DELETE FROM Birthdays WHERE ServerId=%s AND UserId=%s;""",(str(message.guild.id),str(message.author.id)))
            await reply_message(message, "Your birthday has been deleted.")
        elif command == 'listbdays':
            records = await select_sql("""SELECT UserId,BirthMonth,BirthDay FROM Birthdays WHERE ServerId=%s;""",(str(message.guild.id),))
            if not records:
                await reply_message(message,"No birthdays have been recorded!")
                return
            response = "**Server Birthdays**\n\n"
            for row in records:
                month = str(row[1])
                day = str(row[2])
                user_id = str(row[0])
                try:
                    user = message.guild.get_member(int(user_id))
                    response = response + user.display_name + ": " + month + "-" + day + "\n"
                except:
                    pass
            await reply_message(message, response)
        elif command == 'info' or command == 'help':
            response = "**Have Some Cake Help**\n\nHave Some Cake is a Discord birthday bot!\n\n**Commands:\n**`cake setbdaychannel #channel` Set the channel for birthday announcements.\n`cake setbirthdayrole @Role` Set the birthday role for embarrassing people. Must be an existing role below the bot role.\n`cake mybday MM-DD` Set your birthday to month MM and day DD.\n`cake listbdays` See all birthdays on the server.\n`cake deletemybday`: Delete your birthdayb from the server.\n\nBirthdays are announced at midnight GMT."
            await reply_message(message, response)
        if command == 'invite':
            await reply_message(message, "Click here to invite Have Some Cake! https://discord.com/api/oauth2/authorize?client_id=718144819666485260&permissions=268504064&scope=bot")
            
        else:
            pass

        
    
        
client.run('REDACTED')		