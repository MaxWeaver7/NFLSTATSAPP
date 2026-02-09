NFL API

Welcome to the BALLDONTLIE NFL API, the best NFL API on the planet. This API contains data from 2002-current. An API key is required. You can obtain an API key by creating a free account on our website. Read the authentication section to learn how to use the API key.

Download language specific libraries:

Python
Javascript
Take a look at our other APIs.

Join us on discord.

AI-Powered Integration

 New to programming? Our API is designed to work seamlessly with AI assistants like ChatGPT, Claude, and Gemini. You don't need coding experience to get started!
Using the OpenAPI Specification with AI
Our complete OpenAPI specification allows AI assistants to automatically understand and interact with our API. Simply share the spec URL with your AI assistant and describe what you want to build—the AI will handle the technical implementation.

Getting Started with AI:

Copy this URL: https://www.balldontlie.io/openapi.yml
Share it with your preferred AI assistant (ChatGPT, Claude, Gemini, etc.)
Tell the AI what you want to build (e.g., "Create a dashboard showing this week's NFL games")
The AI will read the OpenAPI spec and write the code for you
Example prompts to try:

"Using the OpenAPI spec at https://www.balldontlie.io/openapi.yml, show me how to get Patrick Mahomes' season stats"
"Read the BALLDONTLIE OpenAPI spec and create a Python script that fetches this week's NFL games"
"Help me understand the available NFL endpoints from this OpenAPI spec: https://www.balldontlie.io/openapi.yml"
This makes it incredibly easy for non-technical users, analysts, and researchers to leverage our sports data without needing to learn programming from scratch.

Google Sheets Integration

 Prefer spreadsheets over code? Pull live sports data directly into Google Sheets with our custom functions - no programming required!
Our Google Sheets integration lets you access all the same data available through our API using simple spreadsheet formulas. Perfect for fantasy sports tracking, betting analysis, and sports research.

Quick Start:

Get your API key from app.balldontlie.io
Copy our Google Sheets script
Paste it into your Google Sheet (Extensions > Apps Script)
Start using functions in your cells
Example functions:

=BDL_NFL_PLAYERS("Mahomes") - Search for players
=BDL_NFL_GAMES("2026-01-27", 2025, 18) - Get games by date/week
=BDL_NFL_STANDINGS(2025) - Get current standings
=BDL_NFL_ODDS("2026-01-27") - Get betting odds
For full setup instructions and the complete list of 150+ functions, see our Google Sheets Integration Guide.

Account Tiers

There are three different account tiers which provide you access to different types of data. Visit our website to create an account for free.

Paid tiers do not apply across sports. The tier you purchase for NFL will not automatically be applied to other sports. You can purchase the ALL-ACCESS ($299.99/mo) tier to get access to every endpoint for every sport.

Read the table below to see the breakdown.

Endpoint	Free	ALL-STAR	GOAT
Teams	Yes	Yes	Yes
Players	Yes	Yes	Yes
Games	Yes	Yes	Yes
Player Injuries	No	Yes	Yes
Active Players	No	Yes	Yes
Team Standings	No	Yes	Yes
Stats	No	Yes	Yes
Season Stats	No	Yes	Yes
Team Stats	No	Yes	Yes
Team Season Stats	No	Yes	Yes
Advanced Rushing Stats	No	No	Yes
Advanced Passing Stats	No	No	Yes
Advanced Receiving Stats	No	No	Yes
Plays	No	No	Yes
Betting Odds	No	No	Yes
Player Props	No	No	Yes
Team Roster	No	No	Yes
The feature breakdown per tier is shown in the table below.

Tier	Requests / Min	$USD / mo.
GOAT	600	39.99
ALL-STAR	60	9.99
Free	5	0
Authentication

To authorize, use this code:
from balldontlie import BalldontlieAPI

api = BalldontlieAPI(api_key="YOUR_API_KEY")
Make sure to replace YOUR_API_KEY with your API key.
BALLDONTLIE uses API keys to allow access to the API. You can obtain an API key by creating a free account at our website

We expect the API key to be included in all API requests to the server in a header that looks like the following:

Authorization: YOUR_API_KEY

 You must replace YOUR_API_KEY with your personal API key.
Pagination

This API uses cursor based pagination rather than limit/offset. Endpoints that support pagination will send back responses with a meta key that looks like what is displayed on the right.

{
  "meta": {
    "next_cursor": 90,
    "per_page": 25
  }
}
You can use per_page to specify the maximum number of results. It defaults to 25 and doesn't allow values larger than 100.

You can use next_cursor to get the next page of results. Specify it in the request parameters like this: ?cursor=NEXT_CURSOR.

Errors

The API uses the following error codes:

Error Code	Meaning
401	Unauthorized - You either need an API key or your account tier does not have access to the endpoint.
400	Bad Request -- The request is invalid. The request parameters are probably incorrect.
404	Not Found -- The specified resource could not be found.
406	Not Acceptable -- You requested a format that isn't json.
429	Too Many Requests -- You're rate limited.
500	Internal Server Error -- We had a problem with our server. Try again later.
503	Service Unavailable -- We're temporarily offline for maintenance. Please try again later.
Teams

Get All Teams
from balldontlie import BalldontlieAPI

api = BalldontlieAPI(api_key="YOUR_API_KEY")
teams = api.nfl.teams.list()
The above command returns JSON structured like this:
{
  "data": [
    {
      "id": 18,
      "conference": "NFC",
      "division": "EAST",
      "location": "Philadelphia",
      "name": "Eagles",
      "full_name": "Philadelphia Eagles",
      "abbreviation": "PHI"
    },
    ...
  ]
}

This endpoint retrieves all teams.

HTTP Request

GET https://api.balldontlie.io//nfl/v1/teams

Query Parameters

Parameter	Required	Description
division	false	Returns teams that belong to this division
conference	false	Returns teams that belong to this conference
Get a Specific Team
from balldontlie import BalldontlieAPI

api = BalldontlieAPI(api_key="YOUR_API_KEY")
team = api.nfl.teams.get(18)
The above command returns JSON structured like this:
{
  "data": [
    {
      "id": 18,
      "conference": "NFC",
      "division": "EAST",
      "location": "Philadelphia",
      "name": "Eagles",
      "full_name": "Philadelphia Eagles",
      "abbreviation": "PHI"
    }
  ]
}
This endpoint retrieves a specific team.

HTTP Request

GET https://api.balldontlie.io/nfl/v1/teams/<ID>

URL Parameters

Parameter	Required	Description
ID	true	The ID of the team to retrieve
Team Roster

 Team roster data is only available starting with the 2025 season.
Get Team Roster
from balldontlie import BalldontlieAPI

api = BalldontlieAPI(api_key="YOUR_API_KEY")
roster = api.nfl.teams.roster(18)
The above command returns JSON structured like this:
{
  "data": [
    {
      "player": {
        "id": 2153,
        "first_name": "Connor",
        "last_name": "McGovern",
        "position": "Center",
        "position_abbreviation": "C",
        "height": "6' 5\"",
        "weight": "318 lbs",
        "jersey_number": "66",
        "college": "Penn State",
        "experience": "7th Season",
        "age": 28
      },
      "position": "C",
      "depth": 1,
      "player_name": "Connor McGovern",
      "injury_status": null
    },
    {
      "player": {
        "id": 279668,
        "first_name": "Alec",
        "last_name": "Anderson",
        "position": "Offensive Tackle",
        "position_abbreviation": "OT",
        "height": "6' 5\"",
        "weight": "305 lbs",
        "jersey_number": "70",
        "college": "UCLA",
        "experience": "3rd Season",
        "age": 26
      },
      "position": "C",
      "depth": 2,
      "player_name": "Alec Anderson",
      "injury_status": null
    },
    {
      "player": {
        "id": 279664,
        "first_name": "Sedrick",
        "last_name": "Van Pran-Granger",
        "position": "Center",
        "position_abbreviation": "C",
        "height": "6' 4\"",
        "weight": "310 lbs",
        "jersey_number": "62",
        "college": "Georgia",
        "experience": "2nd Season",
        "age": 24
      },
      "position": "C",
      "depth": 3,
      "player_name": "Sedrick Van Pran-Granger",
      "injury_status": null
    }
  ]
}
This endpoint retrieves a team's roster with depth chart information. Results are ordered by position group, position, and depth.

