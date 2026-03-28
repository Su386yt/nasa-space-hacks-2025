import configparser
import os
import subprocess
from abc import abstractmethod, ABC
from dataclasses import dataclass
from datetime import datetime
import h5py
import xarray as xr
import numpy as np
import requests
from netCDF4 import Dataset
import xarray as xr
import numpy as np
import pandas as pd
import cdsapi
import rasterio
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from pyhigh import get_elevation_batch
import math
from functools import wraps
from geopy.distance import geodesic
from main import Location


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

    @log_time
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

#############
# Wind Data #
#############

class Wind(DataSet):
    @log_time
    def get_all(self, spacetimecoords: list[tuple[float, float, int]]) -> list[tuple[float, float]]:
        l = [(0.0, 0.0)] * len(spacetimecoords)

        c = cdsapi.Client()

        # Separate lats and lons
        lats = [p[0] for p in coords]
        lons = [p[1] for p in coords]

        # Determine bounding box
        north = max(lats) + 1.0  # add small buffer
        south = min(lats) - 1.0
        east = max(lons) + 1.0
        west = min(lons) - 1.0

        expected_paths_starts = {}
        for i in range(len(spacetimecoords)):
            coord = spacetimecoords[i]
            dt_object = datetime.fromtimestamp((coord[2]))

            expected_path = f"/data_sets/wind/era5_region-{north}{west}{south}{east}-{dt_object.year}{dt_object.month}{dt_object.day}"  # not even kidding dont ask me where the fuck i got the data from
            if expected_path not in expected_paths_starts:
                expected_paths_starts[expected_path] = [(i, coord)]
            else:
                expected_paths_starts[expected_path].append((i, coord))

        for path_start in expected_paths_starts:
            # Define download parameters
            coord = expected_paths_starts[path_start]
            dt_object = datetime.fromtimestamp((coord[0][1][2]))
            file_path = f"./data_sets/wind/era5_region-{north}{west}{south}{east}-{dt_object.year}{dt_object.month}{dt_object.day}.nc"

            p = Path(file_path)
            if not p.exists():
                # explicit filename expected by the downloader
                target_file = Path(file_path)
                target_file.parent.mkdir(parents=True, exist_ok=True)

                # ensure we pass a plain string and that the parent dir is writable
                target_str = str(target_file.resolve())

                # call retrieve
                c.retrieve(
                    'reanalysis-era5-single-levels',
                    {
                        'product_type': 'reanalysis',
                        'variable': ['10m_u_component_of_wind', '10m_v_component_of_wind'],
                        'year': f"{dt_object.year}",
                        'month': f"{dt_object.month}",
                        'day': f"{dt_object.day}",
                        'time': [
                            '12:00',
                        ],
                        'area': [north, west, south, east],  # N, W, S, E
                        'format': 'netcdf'
                    },
                    target=target_str
                )

                x = input("Press enter when the file is downloaded: ")

            # Open ERA5 NetCDF file (already downloaded)
            ds = xr.open_dataset(file_path)

            # Separate lats and lons into arrays for vectorized interpolation
            lats = xr.DataArray([p[1][0] for p in coord], dims="points")
            lons = xr.DataArray([p[1][1] for p in coord], dims="points")

            # Interpolate u10 and v10 components to all points at once
            u_interp = ds['u10'].interp(latitude=lats, longitude=lons)
            v_interp = ds['v10'].interp(latitude=lats, longitude=lons)

            # Convert to wind speed and direction
            wind_speed = np.sqrt(u_interp ** 2 + v_interp ** 2)
            wind_dir = (np.degrees(np.arctan2(u_interp, v_interp)) + 360) % 360

            wind_speed = wind_speed.values.astype(float).tolist()[0]
            wind_dir = wind_dir.values.astype(float).tolist()[0]
            for i in range(len(wind_speed)):
                l[coord[i][0]] = (wind_speed[i], wind_dir[i])
        return l


# ###################
# # Topography Data #
# ###################

