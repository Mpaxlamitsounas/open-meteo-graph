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
params = {
    "latitude": 0.0,
    "longitude": 0.0,
    "hourly": "temperature_2m",
    "timezone": "auto",
    "forecast_days": 2
}


def get_data() -> WeatherApiResponse:
    cache_session = requests_cache.CachedSession('.cache', expire_after=82800)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)
    return openmeteo.weather_api(url, params=params)[0]


def print_header(response: WeatherApiResponse):
    print(f"Coordinates {response.Latitude()}°N {response.Longitude()}°E")
    print(f"Timezone {response.Timezone()} {response.TimezoneAbbreviation()}")


def get_offset_time(now_dec: float) -> int:
    if now_dec >= 16:
        return 16
    else:
        return 0


def make_x_ticks(offset: int) -> list[str]:
    return [(datetime.today() + timedelta(hours=hour)).strftime('%d %b') if hour % 24 == 0
            else str(hour % 24) + ':00' if hour % 2 == 0
            else ''
            for hour in range(offset, 25 + offset)]


def get_temp(response: WeatherApiResponse, offset: int) -> list[float]:
    return [temp for temp in response.Hourly().Variables(0).ValuesAsNumpy()][offset:25 + offset] # type: ignore


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
    return plt.figure('24h temperature', figsize=(12, 4))


response = get_data()
print_header(response)

now = datetime.today()
now_dec = now.hour + now.minute / 60
offset = get_offset_time(now_dec)

x_time = range(offset, 25 + offset)
x_ticks = range(offset, 25 + offset)
x_tick_labels = make_x_ticks(offset)

y_temp = get_temp(response, offset)
tick_spacing = get_y_tick_spacing(y_temp)
low_lim = round_with_precision(min(y_temp), tick_spacing)
high_lim = round_with_precision(max(y_temp), tick_spacing) + tick_spacing
y_ticks = make_y_ticks(low_lim, high_lim, tick_spacing)
high_lim += 0.001 * tick_spacing

fig = init_figure()
plt.plot(
    x_time,
    y_temp,
    color='#2caffe',
    marker='o',
    linewidth=1,
    label='Temperature')
plt.axvline(now_dec, color='#646464', marker='|', linewidth=1)

plt.grid(True, axis='y', alpha=0.5)
fig.axes[0].tick_params(left=False)

plt.xlim([offset - 0.25, offset + 24.25])
plt.xticks(x_ticks, x_tick_labels)

plt.ylim([low_lim, high_lim])
plt.yticks(y_ticks)
plt.ylabel('°C')

plt.legend(loc='upper right')
plt.tight_layout()
plt.show()
