from typing import Any, Tuple
import httpx
from mcp.server.fastmcp import FastMCP
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# Initialize FastMCP server
mcp = FastMCP("weather")

# Constants
NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"
GEOCODER = Nominatim(user_agent=USER_AGENT)

async def make_nws_request(url: str) -> dict[str, Any] | None:
    """Make a request to the NWS API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

def format_alert(feature: dict) -> str:
    """Format an alert feature into a readable string."""
    props = feature["properties"]
    return f"""
Event: {props.get('event', 'Unknown')}
Area: {props.get('areaDesc', 'Unknown')}
Severity: {props.get('severity', 'Unknown')}
Description: {props.get('description', 'No description available')}
Instructions: {props.get('instruction', 'No specific instructions provided')}
"""

@mcp.tool()
async def get_alerts(state: str) -> str:
    """Get weather alerts for a US state.

    Args:
        state: Two-letter US state code (e.g. CA, NY)
    """
    url = f"{NWS_API_BASE}/alerts/active/area/{state}"
    data = await make_nws_request(url)

    if not data or "features" not in data:
        return "Unable to fetch alerts or no alerts found."

    if not data["features"]:
        return "No active alerts for this state."

    alerts = [format_alert(feature) for feature in data["features"]]
    return "\n---\n".join(alerts)

@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for a location.

    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
    """
    # First get the forecast grid endpoint
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)

    if not points_data:
        return "Unable to fetch forecast data for this location."

    # Get the forecast URL from the points response
    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await make_nws_request(forecast_url)

    if not forecast_data:
        return "Unable to fetch detailed forecast."

    # Format the periods into a readable forecast
    periods = forecast_data["properties"]["periods"]
    forecasts = []
    for period in periods:  # Show all available periods (usually 14 for a 7-day forecast)
        forecast = f"""
{period['name']}:
Temperature: {period['temperature']}°{period['temperatureUnit']}
Wind: {period['windSpeed']} {period['windDirection']}
Forecast: {period['detailedForecast']}
"""
        forecasts.append(forecast)

    return "\n---\n".join(forecasts)

def geocode_city(city: str, state: str = None) -> Tuple[float, float] | None:
    """Convert a city name to latitude and longitude coordinates.
    
    Args:
        city: The name of the city
        state: Optional US state code (e.g. CA, NY)
        
    Returns:
        Tuple of (latitude, longitude) or None if geocoding failed
    """
    try:
        # Add state code to query if provided for better accuracy
        query = f"{city}, {state}" if state else city
        location = GEOCODER.geocode(query, exactly_one=True, timeout=10)
        
        if location:
            return (location.latitude, location.longitude)
        return None
    except (GeocoderTimedOut, GeocoderServiceError):
        return None

@mcp.tool()
async def get_forecast_by_city(city: str, state: str = None) -> str:
    """Get a 7-day weather forecast for a city.
    
    Args:
        city: The name of the city
        state: Optional US state code (e.g. CA, NY) for better accuracy
    """
    # First geocode the city to get coordinates
    coordinates = geocode_city(city, state)
    
    if not coordinates:
        return f"Unable to find coordinates for {city}{', ' + state if state else ''}."
    
    latitude, longitude = coordinates
    
    # Use the existing forecast function with the obtained coordinates
    return await get_forecast(latitude, longitude)

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
