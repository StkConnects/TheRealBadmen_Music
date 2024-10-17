import discord
from discord.ext import commands
from discord import Intents
import yt_dlp
import os
from collections import deque

from googleapiclient.discovery import build
from dotenv import load_dotenv
import subprocess
import urllib.request

# Load environment variables from .env file
load_dotenv()

# Retrieve API key and bot token from environment
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Ensure ffmpeg is installed
def check_ffmpeg():
    try:
        subprocess.run(['ffmpeg', '-version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        print("FFmpeg is not installed. Please install FFmpeg manually.")
        raise

check_ffmpeg()

ytdl_format_options = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'cookiefile': 'youtube_cookies.txt',  # Path to your cookies file
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

# Set up yt_dlp options
ytdl_format_options = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',  # Disable video stream
    'executable': 'ffmpeg',  # Assume ffmpeg is already installed and in the PATH
}

# Set up Discord Bot
intents = Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='*', intents=intents)

# Create a queue to hold songs
song_queue = deque()

# Points system and user ranks
user_points = {}
user_ranks = {}

# Helper function to update rank based on points
def update_rank(user_id):
    points = user_points.get(user_id, 0)
    if points >= 500:
        user_ranks[user_id] = 'Diamond'
    elif points >= 400:
        user_ranks[user_id] = 'Platinum'
    elif points >= 300:
        user_ranks[user_id] = 'Gold'
    elif points >= 200:
        user_ranks[user_id] = 'Silver'
    elif points >= 100:
        user_ranks[user_id] = 'Bronze'
    elif points >= 50:
        user_ranks[user_id] = 'Iron'
    else:
        user_ranks[user_id] = 'Newbie'

# Check if user has "Ender" rank
def has_ender_rank(user_id):
    return user_ranks.get(user_id) == 'Ender'

# Set up the password for granting the "Ender" and "Adventurer" ranks
ENDER_PASSWORD = 'Real&Bad&Men&Grant'
ADVENTURER_PASSWORD = 'Adventurer&Access'

# Grant "Ender" and "Adventurer" ranks only with password
@bot.command(name="grant")
async def grant_command(ctx, rank: str, user: discord.Member, password: str):
    if password == ENDER_PASSWORD:
        if rank.lower() == "ender":
            user_ranks[user.id] = 'Ender'
            await ctx.send(f"Granted 'Ender' rank to {user.mention}")
        else:
            await ctx.send(f"Rank '{rank}' not recognized.")
    elif password == ADVENTURER_PASSWORD:
        if rank.lower() == "adventurer":
            user_ranks[user.id] = 'Adventurer'
            await ctx.send(f"Granted 'Adventurer' rank to {user.mention}")
        else:
            await ctx.send(f"Rank '{rank}' not recognized.")
    else:
        await ctx.send("Incorrect password.")

# Function to play next song
async def play_next_song(voice_client):
    """Play the next song in the queue."""
    if song_queue:
        audio_url, title = song_queue.popleft()
        voice_client.play(discord.FFmpegPCMAudio(audio_url, **ffmpeg_options), 
                          after=lambda e: bot.loop.create_task(play_next_song(voice_client)))
        await bot.get_channel(voice_client.channel.id).send(f"Now playing: {title}")

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.event
async def on_member_join(member):
    """Automatically grant 'Adventurer' rank when someone joins the server."""
    user_ranks[member.id] = 'Adventurer'
    await member.send(f"Welcome to the server! You have been granted the 'Adventurer' rank.")
    await member.guild.get_channel(member.guild.system_channel.id).send(f"Welcome {member.mention}! {member.name} is now an Adventurer.")

@bot.command(name="commands_help")
async def help_command(ctx):
    """Provides a list of commands and their descriptions."""
    help_message = (
        "**Available Commands:**\n"
        "`*join` - Join the voice channel.\n"
        "`*leave` - Leave the voice channel.\n"
        "`*play <song_name>` - Play a song from YouTube.\n"
        "`*pause` - Pause the currently playing song.\n"
        "`*resume` - Resume the paused song.\n"
        "`*skip` - Skip the currently playing song.\n"
        "`*stop` - Stop the music and clear the queue.\n"
        "`*volume <0-100>` - Set the volume (default is 50).\n"
        "`*loop` - Toggle looping the current song.\n"
        "`*queue` - Show the current song queue.\n"
        "`*commands_help` - Show this help message.\n"
        "`/grant ender <user> <password>` - Grant the 'Ender' rank to a user (requires password).\n"
        "`/grant adventurer <user> <password>` - Grant the 'Adventurer' rank to a user (requires password).\n"
        "`*rank` - Show your current rank and points."
    )
    await ctx.send(help_message)

