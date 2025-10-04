from abc import abstractmethod, ABC
from dataclasses import dataclass
from typing import Optional
from functools import wraps
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import subprocess
import configparser
import os
import requests
import xarray as xr


#################
# Logging Setup #
#################
logger = logging.getLogger("timing_logger")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler("./logs/timing.txt", maxBytes=1024**2, backupCount=5)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


# Decorator to time a function and log the duration
def log_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = datetime.now()
        result = func(*args, **kwargs)
        end_time = datetime.now()
        elapsed = end_time - start_time
        logger.info(
            f"Function '{func.__qualname__}' took {elapsed} seconds to complete."
        )
        return result

    return wrapper


##########################
# Data Reading Utilities #
##########################


@dataclass
class Credentials:
    host: str
    user: str
    password: str


def download_file(url: str, output_dir: str) -> None:
    header = {
        "User-Agent": "Mozilla/5.0",
        "Cookie": "JSESSIONID=EE6CC73E2F0E8EBB9B9B9E61488A4BC0; _shibsession_64656661756c7468747470733a2f2f736d6f732d646973732e656f2e6573612e696e742f73686962626f6c657468=_7ca12c9c7d87c4c73c17a68dafeaaa2d; _saml_idp=ZW9pYW0taWRwLmVvLmVzYS5pbnQ%3D",
    }

    try:
        r = requests.get(url=url, headers=header)
        with open(output_dir, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    except subprocess.CalledProcessError as e:
        print("Download failed:", e)
        print(e.stderr)


###############################
# Dataset Representation Code #
###############################

class DataSet(ABC):
    INPUT_UNIT: str
    OUTPUT_UNIT: str

    @abstractmethod
    @log_time
    def get_all(
        self, coordinates: list[tuple[float, float]], time: datetime
    ) -> list[float]:
        """Returns a list corresponding to the data value at each input coordinate"""
        pass


####################
# Moisture DataSet #
####################

def get_ftp_credentials(service: str) -> Credentials:
    config = configparser.ConfigParser()
    home_dir = os.path.expanduser("~")
    config.read(os.path.join(home_dir, ".api_credentials.ini"))

    ftp_config = config[service]
    return Credentials(
        host=ftp_config["host"],
        user=ftp_config["user"],
        password=ftp_config["password"],
    )


class Moisture(DataSet):
    DIR = "./data_sets/moisture/"
    URL_PREFIX = "https://smos-diss.eo.esa.int/oads/data/NRT_Open/W_XX-ESA,SMOS,NRTNN_C_LEMM_"

    @log_time
    def get_all(
        self, coordinates: list[tuple[float, float]], time: datetime
    ) -> list[float]:
        """Will attempt to retrieve data from within the same day as the provided time"""
        expected_filepath = os.path.join(
            self.DIR, f"moisture_{time.strftime('%Y_%m_%d')}.nc"
        )

        if (
            not os.path.exists(expected_filepath)
            or os.stat(expected_filepath).st_size == 0
        ):
            # Download the file if it cannot be found locally
            with open(os.path.join(self.DIR, f"moisture_urls.txt"), "r") as f:
                for line in f:
                    if line.strip().__contains__(self.URL_PREFIX + time.strftime("%Y%m%d")):
                        url = line.strip()
                        download_file(url, expected_filepath)
                        break
        
        with xr.open_dataset(expected_filepath) as ds:            
            data = xr.DataArray()
            lats = xr.DataArray([p[0] for p in coordinates], dims="points")
            lons = xr.DataArray([p[1] for p in coordinates], dims="points")

            # Interpolate soil moisture to all points at once
            moisture_interp = ds['soil_moisture'].interp(latitude=lats, longitude=lons)

        print(moisture_interp)
        return moisture_interp


class FuelData(DataSet):
    pass


class Wind(DataSet):
    pass


class Topography(DataSet):
    pass


class ForestDensity(DataSet):
    pass


if __name__ == "__main__":
    moisture_data = Moisture()
    coords = [
        (34.05, -118.25),
        (40.71, -74.01),
    ]  # Example coordinates (Los Angeles and New York City)
    time = datetime(2023, 10, 1)  # Example date
    results = moisture_data.get_all(coords, time)
    print(results)
