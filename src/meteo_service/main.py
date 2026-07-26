from meteo_service.shared.adapters.api.app import create_app
from meteo_service.shared.config import get_settings


app = create_app(get_settings())
