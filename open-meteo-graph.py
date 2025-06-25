import json
from datetime import datetime, timedelta
from json import JSONDecodeError

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import openmeteo_requests
import requests_cache
from matplotlib.figure import Figure
from numpy import ndarray
from openmeteo_sdk.WeatherApiResponse import WeatherApiResponse
from retry_requests import retry

url = "https://api.open-meteo.com/v1/forecast"

hourly_metrics = "temperature_2m"
timezone = "auto"
past_days = 1
forecast_days = 3


def create_config():
    with open("./entries.txt", "wt") as file:
        # noinspection PyTypeChecker
        json.dump(
            [
                {
                    "name": "Example 1",
                    "colour": "#2caffe",
                    "params": {"latitude": 34.3434, "longitude": -4.44},
                },
                {
                    "name": "Example 2",
                    "colour": "#ffa808",
                    "params": {"latitude": 2.22, "longitude": 11.1111},
                },
                {
                    "name": "Example 3",
                    "colour": "#35b035",
                    "params": {"latitude": 1.234, "longitude": -4.321},
                },
            ],
            file,
            indent=4,
        )
        print("Created entries file.")


def load_config():
    try:
        with open("./entries.txt", "rt") as file:
            entries = json.load(file)
            if not all(
                [
                    entry["name"]
                    and entry["colour"]
                    and entry["params"]["latitude"]
                    and entry["params"]["longitude"]
                    for entry in entries
                ]
            ):
                raise SyntaxError

            return entries

    except (FileExistsError, JSONDecodeError, SyntaxError):
        create_config()
        exit(1)


entries = load_config()

for entry in entries:
    entry["params"]["hourly"] = hourly_metrics
    entry["params"]["timezone"] = timezone
    entry["params"]["past_days"] = past_days
    entry["params"]["forecast_days"] = forecast_days


def get_data(entries) -> WeatherApiResponse:
    cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)
    return openmeteo.weather_api(url, params=entries["params"])[0]


def get_offset_time(now_dec: float) -> int:
    if now_dec < 4:
        return 10
    elif now_dec < 16:
        return 24
    else:
        return 24 + 10


hours = 34 + 1


def make_x_ticks(offset: int) -> list[str]:
    return [
        (
            (datetime.today() + timedelta(days=-1, hours=hour)).strftime("%d %b")
            if hour % 24 == 0
            else f"{hour % 24}:00" if hour % 2 == 0 else ""
        )
        for hour in range(offset, hours + offset)
    ]


def get_temp(response: WeatherApiResponse, offset: int) -> list[float]:
    return [temp for temp in response.Hourly().Variables(0).ValuesAsNumpy()][
        offset : hours + offset
    ]  # type: ignore


def get_y_tick_spacing(temp: list[float]) -> float:
    spacings = [1, 2, 5, 10]
    spacing_idx = 0
    tick_spacing = 1
    while (max(temp) - min(temp)) / tick_spacing > 8:
        spacing_idx += 1
        tick_spacing = spacings[spacing_idx]

    return tick_spacing


def round_with_precision(num: float, precision: float) -> float:
    return precision * (num // precision)


def make_y_ticks(low: float, high: float, step: float) -> ndarray:
    return np.arange(low, high + step, step)


def init_figure() -> Figure:
    plt.style.use("dark_background")
    mpl.rcParams["axes.spines.left"] = False
    mpl.rcParams["axes.spines.top"] = False
    mpl.rcParams["axes.spines.right"] = False
    mpl.rcParams["toolbar"] = "None"
    return plt.figure(f"{hours - 1}h temperature", figsize=(12, 4))


now = datetime.today()
now_dec = now.hour + now.minute / 60
offset = get_offset_time(now_dec)

x_time = range(offset, hours + offset)
x_ticks = range(offset, hours + offset)
x_tick_labels = make_x_ticks(offset)

fig = init_figure()
tick_spacing = 0
low_lim = 10000  # if your location exceeds this you have bigger problems
high_lim = -10000

for entry in entries:
    response = get_data(entry)

    y_temp = get_temp(response, offset)
    tick_spacing = max(tick_spacing, get_y_tick_spacing(y_temp))
    low_lim = min(low_lim, round_with_precision(min(y_temp), tick_spacing))
    high_lim = max(
        high_lim, round_with_precision(max(y_temp), tick_spacing) + tick_spacing
    )

    plt.plot(
        x_time,
        y_temp,
        color=entry["colour"],
        marker="o",
        linewidth=1,
        label=entry["name"],
    )

y_ticks = make_y_ticks(low_lim, high_lim, tick_spacing)
high_lim += 0.001 * tick_spacing

plt.axvline(
    now_dec + 24 if (offset != 0 and now_dec < 24) else now_dec,
    color="#646464",
    marker="|",
    linewidth=1,
)

plt.grid(True, axis="y", alpha=0.5)
fig.axes[0].tick_params(left=False)

plt.xlim([offset - 0.25, offset + hours - 1 + 0.25])
plt.xticks(x_ticks, x_tick_labels)

plt.ylim([low_lim, high_lim])
plt.yticks(y_ticks)
plt.ylabel("°C")

plt.legend()
plt.tight_layout()
plt.show()