class Topography(DataSet):
    @log_time
    def get_all(
            self, spacetimecoords: list[tuple[float, float, int]]
    ) -> list[tuple[float, float, float]]:
        """Returns tuples of (elevation, gradient_x, gradient_y) for each input coordinate"""

        results = []

        delta = 0.001
        needed_elevs_expanded = [[(lat, long), (lat + delta, long), (lat, long + delta)] for lat, long, _ in spacetimecoords]
        needed_elevs = [elem for sublist in needed_elevs_expanded for elem in sublist]

        elev_queries = get_elevation_batch(needed_elevs)
        for i in range(0, len(spacetimecoords) * 3, 3):
            elevation = float(elev_queries[i])
            elev_lat_plus = float(elev_queries[i+1])
            elev_long_plus = float(elev_queries[i+2])

            delta_lat = (elev_lat_plus - elevation) / delta
            delta_long = (elev_long_plus - elevation) / delta

            results.append((
                elevation,
                delta_lat,
                delta_long
            ))

        return results


#######################
# Forest Density Data #
#######################
#
# class ForestDensity(DataSet):
#     @log_time
#     def get_all(
#             self, spacetimecoords: list[tuple[float, float, int]]
#     ) -> list[float]:
#         l = [0.0] * len(spacetimecoords)
#         p = Path("./data_sets/vegetation/")
#         p.mkdir(parents=True, exist_ok=True)
#         print(p.resolve())
#
#         for file in p.iterdir():
#             # Open the HDF4 file with rasterio to list subdatasets
#             with rasterio.open(file) as src:
#                 # Find the Percent_Tree_Cover subdataset
#                 subdatasets = src.subdatasets
#                 tree_cover_path = [s for s in subdatasets if "Percent_Tree_Cover" in s][0]
#
#             # Now open that subdataset with xarray
#             ds = xr.open_dataset(tree_cover_path, engine="rasterio")
#
#             # Build query arrays
#             lats = xr.DataArray([pt[0] for pt in spacetimecoords], dims="points")
#             lons = xr.DataArray([pt[1] for pt in spacetimecoords], dims="points")
#
#             # Interpolate
#             percent_tree_cover = ds["band_data"].interp(y=lats, x=lons)
#             percent_tree_cover = percent_tree_cover.values.astype(float).tolist()
#
#             for i, val in enumerate(percent_tree_cover):
#                 if math.isnan(val):
#                     continue
#                 l[i] = val
#
#         return l

#################
# Fire Checking #
#################

def was_fire(place: Location, start_time: int, end_time: int, radius: float = 0.1) -> bool:
    """Returns whether a fire ocurred within radius of place between startTime and endTime"""
    pass

def were_fires(places: list[Location], start_time: int, end_time: int) -> list[int]:
    """Returns a list of fires between """


    results = []

    start_dt = datetime.fromtimestamp(start_time)
    start_date = start_dt.strftime("%Y-%m-%d")
    end_dt = datetime.fromtimestamp(end_time)
    end_date = end_dt.strftime("%Y-%m-%d")

    for loc in places:
        location = loc.location

        response = requests.get(url)
        if response.status_code != 200:
            print(f"Error fetching data for ({lat}, {lon}) — {response.status_code}")
            results[(lat, lon)] = {
                "fire_detected": False,
                "fire_count": 0,
                "records": [],
            }
            continue

        # Parse CSV text
        lines = response.text.strip().split("\n")
        if len(lines) <= 1:
            results.append([0])
            continue

        headers = lines[0].split(",")
        fire_records = []

        for line in lines[1:]:
            values = line.split(",")
            record = dict(zip(headers, values))
            acq_date = record.get("acq_date", "")
            if acq_date:
                acq_dt = datetime.strptime(acq_date, "%Y-%m-%d")
                if start_dt <= acq_dt <= end_dt:
                    fire_records.append(record)

        results[(lat, lon)] = {
            "fire_detected": len(fire_records) > 0,
            "fire_count": len(fire_records),
            "records": fire_records,
        }

    return results




if __name__ == "__main__":
    f = ForestDensity()
    topography = Topography()
    coords = [
        (52.8734,-118.0814, 1704218400),
        (52.7264, -117.6360, 1704218400),
        (52.6646, -118.0565, 1704218400),
        (52.6639, -117.8839, 1704218400),
        (52.9093, -118.0887, 1704218400)
    ]  # Example coordinates (Georgia's random generated coords around jasper)
    time = datetime(2023, 10, 1)  # Example date
    # forest = f.get_all(coords)
    # print(forest)
    topography_results = topography.get_all(coords)
    print(topography_results)