HTTP Request

GET https://api.balldontlie.io/nfl/v1/teams/<ID>/roster

URL Parameters

Parameter	Required	Description
ID	true	The ID of the team to retrieve roster for
Query Parameters

Parameter	Required	Description
season	false	Filter by season year. Defaults to the most recent season with roster data.
Players

Get All Players
from balldontlie import BalldontlieAPI

api = BalldontlieAPI(api_key="YOUR_API_KEY")
players = api.nfl.players.list()
The above command returns JSON structured like this:
{
  "data": [
    {
      "id": 33,
      "first_name": "Lamar",
      "last_name": "Jackson",
      "position": "Quarterback",
      "position_abbreviation": "QB",
      "height": "6' 2\"",
      "weight": "205 lbs",
      "jersey_number": "8",
      "college": "Louisville",
      "experience": "7th Season",
      "age": 27,
      "team": {
        "id": 6,
        "conference": "AFC",
        "division": "NORTH",
        "location": "Baltimore",
        "name": "Ravens",
        "full_name": "Baltimore Ravens",
        "abbreviation": "BAL"
      }
    },
    ...
  ],
  "meta": { "next_cursor": 25, "per_page": 25 }
}
This endpoint retrieves all players.

HTTP Request

GET https://api.balldontlie.io/nfl/v1/players

Query Parameters

Parameter	Required	Description
cursor	false	The cursor, used for pagination
per_page	false	The number of results per page. Default to 25. Max is 100
search	false	Returns players whose first or last name matches this value. For example, ?search=lamar will return players that have 'lamar' in their first or last name.
first_name	false	Returns players whose first name matches this value. For example, ?search=lamar will return players that have 'lamar' in their first name.
last_name	false	Returns players whose last name matches this value. For example, ?search=jackson will return players that have 'jackson' in their last name.
team_ids	false	Returns players that belong to these team ids. This should be an array: ?team_ids[]=1&team_ids[]=2
player_ids	false	Returns players that match these ids. This should be an array: ?player_ids[]=1&player_ids[]=2
Get a Specific Player
from balldontlie import BalldontlieAPI

api = BalldontlieAPI(api_key="YOUR_API_KEY")
player = api.nfl.players.get(33)
The above command returns JSON structured like this:
{
  "data": {
    "id": 33,
    "first_name": "Lamar",
    "last_name": "Jackson",
    "position": "Quarterback",
    "position_abbreviation": "QB",
    "height": "6' 2\"",
    "weight": "205 lbs",
    "jersey_number": "8",
    "college": "Louisville",
    "experience": "7th Season",
    "age": 27,
    "team": {
      "id": 6,
      "conference": "AFC",
      "division": "NORTH",
      "location": "Baltimore",
      "name": "Ravens",
      "full_name": "Baltimore Ravens",
      "abbreviation": "BAL"
    }
  }
}
This endpoint retrieves a specific player.

HTTP Request

GET https://api.balldontlie.io/nfl/v1/players/<ID>

URL Parameters

Parameter	Required	Description
ID	true	The ID of the player to retrieve
Player Injuries

Get All Player Injuries
from balldontlie import BalldontlieAPI

api = BalldontlieAPI(api_key="YOUR_API_KEY")
injuries = api.nfl.injuries.list()
The above command returns JSON structured like this:
{
  "data": [
    {
      "player": {
        "id": 85,
        "first_name": "Dorian",
        "last_name": "Thompson-Robinson",
        "position": "Quarterback",
        "position_abbreviation": "QB",
        "height": "6' 2\"",
        "weight": "203 lbs",
        "jersey_number": "17",
        "college": "UCLA",
        "experience": "2nd Season",
        "age": 24,
        "team": {
          "id": 8,
          "conference": "AFC",
          "division": "NORTH",
          "location": "Cleveland",
          "name": "Browns",
          "full_name": "Cleveland Browns",
          "abbreviation": "CLE"
        }
      },
      "status": "Questionable",
      "comment": "Thompson-Robinson (finger) received negative X-ray results on his right middle finger Monday but is undergoing an MRI to determine the severity of the injury, Mary Kay Cabot of The Cleveland Plain Dealer reports.",
      "date": "2024-10-21T16:04:00.000Z"
    },
    ...
  ],
  "meta": { "next_cursor": 62089, "per_page": 25 }
}

This endpoint retrieves all player injuries.

HTTP Request

GET https://api.balldontlie.io/nfl/v1/player_injuries

Query Parameters

Parameter	Required	Description
cursor	false	The cursor, used for pagination
per_page	false	The number of results per page. Default to 25. Max is 100
team_ids	false	Returns players that belong to these team ids. This should be an array: ?team_ids[]=1&team_ids[]=2
player_ids	false	Returns players that match these ids. This should be an array: ?player_ids[]=1&player_ids[]=2
Active Players

Get All Active Players
from balldontlie import BalldontlieAPI

api = BalldontlieAPI(api_key="YOUR_API_KEY")
players = api.nfl.players.list_active()
The above command returns JSON structured like this:
{
  "data": [
    {
      "id": 12,
      "first_name": "Kenneth",
      "last_name": "Gainwell",
      "position": "Running Back",
      "position_abbreviation": "RB",
      "height": "5' 9\"",
      "weight": "200 lbs",
      "jersey_number": "14",
      "college": "Memphis",
      "experience": "4th Season",
      "age": 25,
      "team": {
        "id": 18,
        "conference": "NFC",
        "division": "EAST",
        "location": "Philadelphia",
        "name": "Eagles",
        "full_name": "Philadelphia Eagles",
        "abbreviation": "PHI"
      }
    },
    ...
  ],
  "meta": { "next_cursor": 23, "per_page": 25 }
}

This endpoint retrieves all active players.

HTTP Request

GET https://api.balldontlie.io/nfl/v1/players/active

Query Parameters

Parameter	Required	Description
cursor	false	The cursor, used for pagination
per_page	false	The number of results per page. Default to 25. Max is 100
search	false	Returns players whose first or last name matches this value. For example, ?search=lamar will return players that have 'lamar' in their first or last name.
first_name	false	Returns players whose first name matches this value. For example, ?search=lamar will return players that have 'lamar' in their first name.
last_name	false	Returns players whose last name matches this value. For example, ?search=jackson will return players that have 'jackson' in their last name.
team_ids	false	Returns players that belong to these team ids. This should be an array: ?team_ids[]=1&team_ids[]=2
player_ids	false	Returns players that match these ids. This should be an array: ?player_ids[]=1&player_ids[]=2
Games

Game data is updated in real-time for games currently in progress.
Get All Games
from balldontlie import BalldontlieAPI

api = BalldontlieAPI(api_key="YOUR_API_KEY")
games = api.nfl.games.list()
The above command returns JSON structured like this:
{
  "data": [
    {
      "id": 7001,
      "visitor_team": {
        "id": 6,
        "conference": "AFC",
        "division": "NORTH",
        "location": "Baltimore",
        "name": "Ravens",
        "full_name": "Baltimore Ravens",
        "abbreviation": "BAL"
      },
      "home_team": {
        "id": 14,
        "conference": "AFC",
        "division": "WEST",
        "location": "Kansas City",
        "name": "Chiefs",
        "full_name": "Kansas City Chiefs",
        "abbreviation": "KC"
      },
      "summary": "Chiefs hold off Ravens 27-20 when review overturns TD on final play of NFL's season opener",
      "venue": "GEHA Field at Arrowhead Stadium",
      "week": 1,
      "date": "2024-09-06T00:20:00.000Z",
      "season": 2024,
      "postseason": false,
      "status": "Final",
      "home_team_score": 27,
      "home_team_q1": 7,
      "home_team_q2": 6,
      "home_team_q3": 7,
      "home_team_q4": 7,
      "home_team_ot": null,
      "visitor_team_score": 20,
      "visitor_team_q1": 7,
      "visitor_team_q2": 3,
      "visitor_team_q3": null,
      "visitor_team_q4": 10,
      "visitor_team_ot": null
    }
  ],
  "meta": {
    "per_page": 25,
    "next_cursor": 7024
  }
}
This endpoint retrieves all games.

