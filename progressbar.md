# Custom Progress Bars

The bot's song embed includes a small, self-updating progress bar.

By default, it uses ASCII characters:

![Default ASCII progress bar](https://x02.me/u/73W6.png)

You can replace it with Discord emotes and even create different progress bars for different cover artists:

![Custom emote progress bar](https://x02.me/u/A2WJWS.png)

The example emotes are included in the `progressbar_resources` folder.


---

## Setup

### 1. Upload the emotes

Upload your progress bar emotes to the Discord Developer Portal (recommended).

You will need the IDs/markdown of the uploaded emotes for the configuration file.

### 2. Create the configuration


Create:

```text
data/progressbar.json
```
>The `data` folder is created automatically when you start the bot for the first time.



A basic configuration for the included progress bar:

```json
{
  "default": {
    "start": {
      "0": "<:start_empty:EMOTE_ID>",
      "1": "<:start_half:EMOTE_ID>",
      "100": "<:start_full:EMOTE_ID>"
    },
    "middle": {
      "0": "<:mid_empty:EMOTE_ID>",
      "50": "<:mid_half:EMOTE_ID>",
      "100": "<:mid_full:EMOTE_ID>"
    },
    "end": {
      "0": "<:end_empty:EMOTE_ID>",
      "50": "<:end_half:EMOTE_ID>",
      "98": "<:end_full:EMOTE_ID>"
    }
  }
}
```

Replace each `EMOTE_ID` with the corresponding emote ID from the Discord Developer Portal.

Save the file and **restart the bot**.

---

# Configuration

## Progress bar segments

A progress bar is built from three types of segments:

```text
[start][middle][middle][middle][end]
```

`start` and `end` are optional, if either is missing, `middle` is used instead.

The length (number of segments) is defined in `config.py` as `PROGRESSBAR_LENGTH`

---

## Percentage mappings

Each entry maps a percentage to an emote:

```json
"50": "<:mid_half:EMOTE_ID>"
```

This percentage represents **how full that individual segment is** (not the overall progress of the song).

The bot selects the highest configured percentage that is **less than or equal to** the segment's current progress.

For example:

```json
"middle": {
  "0": "empty",
  "30": "half",
  "60": "full"
}
```

maps to:

| Segment progress | Selected emote |
|---:|---|
| `0%` – `29%` | `empty` |
| `30%` – `59%` | `half` |
| `60%` – `100%` | `full` |

You can define as many percentage levels as you need.
The system uses the highest defined value to render fully completed segments, and the lowest defined value for upcoming empty segments

---

## Cover artist-specific bars

The `default` configuration is used whenever the bot cannot find a configuration matching the song's cover artist.

> **It is recommended to always define `default`**, even if you create custom progress bars for every cover artist.

Artist-specific configurations act as overrides.

For example:

```json
{
  "default": {
    ...
  },
  "Neuro": {
    ...
  },
  "Evil": {
    ...
  },
  "Twins": {
    ...
  }
}
```

For the complete list of supported cover artists, see the `CoverBy` enum in `utils.py`.

---

## Why does `start` use `1` instead of `50`?

The `start` segment represents the very beginning of the progress bar.

If its second state required `50%` progress, the beginning of the bar could remain completely empty for a noticeable amount of time after the song starts.

Using a low threshold such as `1%` makes the bar feel more natural:

```text
0%      → nothing has started
1%+     → playback has started
```

This means the completely empty state represents **no playback yet**

---

## Why does `end` use `98` instead of `100`?

This is primarily to avoid floating-point precision issues.

The audio progress is calculated using the exact audio frames, while the Discord embed only refreshes up to the exact second of the song's length.
This means the calculated song progress may never reach exactly `100%` if the song plays for a few milliseconds after the duration in seconds is displayed

As a result `"100": "<:end_full:EMOTE_ID>"` may never be selected.

Using `"98": "<:end_full:EMOTE_ID>"` ensures that the final segment reliably reaches its full state.

If you don't define an `end` segment, it is recommended to use `98` as the highest percentage in `middle` instead

---

# ASCII Progress Bar

The same configuration system can be used to recreate the original ASCII progress bar **without changing any Python code**.
(for example, if you want to change the progress symbol)

Example:

```json
{
  "default": {
    "middle": {
      "0": "▬",
      "0.1": "█",
      "101": "▬"
    }
  }
}
```

This works by taking advantage of the percentage matching described above.

- `0` → show `▬` when the segment has no progress.
- `0.1` → switch to `█` almost immediately after progress begins.
- `101` → switch back to `▬` only for the full segments after the playback marker

The result behaves essentially like the original ASCII progress bar
