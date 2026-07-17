import os
import sqlite3
import cfbd
import time
from collections import defaultdict
from dotenv import load_dotenv

# call load_env function
load_dotenv()
# extracting API key
raw_key = os.getenv("CFBD_API_KEY")
if not raw_key:
    print("Error: 'CFBD_API_KEY' not found in .env")
else:
    print("API Key successfully pulled from .env file")

# CFBD API Authorization
configuration = cfbd.Configuration(
    access_token = raw_key
)

# global connection variable
connection = sqlite3.connect("cfb_analytics.db")

# connects to cfbd API
api_client = cfbd.ApiClient(configuration)

def fetch_recruiting_years(year, connection):
    cursor = connection.cursor()
    # connects to recruiting section of API
    recruiting_api = cfbd.RecruitingApi(api_client)
    try:
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
    except Exception as e:
        print("Error: {}".format(e))
    finally:
        connection.commit()

def fetch_records(year, connection):
    cursor = connection.cursor()
    # connects to recruiting section of API
    games_api = cfbd.GamesApi(api_client)
    try:
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
    except Exception as e:
        print("Error: {}".format(e))
    finally:
        connection.commit()

def fetch_expected_performance(year, connection):
    cursor = connection.cursor()
    # connects to recruiting section of API
    games_api = cfbd.GamesApi(api_client)
    try:
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
    except Exception as e:
        print("Error: {}".format(e))
    finally:
        connection.commit()

def fetch_games(year, connection):
    games_api = cfbd.GamesApi(api_client)
    cursor = connection.cursor()
    try:
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
        
    except Exception as e:
        print(f"Error fetching games for {year}: {e}")

def fetch_transfer_portal(year, connection):
    cursor = connection.cursor()
    # connects to recruiting section of API
    if year < 2021:
        return
    players_api = cfbd.PlayersApi(api_client)
    try:
        print("Fetching data from {}...".format(year))
        api_response = players_api.get_transfer_portal(year=year)
        team_summary = defaultdict(lambda: {"in":0, "out": 0, "net_rating": 0.0})
        for row in api_response:
            star = row.stars if row.stars else 0
            rating = row.rating if row.rating else 0.0
            if row.origin:
                team_summary[row.origin]["out"] += 1
                team_summary[row.origin]["net_rating"] -= rating if rating > 0 else (star * 0.02)
            if row.destination:
                team_summary[row.destination]["in"] += 1
                team_summary[row.destination]["net_rating"] += rating if rating > 0 else (star * 0.02)
        for team, stats in team_summary.items():
            cursor.execute(
                "INSERT OR REPLACE INTO transfer_portal \
                    (team, year, players_in, players_out, net_rating) VALUES (?, ?, ?, ?, ?)",
                (team, year, stats["in"], stats["out"], round(stats["net_rating"], 3))
            )
        print("Successfully saved {} transfer portal stats to database".format(len(api_response)))
    except Exception as e:
        print("Error: {}".format(e))
    finally:
        connection.commit()

def run_backfill_pipeline(start_year, end_year):
    connection = sqlite3.connect("cfb_analytics.db")
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
    