# Discord Music Bot

A Discord music bot that allows users to play music from YouTube, manage a queue, and grant ranks based on points.

## Setup Instructions

1. Clone the repository.
2. Install dependencies: `pip install -r requirements.txt`
3. Create a `.env` file and add your YouTube API key and Discord Bot Token:
    ```
    YOUTUBE_API_KEY=your_youtube_api_key
    BOT_TOKEN=your_discord_bot_token
    ```
4. Run the bot locally: `python bot.py`
5. For deployment, you can use Render. 

## Commands

- `*play <song>` - Play a song from YouTube.
- `*pause` - Pause the song.
- `*resume` - Resume the song.
- `*skip` - Skip the current song.
- `*loop` - Toggle looping the current song.
- `*queue` - View the current song queue.
- `/grant <rank> <user> <password>` - Grant a user a specific rank (`Adventurer` or `Ender`) using the password.