HTTP Request

GET https://api.balldontlie.io/nfl/v1/games

Query Parameters

Parameter	Required	Description
cursor	false	The cursor, used for pagination
per_page	false	The number of results per page. Default to 25. Max is 100
dates	false	Returns games that match these dates. Dates should be formatted in YYYY-MM-DD. This should be an array: ?dates[]=2024-01-01&dates[]=2024-01-02
seasons	false	Returns games that occurred in these seasons. This should be an array: ?seasons[]=2022&seasons[]=2023
team_ids	false	Returns games for these team ids. This should be an array: ?team_ids[]=1&team_ids[]=2
posteason	false	Returns playoffs games when set to true. Returns regular season games when set to false. Returns both when not specified
weeks	false	Returns games that occurred in these weeks. This should be an array: ?weeks[]=3
Get a Specific Game
from balldontlie import BalldontlieAPI

api = BalldontlieAPI(api_key="YOUR_API_KEY")
game = api.nfl.games.get(7001)
The above command returns JSON structured like this:
{
  "data": {
    "id": 7001,
    "visitor_team": {
      "id": 6,
      "conference": "AFC",
      "division": "NORTH",
      "location": "Baltimore",
      "name": "Ravens",
      "full_name": "Baltimore Ravens",
      "abbreviation": "BAL"
    },
    "home_team": {
      "id": 14,
      "conference": "AFC",
      "division": "WEST",
      "location": "Kansas City",
      "name": "Chiefs",
      "full_name": "Kansas City Chiefs",
      "abbreviation": "KC"
    },
    "summary": "Chiefs hold off Ravens 27-20 when review overturns TD on final play of NFL's season opener",
    "venue": "GEHA Field at Arrowhead Stadium",
    "week": 1,
    "date": "2024-09-06T00:20:00.000Z",
    "season": 2024,
    "postseason": false,
    "status": "Final",
    "home_team_score": 27,
    "home_team_q1": 7,
    "home_team_q2": 6,
    "home_team_q3": 7,
    "home_team_q4": 7,
    "home_team_ot": null,
    "visitor_team_score": 20,
    "visitor_team_q1": 7,
    "visitor_team_q2": 3,
    "visitor_team_q3": null,
    "visitor_team_q4": 10,
    "visitor_team_ot": null
  }
}
This endpoint retrieves a specific game.

HTTP Request

GET https://api.balldontlie.io/nfl/v1/games/<ID>

URL Parameters

Parameter	Required	Description
ID	true	The ID of the game to retrieve
Stats

Stats are updated in real-time for games currently in progress.
Get All Stats
from balldontlie import BalldontlieAPI

api = BalldontlieAPI(api_key="YOUR_API_KEY")
stats = api.nfl.stats.list()
The above command returns JSON structured like this:
{
  "data": [
    {
      "player": {
        "id": 33,
        "first_name": "Lamar",
        "last_name": "Jackson",
        "position": "Quarterback",
        "position_abbreviation": "QB",
        "height": "6' 2\"",
        "weight": "205 lbs",
        "jersey_number": "8",
        "college": "Louisville",
        "experience": "7th Season",
        "age": 27
      },
      "team": {
        "id": 6,
        "conference": "AFC",
        "division": "NORTH",
        "location": "Baltimore",
        "name": "Ravens",
        "full_name": "Baltimore Ravens",
        "abbreviation": "BAL"
      },
      "game": {
        "id": 7001,
        "visitor_team": {
          "id": 6,
          "conference": "AFC",
          "division": "NORTH",
          "location": "Baltimore",
          "name": "Ravens",
          "full_name": "Baltimore Ravens",
          "abbreviation": "BAL"
        },
        "home_team": {
          "id": 14,
          "conference": "AFC",
          "division": "WEST",
          "location": "Kansas City",
          "name": "Chiefs",
          "full_name": "Kansas City Chiefs",
          "abbreviation": "KC"
        },
        "summary": "Chiefs hold off Ravens 27-20 when review overturns TD on final play of NFL's season opener",
        "venue": "GEHA Field at Arrowhead Stadium",
        "week": 1,
        "date": "2024-09-06T00:20:00.000Z",
        "season": 2024,
        "postseason": false,
        "status": "Final",
        "home_team_score": 27,
        "home_team_q1": 7,
        "home_team_q2": 6,
        "home_team_q3": 7,
        "home_team_q4": 7,
        "home_team_ot": null,
        "visitor_team_score": 20,
        "visitor_team_q1": 7,
        "visitor_team_q2": 3,
        "visitor_team_q3": null,
        "visitor_team_q4": 10,
        "visitor_team_ot": null
      },
      "passing_completions": 26,
      "passing_attempts": 41,
      "passing_yards": 273,
      "yards_per_pass_attempt": 6.7,
      "passing_touchdowns": 1,
      "passing_interceptions": null,
      "sacks": 1,
      "sacks_loss": 6,
      "qbr": 61.1,
      "qb_rating": 90.8,
      "rushing_attempts": 16,
      "rushing_yards": 122,
      "yards_per_rush_attempt": 7.6,
      "rushing_touchdowns": 0,
      "long_rushing": 16,
      "receptions": null,
      "receiving_yards": null,
      "yards_per_reception": null,
      "receiving_touchdowns": null,
      "long_reception": null,
      "receiving_targets": null,
      "fumbles": 1,
      "fumbles_lost": 1,
      "fumbles_recovered": 0,
      "total_tackles": null,
      "defensive_sacks": null,
      "solo_tackles": null,
      "tackles_for_loss": null,
      "passes_defended": null,
      "qb_hits": null,
      "fumbles_touchdowns": null,
      "defensive_interceptions": null,
      "interception_yards": null,
      "interception_touchdowns": null,
      "kick_returns": null,
      "kick_return_yards": null,
      "yards_per_kick_return": null,
      "long_kick_return": null,
      "kick_return_touchdowns": null,
      "punt_returns": null,
      "punt_return_yards": null,
      "yards_per_punt_return": null,
      "long_punt_return": null,
      "punt_return_touchdowns": null,
      "field_goal_attempts": null,
      "field_goals_made": null,
      "field_goal_pct": null,
      "long_field_goal_made": null,
      "extra_points_made": null,
      "total_points": null,
      "punts": null,
      "punt_yards": null,
      "gross_avg_punt_yards": null,
      "touchbacks": null,
      "punts_inside_20": null,
      "long_punt": null
    },
    ...
  ],
  "meta": { "per_page": 25 }
}
This endpoint retrieves all stats.

HTTP Request

GET https://api.balldontlie.io/nfl/v1/stats

Query Parameters

Parameter	Required	Description
cursor	false	The page number, used for pagination.
per_page	false	The number of results returned per call, used for pagination. Max 100.
player_ids	false	Returns stats for these player ids. This should be an array: ?player_ids[]=1&player_ids[]=2
game_ids	false	Returns stat for these game ids. This should be an array: ?game_ids[]=1&game_ids[]=2
seasons	false	Returns stats that occurred in these seasons. This should be an array: ?seasons[]=2022&seasons[]=2023
Season Stats

Get Season Stats
from balldontlie import BalldontlieAPI

