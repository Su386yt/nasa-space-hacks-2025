from abc import abstractmethod, ABC
import logging
from logging.handlers import RotatingFileHandler
import time
from functools import wraps

# Sets up logging
logger = logging.getLogger("timing_logger")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler("./logs/timing.logs", maxBytes = 1024 ** 2, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Decorator to time a function and log the duration
def log_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        logger.info(f"Function '{func.__qualname__}' took {elapsed:.6f} seconds to complete.")
        return result
    return wrapper


class DataSet(ABC):
    FILENAME: str
    INPUT_UNIT: str
    OUTPUT_UNIT: str

    @abstractmethod
    @log_time
    def get_all(self, coordinates: list[tuple[float, float]], time: ) -> list[float]:
        """Returns a list corresponding to the data value at each input coordinate"""
        pass

class FuelData(DataSet):
    pass

class Wind(DataSet):
    pass

class Topography(DataSet):
    pass

class ForestDensity(DataSet):
    pass

class Moisture(DataSet):
    pass