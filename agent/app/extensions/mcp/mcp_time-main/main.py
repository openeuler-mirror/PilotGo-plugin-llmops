"""
MCP Time Server

A Model Context Protocol (MCP) server that provides time-related tools.
This server can be integrated with Claude Desktop or other MCP-compatible clients.

Features:
- Current time in any timezone
- Multi-timezone world clock
- Unix timestamp generation and conversion
- Timezone-aware date/time formatting

Author: Generated for MCP integration
License: MIT
"""

from typing import Any, Optional
from datetime import datetime
import zoneinfo
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server with descriptive name
mcp = FastMCP("timeserver")

# Common timezone mappings for easier reference
COMMON_TIMEZONES = [
    "UTC",
    "US/Eastern", 
    "US/Central",
    "US/Mountain",
    "US/Pacific",
    "Europe/London",
    "Europe/Paris",
    "Asia/Tokyo",
    "Asia/Shanghai",
    "Australia/Sydney"
]

@mcp.tool()
async def get_current_time(timezone: str = "UTC") -> str:
    """
    Get the current time in a specified timezone.
    
    This function retrieves the current date and time for any valid timezone.
    It uses Python's zoneinfo module for accurate timezone handling.

    Args:
        timezone (str): Timezone name following IANA timezone database format.
                       Examples: 'UTC', 'US/Pacific', 'US/Eastern', 'Europe/London',
                       'Asia/Tokyo', 'Australia/Sydney'
                       Defaults to 'UTC' if not specified.

    Returns:
        str: Formatted current time string in the format:
             "Current time in {timezone}: YYYY-MM-DD HH:MM:SS TZ"
             
    Examples:
        >>> await get_current_time()
        "Current time in UTC: 2024-01-01 12:00:00 UTC"
        
        >>> await get_current_time("US/Pacific")
        "Current time in US/Pacific: 2024-01-01 04:00:00 PST"
        
    Note:
        If an invalid timezone is provided, returns an error message
        with suggestions for valid timezone formats.
    """
    try:
        # Parse and validate the timezone
        if timezone.upper() == "UTC":
            tz = zoneinfo.ZoneInfo("UTC")
        else:
            tz = zoneinfo.ZoneInfo(timezone)
        
        # Get current time in the specified timezone
        current_time = datetime.now(tz)
        
        # Format the time in a human-readable format
        formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S %Z")
        
        return f"Current time in {timezone}: {formatted_time}"
    
    except Exception as e:
        return (f"Error getting time for timezone '{timezone}': {str(e)}. "
                f"Please use a valid timezone like 'UTC', 'US/Pacific', "
                f"'US/Eastern', 'Europe/London', etc.")

@mcp.tool()
async def get_time_in_multiple_zones() -> str:
    """
    Get the current time across multiple common timezones simultaneously.
    
    This function provides a world clock view showing the current time
    in major timezones around the globe. Useful for scheduling across
    time zones or getting a global time perspective.

    Returns:
        str: Multi-line string with current time in each timezone.
             Format: "Timezone: YYYY-MM-DD HH:MM:SS TZ"
             
    Examples:
        >>> await get_time_in_multiple_zones()
        '''Current time across multiple timezones:
        UTC: 2024-01-01 12:00:00 UTC
        US/Eastern: 2024-01-01 07:00:00 EST
        US/Pacific: 2024-01-01 04:00:00 PST
        Europe/London: 2024-01-01 12:00:00 GMT
        Asia/Tokyo: 2024-01-01 21:00:00 JST
        ...'''
        
    Note:
        Includes timezones for: UTC, US (Eastern/Central/Mountain/Pacific),
        Europe (London/Paris), Asia (Tokyo/Shanghai), Australia (Sydney)
    """
    time_info = []
    
    # Iterate through common timezones and get current time for each
    for tz_name in COMMON_TIMEZONES:
        try:
            tz = zoneinfo.ZoneInfo(tz_name)
            current_time = datetime.now(tz)
            formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S %Z")
            time_info.append(f"{tz_name}: {formatted_time}")
        except Exception as e:
            # Include error info if a timezone fails
            time_info.append(f"{tz_name}: Error - {str(e)}")
    
    return "Current time across multiple timezones:\n" + "\n".join(time_info)

@mcp.tool()
async def get_unix_timestamp() -> str:
    """
    Get the current time as a Unix timestamp.
    
    Returns the current time as seconds since the Unix epoch
    (January 1, 1970, 00:00:00 UTC). Also provides human-readable
    equivalent for reference.

    Returns:
        str: Unix timestamp and human-readable time in UTC.
             Format: "Current Unix timestamp: {timestamp}\\n
                     Human readable (UTC): YYYY-MM-DD HH:MM:SS UTC"
             
    Examples:
        >>> await get_unix_timestamp()
        '''Current Unix timestamp: 1704067200
        Human readable (UTC): 2024-01-01 00:00:00 UTC'''
        
    Note:
        Unix timestamps are timezone-independent and represent
        UTC time by definition.
    """
    current_time = datetime.now()
    unix_timestamp = int(current_time.timestamp())
    
    # Also provide human-readable UTC time for reference
    utc_readable = datetime.utcfromtimestamp(unix_timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')
    
    return f"Current Unix timestamp: {unix_timestamp}\nHuman readable (UTC): {utc_readable}"

@mcp.tool()
async def format_time(timestamp: int) -> str:
    """
    Convert a Unix timestamp to human-readable format.
    
    Takes a Unix timestamp (seconds since epoch) and converts it
    to readable date/time format in both local time and UTC.

    Args:
        timestamp (int): Unix timestamp (seconds since January 1, 1970, 00:00:00 UTC)
                        Must be a valid integer representing seconds since epoch.

    Returns:
        str: Formatted time string showing both local and UTC time.
             Format: "Timestamp {timestamp} converts to:\\n
                     Local time: YYYY-MM-DD HH:MM:SS (Local)\\n
                     UTC time: YYYY-MM-DD HH:MM:SS UTC"
             
    Examples:
        >>> await format_time(1704067200)
        '''Timestamp 1704067200 converts to:
        Local time: 2024-01-01 00:00:00 (Local)
        UTC time: 2024-01-01 00:00:00 UTC'''
        
        >>> await format_time(0)
        '''Timestamp 0 converts to:
        Local time: 1969-12-31 19:00:00 (Local)
        UTC time: 1970-01-01 00:00:00 UTC'''
        
    Raises:
        Returns error message if timestamp is invalid or conversion fails.
    """
    try:
        # Convert timestamp to datetime objects
        dt = datetime.fromtimestamp(timestamp)  # Local time
        utc_dt = datetime.utcfromtimestamp(timestamp)  # UTC time
        
        # Format both times
        local_time = dt.strftime("%Y-%m-%d %H:%M:%S (Local)")
        utc_time = utc_dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        
        return (f"Timestamp {timestamp} converts to:\n"
                f"Local time: {local_time}\n"
                f"UTC time: {utc_time}")
    
    except Exception as e:
        return f"Error converting timestamp {timestamp}: {str(e)}"

if __name__ == "__main__":
    """
    Entry point for the MCP server.
    
    Starts the FastMCP server using stdio transport for communication
    with MCP clients like Claude Desktop.
    """
    # Initialize and run the server with stdio transport
    mcp.run(transport='stdio')
