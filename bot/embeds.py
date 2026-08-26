import enum
import logging
import datetime
import asyncio
import weakref
import discord

import player
import stats
import utils

log = logging.getLogger()


def get_song_embed(
    guild_id: int,
    song: player.Song,
    last_section: str | None = None,
    cover_art: str | discord.File = None,
    footer: str = None,
    show_progressbar=False,
) -> discord.Embed:

    original_by = song.original_artists
    date = song.song_info.get("streamDate")
    if not date:
        date = song.song_info.get("karaokeDate")
    if date:
        date = datetime.datetime.fromisoformat(date).strftime("%B %d, %Y")
    duration = song.duration or 0
    minutes, seconds = divmod(round(duration), 60)
    song_url = song.get_url()
    cover_str = song.cover_artists
    color = utils.color_for_cover_artist(cover_str)
    song_data = stats.get_songs_cache(guild_id).get(song.get_id(), {})
    play_count = song_data.get(stats.DataType.SongCount, 0)
    req_count = song_data.get(stats.DataType.Request, 0)
    song_name = song.song_name()
    description_lines = []
    if cover_str:
        description_lines = [f"Cover by {cover_str}\n"]
    description_lines.append(f"Original by {original_by}\n")
    if date:
        description_lines.append(f"Stream date: {date}")
    remaining = song.remaining()
    if show_progressbar and remaining is not None and duration != 0:
        pminutes, pseconds = divmod(round(duration - remaining), 60)
        bar = get_progressbar((duration - remaining) / duration, 10)
        description_lines.append(f"`{pminutes}:{pseconds:02} {bar} {minutes}:{seconds:02}`")
    else:
        description_lines.append(f"Duration: {minutes}:{seconds:02}")

    description_lines.append(f"{play_count} plays    {req_count} requests")
    if last_section:
        description_lines.append(f"\n{last_section}")
    description = "\n".join(description_lines)
    embed = discord.Embed(title=song_name, description=description, color=color, url=song_url)
    embed.set_footer(text=footer)
    if cover_art:
        if type(cover_art) is str:
            embed.set_thumbnail(url=cover_art)
        elif type(cover_art) is discord.File:
            embed.set_thumbnail(url=cover_art.uri)
        else:
            log.error(f"get_song_embed: got unknown data type for song cover: {type(cover_art)}")
    return embed


def get_radio_embed(
    radio: player.Radio, last_section: str | None = None, footer: str = None
) -> discord.Embed:
    embed = discord.Embed(
        title=radio.name(), description=last_section, color=radio.color(), url=radio.get_url()
    )
    embed.set_thumbnail(url=radio.logo_url())
    embed.set_footer(text=footer)
    return embed


async def update_embed(
    song_ref: weakref.ReferenceType[player.Song], msg: discord.Message, embed: discord.Embed
):
    symbol = embed.description.rfind("🔘")
    line_start = embed.description.rfind("\n", 0, symbol)
    if line_start == -1:
        return
    line_end = embed.description.rfind("▬")
    if line_end == -1:
        return
    if symbol > line_end:
        line_end = symbol
    description_end = embed.description[line_end + 1 :]
    duration = song_ref().duration
    for _ in range(1100):
        await asyncio.sleep(1.6)
        if (song := song_ref()) is not None:
            remaining = song.remaining()
            song = None
        else:
            return
        if remaining is None:
            return
        pminutes, pseconds = divmod(round(duration - remaining), 60)
        bar = get_progressbar((duration - remaining) / duration, 10)
        embed.description = (
            f"{embed.description[:line_start]}\n`{pminutes}:{pseconds:02} {bar}{description_end}"
        )
        try:
            await msg.edit(embed=embed)
        except discord.NotFound:
            return
        if remaining <= 0:
            return


def get_progressbar(percent: float, lenght: int):
    segments = ["▬"] * lenght
    position = max(0, min(int(lenght * percent), lenght - 1))
    segments[position] = "🔘"
    return "".join(segments)