api = BalldontlieAPI(api_key="YOUR_API_KEY")
stats = api.nfl.season_stats.list(season=2024)
The above command returns JSON structured like this:
{
  "data": [
    {
      "player": {
        "id": 36,
        "first_name": "Derrick",
        "last_name": "Henry",
        "position": "Running Back",
        "position_abbreviation": "RB",
        "height": "6' 2\"",
        "weight": "247 lbs",
        "jersey_number": "22",
        "college": "Alabama",
        "experience": "9th Season",
        "age": 30
      },
      "games_played": 7,
      "season": 2024,
      "postseason": false,
      "passing_completions": null,
      "passing_attempts": null,
      "passing_yards": null,
      "yards_per_pass_attempt": null,
      "passing_touchdowns": null,
      "passing_interceptions": null,
      "passing_yards_per_game": null,
      "passing_completion_pct": null,
      "qbr": null,
      "rushing_attempts": 134,
      "rushing_yards": 873,
      "rushing_yards_per_game": 124.7143,
      "yards_per_rush_attempt": 6.515,
      "rushing_touchdowns": 8,
      "rushing_fumbles": 1,
      "rushing_fumbles_lost": null,
      "rushing_first_downs": 39,
      "receptions": 7,
      "receiving_yards": 62,
      "yards_per_reception": 8.857,
      "receiving_touchdowns": 2,
      "receiving_fumbles": null,
      "receiving_fumbles_lost": null,
      "receiving_first_downs": 4,
      "receiving_targets": 9,
      "receiving_yards_per_game": 8.857142,
      "fumbles_forced": null,
      "fumbles_recovered": null,
      "total_tackles": null,
      "defensive_sacks": null,
      "defensive_sack_yards": null,
      "solo_tackles": null,
      "assist_tackles": null,
      "fumbles_touchdowns": null,
      "defensive_interceptions": null,
      "interception_touchdowns": null,
      "kick_returns": null,
      "kick_return_yards": null,
      "yards_per_kick_return": null,
      "kick_return_touchdowns": null,
      "punt_returner_returns": null,
      "punt_returner_return_yards": null,
      "yards_per_punt_return": null,
      "punt_return_touchdowns": null,
      "field_goal_attempts": null,
      "field_goals_made": null,
      "field_goal_pct": null,
      "punts": null,
      "punt_yards": null,
      "field_goals_made_1_19": null,
      "field_goals_made_20_29": null,
      "field_goals_made_30_39": null,
      "field_goals_made_40_49": null,
      "field_goals_made_50": null,
      "field_goals_attempts_1_19": null,
      "field_goals_attempts_20_29": null,
      "field_goals_attempts_30_39": null,
      "field_goals_attempts_40_49": null,
      "field_goals_attempts_50": null
    }
  ],
  "meta": { "next_cursor": 83571, "per_page": 25 }
}
HTTP Request

GET https://api.balldontlie.io/nfl/v1/season_stats

Query Parameters

Parameter	Required	Description
season	true	Returns season stats for this season
player_ids	false	Returns season stats for these players. This should be an array: player_ids[]=1
team_id	false	Returns season stats for his team
postseason	false	Returns season stats for postseason or regular season. Defaults to false.
sort_by	false	Returns season stats sorted by this attribute. Most attributes in the response body can be specified
sort_order	false	Returns season stats sorted in asc or desc
Team Standings

Get Team Standings
from balldontlie import BalldontlieAPI

api = BalldontlieAPI(api_key="YOUR_API_KEY")
standings = api.nfl.standings.get(season=2024)
The above command returns JSON structured like this:
{
  "data": [
    {
      "team": {
        "id": 21,
        "conference": "NFC",
        "division": "EAST",
        "location": "Washington",
        "name": "Commanders",
        "full_name": "Washington Commanders",
        "abbreviation": "WSH"
      },
      "win_streak": 1,
      "points_for": 218,
      "points_against": 152,
      "playoff_seed": 2,
      "point_differential": 66,
      "overall_record": "5-2",
      "conference_record": "3-1",
      "division_record": "1-0",
      "wins": 5,
      "losses": 2,
      "ties": 0,
      "home_record": "3-0",
      "road_record": "2-2",
      "season": 2024
    },
    ...
  ]
}

This endpoint retrieves regular season team standings.

HTTP Request

GET https://api.balldontlie.io/nfl/v1/standings

Query Parameters

Parameter	Required	Description
season	true	Returns regular season standings for the specified season. For example, ?season=2023 will return the team standings for the 2023-24 season.
Advanced Rushing Stats

Get Advanced Rushing Stats
from balldontlie import BalldontlieAPI

api = BalldontlieAPI(api_key="YOUR_API_KEY")
stats = api.nfl.advanced_stats.rushing.get(season=2023)
The above command returns JSON structured like this:
{
  "data": [
    {
      "player": {
        "id": 466,
        "first_name": "James",
        "last_name": "Conner",
        "position": "Running Back",
        "position_abbreviation": "RB",
        "height": "6' 1\"",
        "weight": "233 lbs",
        "jersey_number": "6",
        "college": "Pittsburgh",
        "experience": "8th Season",
        "age": 29
      },
      "season": 2024,
      "week": 0,
      "postseason": false,
      "avg_time_to_los": 2.91877397260274,
      "expected_rush_yards": 618.9679635508963,
      "rush_attempts": 159,
      "rush_pct_over_expected": 0.4285714285714285,
      "rush_touchdowns": 5,
      "rush_yards": 697,
      "rush_yards_over_expected": 59.03203644910366,
      "rush_yards_over_expected_per_att": 0.3833249120071666,
      "efficiency": 4.161334289813485,
      "percent_attempts_gte_eight_defenders": 25.15723270440252,
      "avg_rush_yards": 4.383647798742138
    }
  ],
  "meta": { "next_cursor": 83571, "per_page": 25 }
}
HTTP Request

GET https://api.balldontlie.io/nfl/v1/advanced_stats/rushing?season=2024

Query Parameters

Parameter	Required	Description
season	true	Returns season stats for this season
player_id	false	Returns season stats for this player
postseason	false	Returns season stats for regular vs postseason
week	false	Returns season stats for this week. Week 0 represents stats for the whole season
Advanced Passing Stats

Get Advanced Passing Stats
from balldontlie import BalldontlieAPI

api = BalldontlieAPI(api_key="YOUR_API_KEY")
stats = api.nfl.advanced_stats.passing.get(season=2024)
The above command returns JSON structured like this:
{
  "data": [
    {
      "player": {
        "id": 63,
        "first_name": "Matthew",
        "last_name": "Stafford",
        "position": "Quarterback",
        "position_abbreviation": "QB",
        "height": "6' 3\"",
        "weight": "214 lbs",
        "jersey_number": "9",
        "college": "Georgia",
        "experience": "16th Season",
        "age": 36
      },
      "season": 2024,
      "week": 0,
      "postseason": false,
      "aggressiveness": 13.9751552795031,
      "attempts": 322,
      "avg_air_distance": 21.63436475569557,
      "avg_air_yards_differential": -2.125107043683379,
      "avg_air_yards_to_sticks": -0.8761341853035138,
      "avg_completed_air_yards": 5.58981308411215,
      "avg_intended_air_yards": 7.714920127795528,
      "avg_time_to_throw": 2.78214953271028,
      "completion_percentage": 66.45962732919256,
      "completion_percentage_above_expectation": -1.853113571776092,
      "completions": 214,
      "expected_completion_percentage": 68.31274090096865,
      "games_played": 9,
      "interceptions": 7,
      "max_air_distance": 62.01834083559476,
      "max_completed_air_distance": 55.93206057352081,
      "pass_touchdowns": 9,
      "pass_yards": 2262,
      "passer_rating": 86.99534161490683
    }
  ],
  "meta": { "next_cursor": 83571, "per_page": 25 }
}
HTTP Request

GET https://api.balldontlie.io/nfl/v1/advanced_stats/passing?season=2024

Query Parameters

Parameter	Required	Description
season	true	Returns season stats for this season
player_id	false	Returns season stats for this player
postseason	false	Returns season stats for regular vs postseason
week	false	Returns season stats for this week. Week 0 represents stats for the whole season
Advanced Receiving Stats

Get Advanced Receiving Stats
from balldontlie import BalldontlieAPI

api = BalldontlieAPI(api_key="YOUR_API_KEY")
stats = api.nfl.advanced_stats.passing.get(season=2024)
The above command returns JSON structured like this:
{
  "data": [
    {
      "player": {
        "id": 651,
        "first_name": "Tutu",
        "last_name": "Atwell",
        "position": "Wide Receiver",
        "position_abbreviation": "WR",
        "height": "5' 9\"",
        "weight": "165 lbs",
        "jersey_number": "5",
        "college": "Louisville",
        "experience": "4th Season",
        "age": 25
      },
      "season": 2024,
      "week": 0,
      "postseason": false,
      "avg_cushion": 8.23361111111111,
      "avg_expected_yac": 4.380550229106592,
      "avg_intended_air_yards": 12.60675,
      "avg_separation": 3.579191769761275,
      "avg_yac": 3.581153846153846,
      "avg_yac_above_expectation": -0.7993963829527457,
      "catch_percentage": 65,
      "percent_share_of_intended_air_yards": 20.61619221664847,
      "rec_touchdowns": 0,
      "receptions": 26,
      "targets": 40,
      "yards": 372
    }
  ],
  "meta": { "next_cursor": 83571, "per_page": 25 }
}
HTTP Request

