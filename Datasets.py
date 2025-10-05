import configparser
import os
import subprocess
from abc import abstractmethod, ABC
from dataclasses import dataclass
from datetime import datetime
import xarray as xr

import numpy as np
import requests
from netCDF4 import Dataset


#################
# Logging Setup #
#################
# YOUR FUCKING CODE CRASHED
# Jokes sorry for yelling here's the error
# Sorrryyyyyyyyyyyyyyyy

# Traceback (most recent call last):
#   File "C:\Users\sylvi\GitHub\nasa-space-hacks-2025\Datasets.py", line 20, in <module>
#     handler = RotatingFileHandler("./logs/timing.txt", maxBytes=1024**2, backupCount=5)
#               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#   File "C:\Users\sylvi\AppData\Local\Programs\Python\Python312\Lib\logging\handlers.py", line 155, in __init__
#     BaseRotatingHandler.__init__(self, filename, mode, encoding=encoding,
#   File "C:\Users\sylvi\AppData\Local\Programs\Python\Python312\Lib\logging\handlers.py", line 58, in __init__
#     logging.FileHandler.__init__(self, filename, mode=mode,
#   File "C:\Users\sylvi\AppData\Local\Programs\Python\Python312\Lib\logging\__init__.py", line 1231, in __init__
#     StreamHandler.__init__(self, self._open())
#                                  ^^^^^^^^^^^^
#   File "C:\Users\sylvi\AppData\Local\Programs\Python\Python312\Lib\logging\__init__.py", line 1263, in _open
#     return open_func(self.baseFilename, self.mode,
#            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# FileNotFoundError: [Errno 2] No such file or directory: 'C:\\Users\\sylvi\\GitHub\\nasa-space-hacks-2025\\logs\\timing.txt'

# logger = logging.getLogger("timing_logger")
# logger.setLevel(logging.INFO)
# handler = RotatingFileHandler("./logs/timing.txt", maxBytes=1024**2, backupCount=5)
# formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
# handler.setFormatter(formatter)
# logger.addHandler(handler)
#
#
# # Decorator to time a function and log the duration
# def log_time(func):
#     @wraps(func)
#     def wrapper(*args, **kwargs):
#         start_time = datetime.now()
#         result = func(*args, **kwargs)
#         end_time = datetime.now()
#         elapsed = end_time - start_time
#         logger.info(
#             f"Function '{func.__qualname__}' took {elapsed} seconds to complete."
#         )
#         return result
#
#     return wrapper

# Idk how any of the above works and tbg my brain doesn't work enough to figure it out
# so im only claiming responsible for the code below this line
# love everyone
# <333
# 🌈🌈 - Sylv

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
        # "Cookie": "----------------------; -------; ---------------------",
    } # why commit your credentials to public repo wtfffff
    # Dw i wiped them
    # but wowww that wasnt the brightest

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
    # @log_time
    def get_all(
        self, spacetimecoords: list[tuple[float, float, int]]
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
    # Information link: https://search.earthdata.nasa.gov/search/granules?p=C1700900796-GES_DISC&pg[0][v]=f&pg[0][gsk]=start_date&q=moisture&sb[0]=-121.8239%2C53.58184%2C-108.52653%2C59.57104&qt=2024-01-01T00%3A00%3A00.000Z%2C2024-01-31T23%3A59%3A59.999Z&tl=1401854634.594!5!!&lat=15&long=5.899999823084067&zoom=1.779719355143404
    URL_PREFIX = "https://smos-diss.eo.esa.int/oads/data/NRT_Open/W_XX-ESA,SMOS,NRTNN_C_LEMM_"

    # @log_time
    def get_all(
        self, spacetimecoords: list[tuple[float, float, int]]
    ) -> list[float]:
        """Will attempt to retrieve data from within the same day as the provided time"""
        expected_filepath = os.path.join(
            self.DIR, f"moisture.nc4"
        )
        l = [0]*len(spacetimecoords)

        expected_paths_starts = {}
        for i in range(len(spacetimecoords)):
            coord = spacetimecoords[i]
            dt_object = datetime.fromtimestamp((coord[2]))

            expected_path = f"GLDAS_CLSM025_DA1_D.A{dt_object.strftime("%Y%m%d")}" # not even kidding dont ask me where the fuck i got the data from
            print(expected_path)
            if expected_path not in expected_paths_starts:
                expected_paths_starts[expected_path] = [(i, coord)]
            else:
                expected_paths_starts[expected_path].append((i, coord))

        directory = './data_sets/soil_moisture/'
        for path_start in expected_paths_starts:
            for f in os.listdir(directory):
                if not f.startswith(path_start):
                    continue

                coord = expected_paths_starts[path_start]

                # Open the file
                ds = xr.open_dataset(f"{directory}{f}")
                print(ds.data_vars.keys())

                # Separate lats and lons into arrays for vectorized interpolation
                lats = xr.DataArray([p[1][0] for p in coord], dims="points")
                lons = xr.DataArray([p[1][1] for p in coord], dims="points")

                # Interpolate u10 and v10 components to all points at once
                moistures = ds["SoilMoist_S_tavg"].interp(lat=lats, lon=lons)
                moistures = moistures.values.astype(float).tolist()[0]
                for i in range(len(moistures)):
                    l[coord[i][0]] = moistures[i]
        return l





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
        (52.8734,-118.0814, 1704218400),
        (52.7264, -117.6360, 1704218400),
        (52.6646, -118.0565, 1704218400),
        (52.6639, -117.8839, 1704218400),
        (52.9093, -118.0887, 1704218400)
    ]  # Example coordinates (Georgia's random generated coords around jasper)
    time = datetime(2023, 10, 1)  # Example date
    results = moisture_data.get_all(coords)
    print(results)
