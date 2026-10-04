import os
import sys
import sqlite3
import cfbd
import time
from collections import defaultdict
from dotenv import load_dotenv
from db_setup import DB_PATH

# call load_env function
load_dotenv()
# extracting API key
raw_key = os.getenv("CFBD_API_KEY")
if not raw_key:
    sys.exit("Error: 'CFBD_API_KEY' not found in .env")
print("API Key successfully pulled from .env file")

# CFBD API Authorization
configuration = cfbd.Configuration(
    access_token = raw_key
)

# connects to cfbd API
api_client = cfbd.ApiClient(configuration)

def fetch_recruiting_years(year, connection):
    cursor = connection.cursor()
    # connects to recruiting section of API
    recruiting_api = cfbd.RecruitingApi(api_client)
    print("Fetching data from {}...".format(year))
    api_response = recruiting_api.get_team_recruiting_rankings(year=year)
    for row in api_response:
        team_name = row.team
        point_val = row.points
        # Inserts team data as tuples
        cursor.execute(
            "INSERT OR REPLACE INTO recruiting (team, year, points) VALUES (?, ?, ?)",
            (team_name, year, point_val)
        )
    print("Successfully saved {} recruiting stats to database".format(len(api_response)))

def fetch_records(year, connection):
    cursor = connection.cursor()
    # connects to recruiting section of API
    games_api = cfbd.GamesApi(api_client)
    print("Fetching data from {}...".format(year))
    api_response = games_api.get_records(year=year)
    for row in api_response:
        team_name = row.team
        wins = row.total.wins
        losses = row.total.losses
        # Inserts team data as tuples
        cursor.execute(
            "INSERT OR REPLACE INTO record (team, year, wins, losses) VALUES (?, ?, ?, ?)",
            (team_name, year, wins, losses)
        )
    print("Successfully saved {} team record stats to database".format(len(api_response)))

def fetch_expected_performance(year, connection):
    cursor = connection.cursor()
    # connects to recruiting section of API
    games_api = cfbd.GamesApi(api_client)
    print("Fetching data from {}...".format(year))
    api_response = games_api.get_records(year=year)
    for row in api_response:
        team_name = row.team
        wins = row.total.wins
        expected_wins = row.expected_wins
        # Inserts team data as tuples
        cursor.execute(
            "INSERT OR REPLACE INTO performance (team, year, expected_wins, actual_wins) \
                 VALUES (?, ?, ?, ?)",
            (team_name, year, expected_wins, wins)
        )
    print("Successfully saved {} performance stats to database".format(len(api_response)))

def fetch_games(year, connection):
    games_api = cfbd.GamesApi(api_client)
    cursor = connection.cursor()
    print(f"Fetching games for season {year}...")
    api_response = games_api.get_games(year=year)

    saved_count = 0
    for row in api_response:
        if row.home_points is None or row.away_points is None:
            continue
        is_postseason = 1 if row.season_type == "postseason" else 0

        cursor.execute("""
            INSERT OR REPLACE INTO games (
                game_id, year, week, home_team, away_team, home_points, away_points, postseason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row.id, 
            year, 
            row.week, 
            row.home_team, 
            row.away_team, 
            row.home_points, 
            row.away_points, 
            is_postseason
        ))
        saved_count += 1

    print(f"-> Successfully saved {saved_count} completed games for {year}.")

# Fallback rating for transfers with stars but no rating: the median CFBD rating
# of rated transfers at each star level (2021-2025). 1-star has no rated players,
# so it's extrapolated. Unrated players with no stars contribute 0.
STAR_RATING_FALLBACK = {1: 0.75, 2: 0.79, 3: 0.85, 4: 0.91, 5: 0.98}

def player_rating(stars, rating):
    if rating:
        return rating
    return STAR_RATING_FALLBACK.get(stars or 0, 0.0)

def summarize_transfers(transfers):
    team_summary = defaultdict(lambda: {"in":0, "out": 0, "net_rating": 0.0})
    for row in transfers:
        value = player_rating(row.stars, row.rating)
        if row.origin:
            team_summary[row.origin]["out"] += 1
            team_summary[row.origin]["net_rating"] -= value
        if row.destination:
            team_summary[row.destination]["in"] += 1
            team_summary[row.destination]["net_rating"] += value
    return team_summary

def fetch_transfer_portal(year, connection):
    cursor = connection.cursor()
    # connects to recruiting section of API
    if year < 2021:
        return
    players_api = cfbd.PlayersApi(api_client)
    print("Fetching data from {}...".format(year))
    api_response = players_api.get_transfer_portal(year=year)
    team_summary = summarize_transfers(api_response)
    for team, stats in team_summary.items():
        cursor.execute(
            "INSERT OR REPLACE INTO transfer_portal \
                (team, year, players_in, players_out, net_rating) VALUES (?, ?, ?, ?, ?)",
            (team, year, stats["in"], stats["out"], round(stats["net_rating"], 3))
        )
    print("Successfully saved {} transfer portal stats to database".format(len(api_response)))

def fetch_team_conference(year, connection):
    cursor = connection.cursor()
    teams_api = cfbd.TeamsApi(api_client)
    print("Fetching data from {}...".format(year))
    api_response = teams_api.get_fbs_teams(year=year)
    for row in api_response:
        school = row.school
        conference = row.conference
        logo = row.logos[0] if row.logos else None
        # Inserts team data as tuples
        cursor.execute(
            "INSERT OR REPLACE INTO team_conference (team, year, conference) VALUES (?, ?, ?)",
            (school, year, conference)
        )
        cursor.execute(
            "INSERT OR REPLACE INTO logos (team, logo_url) VALUES (?, ?)",
            (school, logo)
        )
    print("Successfully saved {} team record stats to database".format(len(api_response)))

def run_static_pipeline(start_year, end_year):
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    print("Bulk ingesting from {} to {}.".format(start_year, end_year))
    for cur_year in range(start_year, end_year+1):
        cursor.execute("SELECT COUNT(*) FROM team_conference WHERE year = ?", (cur_year,))
        data_exists = cursor.fetchone()[0] > 0
        if data_exists:
            continue
        print("Processing {} logos".format(cur_year))
        try:
            fetch_team_conference(cur_year, connection)
            connection.commit()
            print("{} successfully saved".format(cur_year))
        except Exception as e:
            print("Error processing {}: {}".format(cur_year, e))
            connection.rollback()
            continue
        time.sleep(1.5)
    connection.close()
    print("Static pipeline execution complete.")

def run_backfill_pipeline(start_year, end_year):
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    print("Bulk ingesting from {} to {}.".format(start_year, end_year))
    for cur_year in range(start_year, end_year+1):
        cursor.execute("SELECT COUNT(*) FROM recruiting WHERE year = ?", (cur_year,))
        data_exists = cursor.fetchone()[0] > 0
        if data_exists:
            continue
        print("Processing {} season".format(cur_year))
        try:
            fetch_recruiting_years(cur_year, connection)
            fetch_records(cur_year, connection)
            fetch_expected_performance(cur_year, connection)
            fetch_games(cur_year, connection)
            fetch_transfer_portal(cur_year, connection)
            connection.commit()
            print("{} successfully saved".format(cur_year))
        except Exception as e:
            print("Error processing {}: {}".format(cur_year, e))
            connection.rollback()
            continue
        time.sleep(1.5)
    connection.close()
    print("Pipeline execution complete.")

if __name__ == "__main__":
    run_backfill_pipeline(start_year=2018, end_year=2025)
    run_static_pipeline(start_year=2018, end_year=2025)