@bot.command(name="rank")
async def rank_command(ctx):
    """Show the user's current rank and points."""
    user_id = ctx.author.id
    points = user_points.get(user_id, 0)
    rank = user_ranks.get(user_id, 'Newbie')
    await ctx.send(f"{ctx.author.mention}, you currently have {points} points and your rank is '{rank}'.")

@bot.command(name="play")
async def play_command(ctx, *, song_name):
    try:
        voice_channel = ctx.author.voice.channel
        if not voice_channel:
            await ctx.send("You need to be in a voice channel to play music.")
            return

        # Connect to the voice channel if not already connected
        if ctx.voice_client is None:
            voice_client = await voice_channel.connect()
        else:
            voice_client = ctx.voice_client

        # Use YouTube Data API to search for the video
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        request = youtube.search().list(
            part="snippet",
            maxResults=1,
            q=song_name
        )
        response = request.execute()
        if response['items']:
            video_id = response['items'][0]['id']['videoId']
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            title = response['items'][0]['snippet']['title']
        else:
            await ctx.send("No song found with the given keywords.")
            return

        # Extract direct audio stream URL using yt-dlp
        info = ytdl.extract_info(video_url, download=False)
        audio_url = info['url']

        # Add the song to the queue
        song_queue.append((audio_url, title))
        await ctx.send(f"Added to queue: {title}")

        # Play the song if it's the only one in the queue
        if len(song_queue) == 1:
            await play_next_song(voice_client)

        # Give points to the user (10 points per song)
        user_points[ctx.author.id] = user_points.get(ctx.author.id, 0) + 10
        update_rank(ctx.author.id)
        await ctx.send(f"You've earned 10 points! Total points: {user_points[ctx.author.id]} (Rank: {user_ranks[ctx.author.id]})")

    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.command(name="pause")
async def pause_command(ctx):
    """Pause the currently playing song."""
    voice_client = ctx.voice_client
    if voice_client.is_playing():
        voice_client.pause()
        await ctx.send("Paused the music.")
    else:
        await ctx.send("No music is playing.")

@bot.command(name="resume")
async def resume_command(ctx):
    """Resume the paused song."""
    voice_client = ctx.voice_client
    if voice_client.is_paused():
        voice_client.resume()
        await ctx.send("Resumed the music.")
    else:
        await ctx.send("No music is paused.")

@bot.command(name="skip")
async def skip_command(ctx):
    """Skip the currently playing song."""
    voice_client = ctx.voice_client
    if voice_client.is_playing():
        voice_client.stop()
        await ctx.send("Skipped the song.")
        await play_next_song(voice_client)
    else:
        await ctx.send("No music is playing.")

@bot.command(name="loop")
async def loop_command(ctx):
    """Toggle looping the current song."""
    voice_client = ctx.voice_client
    if voice_client.is_playing():
        voice_client.source.loop = not voice_client.source.loop
        await ctx.send("Toggled looping.")
    else:
        await ctx.send("No music is playing.")

@bot.command(name="queue")
async def queue_command(ctx):
    """Show the current song queue."""
    if song_queue:
        queue_message = "Current queue:\n"
        for i, (audio_url, title) in enumerate(song_queue):
            queue_message += f"{i+1}. {title}\n"
        await ctx.send(queue_message)
    else:
        await ctx.send("The queue is empty.")

@bot.command(name="join")
async def join_command(ctx):
    """Join the voice channel."""
    if ctx.author.voice is None:
        await ctx.send("You need to be in a voice channel to use this command.")
        return

    voice_channel = ctx.author.voice.channel
    if voice_channel:
        await voice_channel.connect()
        await ctx.send("Joined the voice channel.")

@bot.command(name="leave")
async def leave_command(ctx):
    """Leave the voice channel."""
    voice_client = ctx.voice_client
    if voice_client:
        await voice_client.disconnect()
        await ctx.send("Left the voice channel.")
    else:
        await ctx.send("Not connected to a voice channel.")

# Run the bot
bot.run(BOT_TOKEN)

