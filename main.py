import geopandas as gpd
import matplotlib.pyplot as plt


def location_invariant_model(
    fuel_density,
    forest_density,
    moisture_content,
    fuel_density_weight,
    forest_density_weight,
    moisture_content_weight
):
    return


def get_base_layer():
    pass


class Location:
    pass
    def __init__(
        self,
        location: tuple[float, float],
        time: int,
        fuel_density: float,
        wind_speed: float,
        wind_direction: float,
        forest_density: float,
        moisture_content: float
    ):
        self.location = location
        self.time = time
        self.fuel_density = fuel_density
        self.wind_speed = wind_speed
        self.wind_direction = wind_direction
        self.forest_density = forest_density
        self.moisture_content = moisture_content

    def get_risk_index(self) -> float:
        pass