GET https://api.balldontlie.io/nfl/v1/advanced_stats/receiving?season=2024

Query Parameters

Parameter	Required	Description
season	true	Returns season stats for this season
player_id	false	Returns season stats for this player
postseason	false	Returns season stats for regular vs postseason
week	false	Returns season stats for this week. Week 0 represents stats for the whole season
Team Season Stats

Get Team Season Stats
import requests

response = requests.get(
    'https://api.balldontlie.io/nfl/v1/team_season_stats',
    headers={'Authorization': 'YOUR_API_KEY'}
)
data = response.json()
The above command returns JSON structured like this:
{
  "data": [
    {
      "team": {
        "id": 25,
        "conference": "NFC",
        "division": "NORTH",
        "location": "Detroit",
        "name": "Lions",
        "full_name": "Detroit Lions",
        "abbreviation": "DET"
      },
      "season": 2025,
      "season_type": 2,
      "games_played": 7,
      "fumbles_recovered": 4,
      "fumbles_lost": 2,
      "total_offensive_yards": 2570,
      "total_offensive_yards_per_game": 367.1,
      "net_passing_yards": 1565,
      "net_passing_yards_per_game": 223.6,
      "total_points": 215,
      "total_points_per_game": 30.7,
      "passing_completions": 153,
      "passing_yards": 1634,
      "passing_yards_per_game": 233.4,
      "passing_attempts": 204,
      "passing_completion_pct": 75,
      "net_total_offensive_yards": 2501,
      "net_total_offensive_yards_per_game": 357.3,
      "net_yards_per_pass_attempt": 7.212,
      "yards_per_pass_attempt": 8.01,
      "passing_long": 64,
      "passing_touchdowns": 16,
      "passing_interceptions": 3,
      "passing_sacks": 13,
      "passing_sack_yards_lost": 69,
      "passing_qb_rating": 117.973,
      "rushing_yards": 936,
      "rushing_yards_per_game": 133.7,
      "rushing_attempts": 207,
      "rushing_yards_per_rush_attempt": 4.522,
      "rushing_long": 78,
      "rushing_touchdowns": 10,
      "rushing_fumbles": 7,
      "rushing_fumbles_lost": 0,
      "receiving_receptions": 153,
      "receiving_yards": 1634,
      "receiving_yards_per_reception": 10.68,
      "receiving_long": 64,
      "receiving_touchdowns": 16,
      "receiving_fumbles": 3,
      "receiving_fumbles_lost": 2,
      "receiving_yards_per_game": 233.4,
      "misc_first_downs": 139,
      "misc_first_downs_rushing": 48,
      "misc_first_downs_passing": 84,
      "misc_first_downs_penalty": 7,
      "misc_third_down_convs": 32,
      "misc_third_down_attempts": 85,
      "misc_third_down_conv_pct": 37.647,
      "misc_fourth_down_convs": 8,
      "misc_fourth_down_attempts": 13,
      "misc_fourth_down_conv_pct": 61.538,
      "misc_total_penalties": 42,
      "misc_total_penalty_yards": 315,
      "misc_turnover_differential": 6,
      "misc_total_takeaways": 11,
      "misc_total_giveaways": 5,
      "returning_kick_returns": 25,
      "returning_kick_return_yards": 636,
      "returning_yards_per_kick_return": 25.44,
      "returning_long_kick_return": 37,
      "returning_kick_return_touchdowns": 0,
      "returning_punt_returns": 12,
      "returning_punt_return_yards": 125,
      "returning_yards_per_punt_return": 10.417,
      "returning_long_punt_return": 65,
      "returning_punt_return_touchdowns": 1,
      "returning_punt_return_fair_catches": 8,
      "kicking_field_goals_made": 8,
      "kicking_field_goal_attempts": 11,
      "kicking_field_goal_pct": 72.727,
      "kicking_long_field_goal_made": 58,
      "kicking_field_goals_made_1_19": 0,
      "kicking_field_goals_made_20_29": 2,
      "kicking_field_goals_made_30_39": 2,
      "kicking_field_goals_made_40_49": 2,
      "kicking_field_goals_made_50": 2,
      "kicking_field_goal_attempts_1_19": 0,
      "kicking_field_goal_attempts_20_29": 2,
      "kicking_field_goal_attempts_30_39": 2,
      "kicking_field_goal_attempts_40_49": 2,
      "kicking_field_goal_attempts_50": 5,
      "kicking_extra_points_made": 27,
      "kicking_extra_point_attempts": 27,
      "kicking_extra_point_pct": 100,
      "punting_punts": 27,
      "punting_punt_yards": 1274,
      "punting_long_punt": 66,
      "punting_gross_avg_punt_yards": 47.185,
      "punting_net_avg_punt_yards": 42,
      "punting_punts_blocked": 0,
      "punting_punts_inside_20": 14,
      "punting_touchbacks": 0,
      "punting_fair_catches": 11,
      "punting_punt_returns": 14,
      "punting_punt_return_yards": 140,
      "punting_avg_punt_return_yards": 10,
      "defensive_interceptions": 7,
      "opp_games_played": 7,
      "opp_fumbles_recovered": 2,
      "opp_fumbles_lost": 4,
      "opp_total_offensive_yards": 2244,
      "opp_total_offensive_yards_per_game": 320.6,
      "opp_net_passing_yards": 1486,
      "opp_net_passing_yards_per_game": 212.3,
      "opp_total_points": 151,
      "opp_total_points_per_game": 21.6,
      "opp_passing_completions": 150,
      "opp_passing_yards": 1630,
      "opp_passing_yards_per_game": 232.9,
      "opp_passing_attempts": 238,
      "opp_passing_completion_pct": 63.025,
      "opp_net_total_offensive_yards": 2100,
      "opp_net_total_offensive_yards_per_game": 300,
      "opp_net_yards_per_pass_attempt": 5.693,
      "opp_yards_per_pass_attempt": 6.849,
      "opp_passing_long": 64,
      "opp_passing_touchdowns": 14,
      "opp_passing_interceptions": 7,
      "opp_passing_sacks": 23,
      "opp_passing_sack_yards_lost": 144,
      "opp_passing_qb_rating": 90.494,
      "opp_rushing_yards": 614,
      "opp_rushing_yards_per_game": 87.7,
      "opp_rushing_attempts": 155,
      "opp_rushing_yards_per_rush_attempt": 3.961,
      "opp_rushing_long": 28,
      "opp_rushing_touchdowns": 5,
      "opp_rushing_fumbles": 2,
      "opp_rushing_fumbles_lost": 2,
      "opp_receiving_receptions": 150,
      "opp_receiving_yards": 1630,
      "opp_receiving_yards_per_reception": 10.867,
      "opp_receiving_long": 64,
      "opp_receiving_touchdowns": 14,
      "opp_receiving_fumbles": 7,
      "opp_receiving_fumbles_lost": 2,
      "opp_receiving_yards_per_game": 232.9,
      "opp_misc_first_downs": 132,
      "opp_misc_first_downs_rushing": 36,
      "opp_misc_first_downs_passing": 80,
      "opp_misc_first_downs_penalty": 16,
      "opp_misc_third_down_convs": 32,
      "opp_misc_third_down_attempts": 85,
      "opp_misc_third_down_conv_pct": 37.647,
      "opp_misc_fourth_down_convs": 6,
      "opp_misc_fourth_down_attempts": 13,
      "opp_misc_fourth_down_conv_pct": 46.154,
      "opp_misc_total_penalties": 33,
      "opp_misc_total_penalty_yards": 209,
      "opp_misc_turnover_differential": -6,
      "opp_misc_total_takeaways": 5,
      "opp_misc_total_giveaways": 11,
      "opp_returning_kick_returns": 33,
      "opp_returning_kick_return_yards": 842,
      "opp_returning_yards_per_kick_return": 25.515,
      "opp_returning_long_kick_return": 43,
      "opp_returning_kick_return_touchdowns": 0,
      "opp_returning_punt_returns": 14,
      "opp_returning_punt_return_yards": 140,
      "opp_returning_yards_per_punt_return": 10,
      "opp_returning_long_punt_return": 21,
      "opp_returning_punt_return_touchdowns": 0,
      "opp_returning_punt_return_fair_catches": 11,
      "opp_kicking_field_goals_made": 7,
      "opp_kicking_field_goal_attempts": 8,
      "opp_kicking_field_goal_pct": 87.5,
      "opp_kicking_long_field_goal_made": 53,
      "opp_kicking_field_goals_made_1_19": 0,
      "opp_kicking_field_goals_made_20_29": 0,
      "opp_kicking_field_goals_made_30_39": 4,
      "opp_kicking_field_goals_made_40_49": 1,
      "opp_kicking_field_goals_made_50": 2,
      "opp_kicking_field_goal_attempts_1_19": 0,
      "opp_kicking_field_goal_attempts_20_29": 0,
      "opp_kicking_field_goal_attempts_30_39": 4,
      "opp_kicking_field_goal_attempts_40_49": 1,
      "opp_kicking_field_goal_attempts_50": 3,
      "opp_kicking_extra_points_made": 16,
      "opp_kicking_extra_point_attempts": 17,
      "opp_kicking_extra_point_pct": 94.118,
      "opp_punting_punts": 28,
      "opp_punting_punt_yards": 1376,
      "opp_punting_long_punt": 65,
      "opp_punting_gross_avg_punt_yards": 49.143,
      "opp_punting_net_avg_punt_yards": 44.679,
      "opp_punting_punts_blocked": 0,
      "opp_punting_punts_inside_20": 14,
      "opp_punting_touchbacks": 3,
      "opp_punting_fair_catches": 8,
      "opp_punting_punt_returns": 12,
      "opp_punting_punt_return_yards": 125,
      "opp_punting_avg_punt_return_yards": 10.417,
      "opp_defensive_interceptions": 3
    }
  ],
  "meta": {
    "per_page": 25
  }
}
This endpoint retrieves comprehensive team season statistics including offense, defense, special teams, and opponent stats.

