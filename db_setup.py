import sqlite3

def create_database():
    connection = sqlite3.connect("cfb_analytics.db")
    cursor = connection.cursor()

    print("--- Initializing Database ---")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recruiting(
            team TEXT,
            year INTEGER,
            points REAL,
            PRIMARY KEY (team, year)
        );
    """)
    print("Recruiting table verified/created.")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS record(
            team TEXT,
            year INTEGER,
            wins INTEGER,
            losses INTEGER,
            PRIMARY KEY (team, year)
        );       
    """)
    print("Team record table verified/created")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS performance(
            team TEXT,
            year INTEGER,
            expected_wins REAL,
            actual_wins INTEGER,
            PRIMARY KEY (team, year)
        );
    """)
    print("Performance table verified/created.")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS games(
            game_id INTEGER PRIMARY KEY,
            year INTEGER,
            week INTEGER,
            home_team TEXT,
            away_team TEXT,
            home_points INTEGER,
            away_points INTEGER,
            postseason INTEGER
        );
    """)
    print("Games table verified/created.")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transfer_portal(
            team TEXT,
            year INTEGER,
            players_in INTEGER,
            players_out INTEGER,
            net_rating FLOAT,
            PRIMARY KEY (team, year)
        );
    """)
    print("Transfer portal table verified/created.")

    connection.commit()
    connection.close()
    print("Database setup complete and connection successfully closed")

if __name__ == "__main__":
    create_database()