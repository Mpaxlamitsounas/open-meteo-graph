#!./bin/python

import openmeteo_requests
from openmeteo_sdk.WeatherApiResponse import WeatherApiResponse
import requests_cache
from retry_requests import retry
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from datetime import datetime
from datetime import timedelta
import numpy as np
from numpy import ndarray

url = "https://api.open-meteo.com/v1/forecast"

params = [{
    "latitude": 34.3434,
    "longitude": -4.44,
    "hourly": "temperature_2m",
    "timezone": "auto",
    "past_days": 1,
    "forecast_days": 3
}, {
    "latitude": 2.22,
    "longitude": 11.1111,
    "hourly": "temperature_2m",
    "timezone": "auto",
    "past_days": 1,
    "forecast_days": 3
}]
location_names = ["Example 1", "Example 2"]
colours = ["#2caffe", "#ffa808"]


def get_data(params) -> WeatherApiResponse:
    cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)
    return openmeteo.weather_api(url, params=params)[0]


def get_offset_time(now_dec: float) -> int:
    if now_dec < 4:
        return 10
    elif now_dec < 16:
        return 24
    else:
        return 24 + 10


def make_x_ticks(offset: int) -> list[str]:
    return [(datetime.today() + timedelta(days=-1, hours=hour)).strftime('%d %b') if hour % 24 == 0
            else f'{hour % 24}:00' if hour % 2 == 0
            else ''
            for hour in range(offset, hours + offset)]


def get_temp(response: WeatherApiResponse, offset: int) -> list[float]:
    return [temp for temp in response.Hourly().Variables(0).ValuesAsNumpy()][offset:hours + offset]  # type: ignore


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
    plt.style.use('dark_background')
    mpl.rcParams['axes.spines.left'] = False
    mpl.rcParams['axes.spines.top'] = False
    mpl.rcParams['axes.spines.right'] = False
    mpl.rcParams['toolbar'] = 'None'
    return plt.figure(f'{hours - 1}h temperature', figsize=(12, 4))


hours = 34 + 1

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

for i in range(min(len(params), len(location_names))):

    response = get_data(params[i])

    y_temp = get_temp(response, offset)
    tick_spacing = max(tick_spacing, get_y_tick_spacing(y_temp))
    low_lim = min(low_lim, round_with_precision(min(y_temp), tick_spacing))
    high_lim = max(high_lim, round_with_precision(max(y_temp), tick_spacing) + tick_spacing)

    plt.plot(x_time,
             y_temp,
             color=colours[i],
             marker='o',
             linewidth=1,
             label=location_names[i])

y_ticks = make_y_ticks(low_lim, high_lim, tick_spacing)
high_lim += 0.001 * tick_spacing

plt.axvline(now_dec + 24 if (offset != 0 and now_dec < 24)else now_dec,
            color='#646464',
            marker='|',
            linewidth=1)

plt.grid(True, axis='y', alpha=0.5)
fig.axes[0].tick_params(left=False)

plt.xlim([offset - 0.25, offset + hours - 1 + 0.25])
plt.xticks(x_ticks, x_tick_labels)

plt.ylim([low_lim, high_lim])
plt.yticks(y_ticks)
plt.ylabel('°C')

plt.legend()
plt.tight_layout()
plt.show()