HTTP Request

GET https://api.balldontlie.io/nfl/v1/team_season_stats

Query Parameters

Parameter	Required	Description
season	true	Returns team season stats for this season
team_ids	true	Returns stats for these team ids. This should be an array: ?team_ids[]=1&team_ids[]=2
postseason	false	Returns postseason stats when set to true. Returns regular season stats when set to false
cursor	false	The cursor, used for pagination
per_page	false	The number of results per page. Default to 25. Max is 100
Team Stats

Stats are updated in real-time for games currently in progress.
Get Team Stats
import requests

response = requests.get(
    'https://api.balldontlie.io/nfl/v1/team_stats',
    headers={'Authorization': 'YOUR_API_KEY'}
)
data = response.json()
The above command returns JSON structured like this:
{
  "data": [
    {
      "game": {
        "id": 424066,
        "visitor_team": {
          "id": 6,
          "conference": "AFC",
          "division": "NORTH",
          "location": "Baltimore",
          "name": "Ravens",
          "full_name": "Baltimore Ravens",
          "abbreviation": "BAL"
        },
        "home_team": {
          "id": 5,
          "conference": "AFC",
          "division": "EAST",
          "location": "Miami",
          "name": "Dolphins",
          "full_name": "Miami Dolphins",
          "abbreviation": "MIA"
        },
        "summary": null,
        "venue": "Hard Rock Stadium",
        "week": 9,
        "date": "2025-10-31T00:15:00.000Z",
        "season": 2025,
        "postseason": false,
        "status": "Final",
        "home_team_score": 6,
        "home_team_q1": 3,
        "home_team_q2": 3,
        "home_team_q3": null,
        "home_team_q4": null,
        "home_team_ot": null,
        "visitor_team_score": 28,
        "visitor_team_q1": 7,
        "visitor_team_q2": 7,
        "visitor_team_q3": 14,
        "visitor_team_q4": null,
        "visitor_team_ot": null
      },
      "team": {
        "id": 6,
        "conference": "AFC",
        "division": "NORTH",
        "location": "Baltimore",
        "name": "Ravens",
        "full_name": "Baltimore Ravens",
        "abbreviation": "BAL"
      },
      "home_away": "away",
      "first_downs": 18,
      "first_downs_passing": 11,
      "first_downs_rushing": 7,
      "first_downs_penalty": 0,
      "third_down_efficiency": "5-13",
      "third_down_conversions": 5,
      "third_down_attempts": 13,
      "fourth_down_efficiency": "1-1",
      "fourth_down_conversions": 1,
      "fourth_down_attempts": 1,
      "total_offensive_plays": 56,
      "total_yards": 338,
      "yards_per_play": 6,
      "total_drives": 11,
      "net_passing_yards": 188,
      "passing_completions": 18,
      "passing_attempts": 23,
      "yards_per_pass": 7.5,
      "sacks": 2,
      "sack_yards_lost": 16,
      "rushing_yards": 150,
      "rushing_attempts": 31,
      "yards_per_rush_attempt": 4.8,
      "red_zone_scores": 3,
      "red_zone_attempts": 3,
      "penalties": 5,
      "penalty_yards": 56,
      "turnovers": 0,
      "fumbles_lost": 0,
      "interceptions_thrown": 0,
      "defensive_touchdowns": 0,
      "possession_time": "31:43",
      "possession_time_seconds": 1903
    },
    {
      "game": {
        "id": 424066,
        "visitor_team": {
          "id": 6,
          "conference": "AFC",
          "division": "NORTH",
          "location": "Baltimore",
          "name": "Ravens",
          "full_name": "Baltimore Ravens",
          "abbreviation": "BAL"
        },
        "home_team": {
          "id": 5,
          "conference": "AFC",
          "division": "EAST",
          "location": "Miami",
          "name": "Dolphins",
          "full_name": "Miami Dolphins",
          "abbreviation": "MIA"
        },
        "summary": null,
        "venue": "Hard Rock Stadium",
        "week": 9,
        "date": "2025-10-31T00:15:00.000Z",
        "season": 2025,
        "postseason": false,
        "status": "Final",
        "home_team_score": 6,
        "home_team_q1": 3,
        "home_team_q2": 3,
        "home_team_q3": null,
        "home_team_q4": null,
        "home_team_ot": null,
        "visitor_team_score": 28,
        "visitor_team_q1": 7,
        "visitor_team_q2": 7,
        "visitor_team_q3": 14,
        "visitor_team_q4": null,
        "visitor_team_ot": null
      },
      "team": {
        "id": 5,
        "conference": "AFC",
        "division": "EAST",
        "location": "Miami",
        "name": "Dolphins",
        "full_name": "Miami Dolphins",
        "abbreviation": "MIA"
      },
      "home_away": "home",
      "first_downs": 17,
      "first_downs_passing": 12,
      "first_downs_rushing": 4,
      "first_downs_penalty": 1,
      "third_down_efficiency": "2-12",
      "third_down_conversions": 2,
      "third_down_attempts": 12,
      "fourth_down_efficiency": "2-3",
      "fourth_down_conversions": 2,
      "fourth_down_attempts": 3,
      "total_offensive_plays": 62,
      "total_yards": 332,
      "yards_per_play": 5.4,
      "total_drives": 11,
      "net_passing_yards": 245,
      "passing_completions": 25,
      "passing_attempts": 40,
      "yards_per_pass": 5.8,
      "sacks": 2,
      "sack_yards_lost": 16,
      "rushing_yards": 87,
      "rushing_attempts": 20,
      "yards_per_rush_attempt": 4.4,
      "red_zone_scores": 0,
      "red_zone_attempts": 3,
      "penalties": 5,
      "penalty_yards": 45,
      "turnovers": 3,
      "fumbles_lost": 2,
      "interceptions_thrown": 1,
      "defensive_touchdowns": 0,
      "possession_time": "28:17",
      "possession_time_seconds": 1697
    }
  ],
  "meta": {
    "per_page": 25
  }
}
This endpoint retrieves team statistics for individual games.

HTTP Request

GET https://api.balldontlie.io/nfl/v1/team_stats

Query Parameters

