import discord
from discord.ext import commands
from discord import Intents
import yt_dlp
import os
import requests
from collections import deque
from dotenv import load_dotenv
import asyncio

# Load environment variables from .env file
load_dotenv()

# Retrieve API key and bot token from environment
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
BOT_TOKEN = os.getenv('BOT_TOKEN')

# yt-dlp options for YouTube and other sites
ytdl_format_options = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'cookiefile': 'youtube_cookies.txt',  # Ensure this file is populated with your YouTube cookies
    'geo_bypass': True,
    'headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',  # Disable video stream
}

# Set up Discord Bot
intents = Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='*', intents=intents, help_command=None)

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

# Function to search YouTube using the YouTube Data API
def search_youtube(song_name):
    search_url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        'part': 'snippet',
        'q': song_name,
        'key': YOUTUBE_API_KEY,
        'type': 'video',
        'maxResults': 1,
    }
    response = requests.get(search_url, params=params)
    search_results = response.json()

    if search_results['items']:
        video_id = search_results['items'][0]['id']['videoId']
        video_title = search_results['items'][0]['snippet']['title']
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        return video_url, video_title
    else:
        return None, None

# Function to play the next song in the queue
async def play_next_song(voice_client):
    if song_queue:
        audio_url, title = song_queue.popleft()
        voice_client.play(discord.FFmpegPCMAudio(audio_url, **ffmpeg_options), 
                          after=lambda e: bot.loop.create_task(play_next_song(voice_client)))
        await bot.get_channel(voice_client.channel.id).send(f"Now playing: {title}")

async def get_audio_url(video_url):
    for _ in range(3):  # Try 3 times
        try:
            info = ytdl.extract_info(video_url, download=False)
            return info['url']
        except Exception as e:
            if "captcha" in str(e).lower():
                await asyncio.sleep(5)  # Wait before retrying
                continue
            else:
                raise e  # Raise other errors immediately
    return None

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.command(name="commands")
async def commands_command(ctx):
    help_message = (
        "Here are the commands you can use:\n"
        "`*play <song name or URL>` - Play a song from YouTube.\n"
        "`*pause` - Pause the currently playing music.\n"
        "`*resume` - Resume paused music.\n"
        "`*skip` - Skip the current song.\n"
        "`*queue` - Show the current song queue.\n"
        "`*join` - Join your current voice channel.\n"
        "`*leave` - Leave the voice channel.\n"
        "`*points` - Check your points and rank."
    )
    await ctx.send(help_message)

@bot.command(name="play")
async def play_command(ctx, *, song_name_or_url):
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

        # If it's a URL, process it directly
        if song_name_or_url.startswith("http://") or song_name_or_url.startswith("https://"):
            video_url, title = song_name_or_url, song_name_or_url  # Use the URL as both title and URL
        else:
            # Use YouTube API to search for the video
            video_url, title = search_youtube(song_name_or_url)
            if video_url is None:
                await ctx.send("No song found with the given keywords.")
                return

        # Extract direct audio stream URL using yt-dlp
        audio_url = await get_audio_url(video_url)
        if audio_url is None:
            await ctx.send("Failed to retrieve audio URL after multiple attempts.")
            return

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
    voice_client = ctx.voice_client
    if voice_client.is_playing():
        voice_client.pause()
        await ctx.send("Paused the music.")
    else:
        await ctx.send("No music is playing.")

@bot.command(name="resume")
async def resume_command(ctx):
    voice_client = ctx.voice_client
    if voice_client.is_paused():
        voice_client.resume()
        await ctx.send("Resumed the music.")
    else:
        await ctx.send("No music is paused.")

@bot.command(name="skip")
async def skip_command(ctx):
    voice_client = ctx.voice_client
    if voice_client.is_playing():
        voice_client.stop()
        await ctx.send("Skipped the song.")
        await play_next_song(voice_client)
    else:
        await ctx.send("No music is playing.")

@bot.command(name="queue")
async def queue_command(ctx):
    if song_queue:
        queue_message = "Current queue:\n"
        for i, (audio_url, title) in enumerate(song_queue):
            queue_message += f"{i+1}. {title}\n"
        await ctx.send(queue_message)
    else:
        await ctx.send("The queue is empty.")

@bot.command(name="join")
async def join_command(ctx):
    if ctx.author.voice is None:
        await ctx.send("You need to be in a voice channel to use this command.")
        return

    voice_channel = ctx.author.voice.channel
    if voice_channel:
        await voice_channel.connect()
        await ctx.send("Joined the voice channel.")

@bot.command(name="leave")
async def leave_command(ctx):
    voice_client = ctx.voice_client
    if voice_client:
        await voice_client.disconnect()
        await ctx.send("Left the voice channel.")
    else:
        await ctx.send("Not connected to a voice channel.")

@bot.command(name="points")
async def points_command(ctx):
    points = user_points.get(ctx.author.id, 0)
    rank = user_ranks.get(ctx.author.id, "Newbie")
    await ctx.send(f"You have {points} points. (Rank: {rank})")

def search_youtube(song_name):
    search_url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        'part': 'snippet',
        'q': song_name,
        'key': YOUTUBE_API_KEY,
        'type': 'video',
        'maxResults': 1,
    }
    response = requests.get(search_url, params=params)

    # Check for errors in the response
    if response.status_code != 200:
        print(f"Error fetching data from YouTube API: {response.status_code} - {response.text}")
        return None, None

    search_results = response.json()

    if search_results.get('items'):
        video_id = search_results['items'][0]['id']['videoId']
        video_title = search_results['items'][0]['snippet']['title']
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        return video_url, video_title
    else:
        print("No results found for the query.")
        return None, None

# Run the bot
bot.run(BOT_TOKEN)
