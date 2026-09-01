import json
import logging
import datetime
import asyncio
import weakref
import discord

import player
import stats
import utils

log = logging.getLogger()
# progressbar lenght
pg_lenght = 12
progressbar_data: dict = None


class EmbedEx(discord.Embed):
    def __init__(
        self,
        *,
        colour=None,
        color=None,
        title=None,
        type="rich",
        url=None,
        description=None,
        timestamp=None,
    ):
        super().__init__(
            colour=colour,
            color=color,
            title=title,
            type=type,
            url=url,
            description=description,
            timestamp=timestamp,
        )
        self.progressbar_pos: int | None = None


def get_song_embed(
    guild_id: int,
    song: player.Song,
    last_section: str | None = None,
    cover_art: str | discord.File = None,
    footer: str = None,
    show_progressbar=False,
) -> EmbedEx:

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

        bar = get_progressbar((duration - remaining) / duration, pg_lenght, song.cover_by())
        progressbar_pos = sum(len(text) for text in description_lines) + len(description_lines)
        if len(bar) == pg_lenght:
            description_lines.append(f"`{pminutes}:{pseconds:02} {bar} {minutes}:{seconds:02}`")
        else:
            description_lines.append(f"`{pminutes}:{pseconds:02}` {bar} `{minutes}:{seconds:02}`")
    else:
        description_lines.append(f"Duration: {minutes}:{seconds:02}")
        progressbar_pos = None

    description_lines.append(f"{play_count} plays    {req_count} requests")
    if last_section:
        description_lines.append(f"\n{last_section}")
    description = "\n".join(description_lines)
    embed = EmbedEx(title=song_name, description=description, color=color, url=song_url)
    embed.progressbar_pos = progressbar_pos
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
    song_ref: weakref.ReferenceType[player.Song], msg: discord.Message, embed: EmbedEx
):
    progressbar_start = embed.progressbar_pos
    if progressbar_start is None:
        return
    line_end = embed.description.find("\n", progressbar_start + 5)
    if line_end == -1:
        return
    line_end = embed.description.rfind(" ", progressbar_start, line_end)
    if line_end == -1:
        return
    description_end = embed.description[line_end:]
    duration = song_ref().duration
    if duration is None or duration == 0:
        return
    for _ in range(1100):
        await asyncio.sleep(1.6)
        if (song := song_ref()) is not None:
            remaining = song.remaining()
        else:
            return
        if remaining is None:
            return
        pminutes, pseconds = divmod(round(duration - remaining), 60)
        bar = get_progressbar((duration - remaining) / duration, pg_lenght, song.cover_by())
        song = None
        if len(bar) == pg_lenght:
            embed.description = f"{embed.description[:progressbar_start]}`{pminutes}:{pseconds:02} {bar}{description_end}"
        else:
            embed.description = f"{embed.description[:progressbar_start]}`{pminutes}:{pseconds:02}` {bar}{description_end}"
        try:
            await msg.edit(embed=embed)
        except discord.NotFound:
            return
        if remaining <= 0:
            return


def get_progressbar(percent: float, lenght: int, cover_by=utils.CoverBy.Unknown):
    position = max(0, min(int(lenght * percent), lenght - 1))
    pb_data = progressbar_data.get("default")
    if cover_by.name in progressbar_data:
        pb_data = progressbar_data[cover_by.name]
    else:
        pb_data = progressbar_data.get("default")
    try:
        segments = []
        get_full = lambda a: max(pb_data.get(a), key=lambda x: x["percent"])
        get_empty = lambda a: min(pb_data.get(a), key=lambda x: x["percent"])
        get_specific = lambda a, b: max(
            (item for item in pb_data.get(a) if item["percent"] / 100 <= b),
            key=lambda x: x["percent"],
        )
        if position == 0 and "start" in pb_data:
            result = get_specific("start", percent)
            segments.append(result["emote"])
            middle_empty = get_empty("middle")
            if "end" in pb_data:
                segments.extend(middle_empty["emote"] * (lenght - 2))
                end_empty = get_empty("end")
                segments.append(end_empty["emote"])
            else:
                segments.extend(middle_empty["emote"] * (lenght - 1))
        elif position == lenght - 1 and "end" in pb_data:
            if "start" in pb_data:
                segments.append(get_full("start")["emote"])
            to_fill = lenght - 1 - len(segments)
            middle_full = get_full("middle")
            segments.extend(middle_full["emote"] * to_fill)
            tile_percent = percent * lenght - position
            result = get_specific("end", tile_percent)
            segments.append(result["emote"])
        else:
            if "start" in pb_data:
                segments.append(get_full("start")["emote"])
            to_fill = position - len(segments)
            segments.extend(get_full("middle")["emote"] * to_fill)
            tile_percent = percent * lenght - position
            result = get_specific("middle", tile_percent)
            segments.append(result["emote"])
            middle_empty = get_empty("middle")
            if "end" in pb_data:
                segments.extend(middle_empty["emote"] * (lenght - position - 2))
                end_empty = get_empty("end")
                segments.append(end_empty["emote"])
            else:
                segments.extend(middle_empty["emote"] * (lenght - position - 1))
        return "".join(segments)
    except FileNotFoundError:
        pass
    except Exception:
        log.exception("")
    segments = ["▬"] * lenght
    position = max(0, min(int(lenght * percent), lenght - 1))
    segments[position] = "🔘"
    return "".join(segments)


def load(filename: str = None):
    global progressbar_data
    try:
        with open(filename) as f:
            progressbar_data = json.load(f)
    except FileNotFoundError:
        print(f"Progressbar configuration not found ({filename})")
    except Exception as e:
        print(e)