Parameter	Required	Description
cursor	false	The cursor, used for pagination
per_page	false	The number of results per page. Default to 25. Max is 100
team_ids	false	Returns stats for these team ids. This should be an array: ?team_ids[]=1&team_ids[]=2
seasons	false	Returns stats for these seasons. This should be an array: ?seasons[]=2023&seasons[]=2024
game_ids	false	Returns stats for these game ids. This should be an array: ?game_ids[]=7001&game_ids[]=7002
Plays

Get Play-by-Play Data
import requests

response = requests.get(
    'https://api.balldontlie.io/nfl/v1/plays',
    headers={'Authorization': 'YOUR_API_KEY'}
)
data = response.json()
The above command returns JSON structured like this:
{
  "data": [
    {
      "id": "40177294340",
      "game": {
        "id": 424066,
        "visitor_team": {
          "id": 6,
          "conference": "AFC",
          "division": "NORTH",
          "location": "Baltimore",
          "name": "Ravens",
          "full_name": "Baltimore Ravens",
          "abbreviation": "BAL"
        },
        "home_team": {
          "id": 5,
          "conference": "AFC",
          "division": "EAST",
          "location": "Miami",
          "name": "Dolphins",
          "full_name": "Miami Dolphins",
          "abbreviation": "MIA"
        },
        "summary": null,
        "venue": "Hard Rock Stadium",
        "week": 9,
        "date": "2025-10-31T00:15:00.000Z",
        "season": 2025,
        "postseason": false,
        "status": "Final",
        "home_team_score": 6,
        "home_team_q1": 3,
        "home_team_q2": 3,
        "home_team_q3": null,
        "home_team_q4": null,
        "home_team_ot": null,
        "visitor_team_score": 28,
        "visitor_team_q1": 7,
        "visitor_team_q2": 7,
        "visitor_team_q3": 14,
        "visitor_team_q4": null,
        "visitor_team_ot": null
      },
      "type_slug": "kickoff",
      "type_abbreviation": "K",
      "type_text": "Kickoff",
      "text": "T.Loop kicks 47 yards from BLT 35 to MIA 18. D.Eskridge pushed ob at MIA 43 for 25 yards (T.Wallace).",
      "short_text": "Tyler Loop 47 Yd Kickoff Dee Eskridge 25 Yd Kickoff Return",
      "away_score": 0,
      "home_score": 0,
      "scoring_play": false,
      "period": 1,
      "clock_display": "15:00",
      "team": {
        "id": 5,
        "conference": "AFC",
        "division": "EAST",
        "location": "Miami",
        "name": "Dolphins",
        "full_name": "Miami Dolphins",
        "abbreviation": "MIA"
      },
      "start_yard_line": 65,
      "start_down": null,
      "start_distance": null,
      "start_yards_to_endzone": 65,
      "end_yard_line": 43,
      "end_down": 1,
      "end_distance": 10,
      "end_yards_to_endzone": 57,
      "end_down_distance_text": "1st & 10 at MIA 43",
      "end_short_down_distance_text": "1st & 10",
      "end_possession_text": "MIA 43",
      "stat_yardage": 25,
      "home_win_probability": 0.4182,
      "wallclock": "2025-10-31T00:16:07.000Z"
    },
    {
      "id": "40177294363",
      "game": {
        "id": 424066,
        "visitor_team": {
          "id": 6,
          "conference": "AFC",
          "division": "NORTH",
          "location": "Baltimore",
          "name": "Ravens",
          "full_name": "Baltimore Ravens",
          "abbreviation": "BAL"
        },
        "home_team": {
          "id": 5,
          "conference": "AFC",
          "division": "EAST",
          "location": "Miami",
          "name": "Dolphins",
          "full_name": "Miami Dolphins",
          "abbreviation": "MIA"
        },
        "summary": null,
        "venue": "Hard Rock Stadium",
        "week": 9,
        "date": "2025-10-31T00:15:00.000Z",
        "season": 2025,
        "postseason": false,
        "status": "Final",
        "home_team_score": 6,
        "home_team_q1": 3,
        "home_team_q2": 3,
        "home_team_q3": null,
        "home_team_q4": null,
        "home_team_ot": null,
        "visitor_team_score": 28,
        "visitor_team_q1": 7,
        "visitor_team_q2": 7,
        "visitor_team_q3": 14,
        "visitor_team_q4": null,
        "visitor_team_ot": null
      },
      "type_slug": "pass-reception",
      "type_abbreviation": "REC",
      "type_text": "Pass Reception",
      "text": "(Shotgun) D.Brunskill reported in as eligible.  T.Tagovailoa pass short middle to J.Waddle to BLT 37 for 20 yards (A.Gilman).",
      "short_text": "Tua Tagovailoa Pass Complete for 20 Yds to Jaylen Waddle",
      "away_score": 0,
      "home_score": 0,
      "scoring_play": false,
      "period": 1,
      "clock_display": "14:56",
      "team": {
        "id": 5,
        "conference": "AFC",
        "division": "EAST",
        "location": "Miami",
        "name": "Dolphins",
        "full_name": "Miami Dolphins",
        "abbreviation": "MIA"
      },
      "start_yard_line": 43,
      "start_down": 1,
      "start_distance": 10,
      "start_yards_to_endzone": 57,
      "end_yard_line": 63,
      "end_down": 1,
      "end_distance": 10,
      "end_yards_to_endzone": 37,
      "end_down_distance_text": "1st & 10 at BAL 37",
      "end_short_down_distance_text": "1st & 10",
      "end_possession_text": "BAL 37",
      "stat_yardage": 20,
      "home_win_probability": 0.4499,
      "wallclock": "2025-10-31T00:16:51.000Z"
    }
  ],
  "meta": {
    "next_cursor": 1025245,
    "per_page": 25
  }
}
This endpoint retrieves play-by-play data for NFL games, ordered chronologically by wallclock time.

HTTP Request

GET https://api.balldontlie.io/nfl/v1/plays

Query Parameters

Parameter	Required	Description
game_id	true	Returns plays for this game
cursor	false	The cursor, used for pagination
per_page	false	The number of results per page. Default to 25. Max is 100
Betting Odds

Betting odds data is only available starting from the 2025 season, week 8 onwards.
Odds are updated live and reflect real-time changes from sportsbooks.
Get Betting Odds
import requests

response = requests.get(
    'https://api.balldontlie.io/nfl/v1/odds',
    params={'season': 2025, 'week': 8},
    headers={'Authorization': 'YOUR_API_KEY'}
)

