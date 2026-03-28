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
    def __init__(
        self,
        location: tuple[float, float, int],
        wind: tuple[float, float], # Speed, direction
        forest_density: float,
        moisture_content: float
    ):
        self.location = location
        self.wind = wind
        self.forest_density = forest_density
        self.moisture_content = moisture_content

    def get_risk_index(self) -> float:
        pass

# class Model(ABC):
#     @abstractmethod
#     def train_model(self, data: list[Location]):
#         """Trains the model using the given data"""
#         pass



from scipy.optimize import curve_fit

def risk_index(X, w1, w2, w3, w4, w5):
    v1, v2, v3, v4, v5 = X
    return ((w1 * v1)**2 + (w2 * v2)**2 + (w3 * v3)**2 + (w4 * v4)**2 + (w5 * v5)**2)**0.5

def model_fitting (locations: list, outputs: list) -> list:
    try:
        curve = curve_fit(risk_index, locations, outputs, bounds = (0, 1), maxfev = 1201)
        popt = curve[0]
        return popt
    except RuntimeError:
        return f"couldn't optimise in 1201 iterations"

