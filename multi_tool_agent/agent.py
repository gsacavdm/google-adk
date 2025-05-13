#!python

import datetime
from zoneinfo import ZoneInfo
from google.adk.agents import Agent

def get_weather(city: str) -> dict:
  """Retrieves the current weather report for a specified city.

  Args:
    city (str): The name of the city to get the weather for.
    
  Returns:
    dict: A dictionary containing the weather report.
  """

  if city.lower() == "new york":
    return {
      "status": "success",
      "report": (
        "The weather in New York is sunny with a temperature of 25 degrees"
        " Celcius (77 degress Fahrenheight)."
      ),
    }
  else:
    return {
      "status": "error",
      "report": f"Sorry, I don't have the weather information for {city}.",
    }

def get_current_time(city: str) -> dict:
  """Retrieves the current time for a specified city.

  Args:
    city (str): The name of the city to get the time for.
    
  Returns:
    dict: A dictionary containing the current time.
  """

  if city.lower() == "new york":
    tz_identifier= "America/New_York"
  else:
    return {
      "status": "error",
      "report": f"Sorry, I don't have the timezone information for {city}.",
    }

  tz = ZoneInfo(tz_identifier)
  now = datetime.datetime.now(tz)
  return {
    "status": "success",
    "report": f"The current time in {city} is {now}.",
  }

def get_list_of_cities() -> list:
  """Retrieves a list of cities for which the agent can provide information.

  Returns:
    list: A list of city names.
  """
  return ["New York", "Los Angeles", "Chicago", "Madeupville"]

root_agent = Agent(
  name="weather_time_agent",
  #model="gemini-2.0-flash",
  model="gemini-2.0-flash-live-001",
  description="An agent that provides weather and time information.",
  instruction="You are a helpful agent who can answer questions about the weather and time in a city. Answer each inquiry with rhyme.",
  tools=[get_weather, get_current_time, get_list_of_cities],
)