print(response.json())
The above command returns JSON structured like this:
{
  "data": [
    {
      "id": 135955,
      "game_id": 424051,
      "vendor": "bet365",
      "spread_home_value": "-6",
      "spread_home_odds": -110,
      "spread_away_value": "6",
      "spread_away_odds": -110,
      "moneyline_home_odds": -275,
      "moneyline_away_odds": 225,
      "total_value": "54",
      "total_over_odds": -110,
      "total_under_odds": -110,
      "updated_at": "2025-10-21T03:35:36.520Z"
    },
    {
      "id": 1298,
      "game_id": 424051,
      "vendor": "betmgm",
      "spread_home_value": "-14.5",
      "spread_home_odds": -650,
      "spread_away_value": "14.5",
      "spread_away_odds": 400,
      "moneyline_home_odds": -10000,
      "moneyline_away_odds": 1500,
      "total_value": "33.5",
      "total_over_odds": 325,
      "total_under_odds": -500,
      "updated_at": "2025-10-21T02:21:38.157Z"
    },
    {
      "id": 1185,
      "game_id": 424051,
      "vendor": "draftkings",
      "spread_home_value": "-14.5",
      "spread_home_odds": -100000,
      "spread_away_value": "14.5",
      "spread_away_odds": 4000,
      "moneyline_home_odds": -100000,
      "moneyline_away_odds": 4000,
      "total_value": "33.5",
      "total_over_odds": 3000,
      "total_under_odds": -20000,
      "updated_at": "2025-10-21T02:20:09.818Z"
    },
    {
      "id": 2666,
      "game_id": 424051,
      "vendor": "caesars",
      "spread_home_value": "-14.5",
      "spread_home_odds": -250,
      "spread_away_value": "14.5",
      "spread_away_odds": 195,
      "moneyline_home_odds": -5000,
      "moneyline_away_odds": 1100,
      "total_value": "33.5",
      "total_over_odds": -220,
      "total_under_odds": 165,
      "updated_at": "2025-10-21T02:16:51.935Z"
    },
    {
      "id": 1386,
      "game_id": 424051,
      "vendor": "fanduel",
      "spread_home_value": "-14.5",
      "spread_home_odds": -700,
      "spread_away_value": "14.5",
      "spread_away_odds": 410,
      "moneyline_home_odds": -100000,
      "moneyline_away_odds": 4000,
      "total_value": "33.5",
      "total_over_odds": -102,
      "total_under_odds": -130,
      "updated_at": "2025-10-21T02:12:31.965Z"
    },
    {
      "id": 135954,
      "game_id": 424050,
      "vendor": "bet365",
      "spread_home_value": "1",
      "spread_home_odds": -110,
      "spread_away_value": "-1",
      "spread_away_odds": -110,
      "moneyline_home_odds": -2200,
      "moneyline_away_odds": 1000,
      "total_value": "47",
      "total_over_odds": -110,
      "total_under_odds": -110,
      "updated_at": "2025-10-20T05:00:31.776Z"
    },
    {
      "id": 1184,
      "game_id": 424050,
      "vendor": "draftkings",
      "spread_home_value": "-12.5",
      "spread_home_odds": -154,
      "spread_away_value": "12.5",
      "spread_away_odds": 120,
      "moneyline_home_odds": -100000,
      "moneyline_away_odds": 4000,
      "total_value": "32.5",
      "total_over_odds": -220,
      "total_under_odds": 170,
      "updated_at": "2025-10-20T03:18:08.421Z"
    },
    {
      "id": 2665,
      "game_id": 424050,
      "vendor": "caesars",
      "spread_home_value": "-9.5",
      "spread_home_odds": -135,
      "spread_away_value": "9.5",
      "spread_away_odds": -105,
      "moneyline_home_odds": -10000,
      "moneyline_away_odds": 2200,
      "total_value": "32.5",
      "total_over_odds": 100,
      "total_under_odds": -128,
      "updated_at": "2025-10-20T03:17:52.747Z"
    },
    {
      "id": 1385,
      "game_id": 424050,
      "vendor": "fanduel",
      "spread_home_value": "-9.5",
      "spread_home_odds": -310,
      "spread_away_value": "9.5",
      "spread_away_odds": 220,
      "moneyline_home_odds": -20000,
      "moneyline_away_odds": 2500,
      "total_value": "30.5",
      "total_over_odds": 124,
      "total_under_odds": -166,
      "updated_at": "2025-10-20T03:14:32.050Z"
    },
    {
      "id": 1297,
      "game_id": 424050,
      "vendor": "betmgm",
      "spread_home_value": "1",
      "spread_home_odds": -110,
      "spread_away_value": "-1",
      "spread_away_odds": -110,
      "moneyline_home_odds": -102,
      "moneyline_away_odds": -118,
      "total_value": "46.5",
      "total_over_odds": -110,
      "total_under_odds": -110,
      "updated_at": "2025-10-20T00:05:39.961Z"
    }
  ],
  "meta": {
    "per_page": 25
  }
}
This endpoint retrieves betting odds for NFL games. Either (season and week) or game_ids must be provided.

Available Vendors:

Vendor	Description
ballybet	Bally Bet
bet365	Bet365
betmgm	BetMGM
betparx	BetParx
betrivers	BetRivers
betway	Betway
caesars	Caesars Sportsbook
draftkings	DraftKings
fanatics	Fanatics Sportsbook
fanduel	FanDuel
kalshi	Kalshi (prediction market)
polymarket	Polymarket (prediction market)
HTTP Request

GET https://api.balldontlie.io/nfl/v1/odds

Query Parameters

Parameter	Required	Description
cursor	false	The cursor, used for pagination
per_page	false	The number of results per page. Default to 25. Max is 100
season	false	Returns odds for games in this season. Must be provided with week
week	false	Returns odds for games in this week. Must be provided with season
game_ids	false	Returns odds for these game ids. This should be an array: ?game_ids[]=15907925&game_ids[]=15907926
Player Props

Player prop betting data is LIVE and updated in real-time. We do not store historical data.
As games near completion, many (or all) player props may be removed from sportsbooks.
The Player Props API provides real-time player prop betting odds for NFL games. Player props allow betting on individual player performances such as passing yards, touchdowns, receptions, and more.

Market Types
The API supports two market types:

over_under: Traditional over/under markets where users can bet on whether a player will go over or under a specific line value
milestone: Milestone markets where users bet on whether a player will reach a specific achievement (e.g., 300+ passing yards)
Get Player Props
import requests

response = requests.get(
    'https://api.balldontlie.io/nfl/v1/odds/player_props',
    params={'game_id': 424051},
    headers={'Authorization': 'YOUR_API_KEY'}
)

print(response.json())
The above command returns JSON structured like this:
{
  "data": [
    {
      "id": 111967700,
      "game_id": 424129,
      "player_id": 490,
      "vendor": "betway",
      "prop_type": "rushing_yards",
      "line_value": "85.5",
      "market": {
        "type": "over_under",
        "over_odds": -115,
        "under_odds": -110
      },
      "updated_at": "2025-11-29T16:28:13.503Z"
    },
    {
      "id": 112042232,
      "game_id": 424129,
      "player_id": 490,
      "vendor": "draftkings",
      "prop_type": "anytime_td",
      "line_value": "0.5",
      "market": {
        "type": "milestone",
        "odds": -250
      },
      "updated_at": "2025-11-29T16:31:25.627Z"
    }
  ],
  "meta": {
    "per_page": 2
  }
}
This endpoint retrieves player prop betting odds for a specific NFL game. The game_id parameter is required.

This endpoint returns all player props for the specified game in a single response. Pagination is not supported.
Available Vendors:

Vendor	Description
ballybet	Bally Bet
betparx	BetParx
betrivers	BetRivers
betway	Betway
caesars	Caesars Sportsbook
draftkings	DraftKings
fanatics	Fanatics Sportsbook
fanduel	FanDuel
HTTP Request

GET https://api.balldontlie.io/nfl/v1/odds/player_props

Query Parameters

Parameter	Required	Description
game_id	true	The game ID to retrieve player props for
player_id	false	Filter props for a specific player
prop_type	false	Filter by prop type. See supported prop types below.
vendors	false	Filter by specific sportsbook vendors. This should be an array: ?vendors[]=draftkings&vendors[]=betrivers
Supported Prop Types

The following prop_type values are supported:

Prop Type	Description
anytime_td	Score a touchdown anytime
anytime_td_1h	Score a touchdown in first half
anytime_td_1q	Score a touchdown in first quarter
anytime_td_2h	Score a touchdown in second half
anytime_td_2q	Score a touchdown in second quarter
anytime_td_3q	Score a touchdown in third quarter
anytime_td_4q	Score a touchdown in fourth quarter
fg_made	Field goals made
fg_made_1h	Field goals made in first half
first_td	Score first touchdown of game
interceptions	Total interceptions thrown
kicking_points	Total kicking points
longest_pass	Longest pass completion
longest_reception	Longest reception
longest_rush	Longest rush
passing_attempts	Total passing attempts
passing_completions	Total passing completions
passing_tds	Total passing touchdowns
passing_tds_1h	Passing touchdowns in first half
passing_yards	Total passing yards
passing_yards_1h	Passing yards in first half
passing_yards_1q	Passing yards in first quarter
passing_yards_2q	Passing yards in second quarter
passing_yards_3q	Passing yards in third quarter
passing_yards_4q	Passing yards in fourth quarter
receiving_yards	Total receiving yards
receiving_yards_1h	Receiving yards in first half
receiving_yards_1q	Receiving yards in first quarter
receiving_yards_2q	Receiving yards in second quarter
receiving_yards_3q	Receiving yards in third quarter
receiving_yards_4q	Receiving yards in fourth quarter
receptions	Total receptions
rushing_attempts	Total rushing attempts
rushing_receiving_yards	Combined rushing + receiving yards
rushing_yards	Total rushing yards
rushing_yards_1h