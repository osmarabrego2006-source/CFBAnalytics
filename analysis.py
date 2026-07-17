import sqlite3
import pandas as pd
from collections import defaultdict

connection = sqlite3.connect("cfb_analytics.db")

def get_recruiting(target_year):
    df_recruiting = pd.read_sql_query("SELECT * FROM recruiting WHERE year = ?", \
                                connection, params=[target_year])
    return df_recruiting

def get_record(target_year):
    df_record = pd.read_sql_query("SELECT * FROM record WHERE year = ?", \
                                connection, params=[target_year])
    return df_record

def get_expected_performance(target_year):
    df_performance = pd.read_sql_query("SELECT * FROM performance WHERE year = ?", \
                                connection, params=[target_year])
    return df_performance

def get_games(target_year):
    df_games = pd.read_sql_query(
        "SELECT year, home_team, away_team, home_points, away_points FROM games WHERE year = ?", 
        connection, params=[target_year]
    )
    return df_games

def get_transfer_portal(target_year):
    df_transfer_portal = pd.read_sql_query("SELECT * FROM transfer_portal WHERE year = ?", \
                                connection, params=[target_year])
    return df_transfer_portal

def get_points(target_team, target_year, df_recruiting):
    match = df_recruiting[(df_recruiting["team"] == target_team)& (df_recruiting["year"] == target_year)]
    return float(match["points"].values[0]) if not match.empty else 0.0

def get_organic_talent_index(team, year, df_recruiting):
    senior_class = year - 3
    junior_class = year - 2
    sophomore_class = year - 1
    freshmen_class = year
    r_freshmen = get_points(team, freshmen_class, df_recruiting)
    r_sophomore = get_points(team, sophomore_class, df_recruiting)
    r_junior = get_points(team, junior_class, df_recruiting)
    r_senior = get_points(team, senior_class, df_recruiting)
    organic_talent_index = (r_freshmen * 0.20) + (r_sophomore * 0.30) + (r_junior * 0.35) + (r_senior * 0.15)
    return organic_talent_index

def load_all_years():
    recruiting_frames = []
    for year in range(2018, 2026):
        df_year = get_recruiting(year)
        recruiting_frames.append(df_year)
    df_recruiting = pd.concat(recruiting_frames, ignore_index=True)
    record_frames = []
    performance_frames = []
    portal_frames = []
    games_frames = []
    for year in range(2021, 2026):
        record_frames.append(get_record(year))
        performance_frames.append(get_expected_performance(year))
        portal_frames.append(get_transfer_portal(year))
        games_frames.append(get_games(year))
    df_record = pd.concat(record_frames, ignore_index=True)
    df_performance = pd.concat(performance_frames, ignore_index=True)
    df_portal = pd.concat(portal_frames, ignore_index=True)
    df_games = pd.concat(games_frames, ignore_index=True)
    return df_recruiting, df_record, df_performance, df_portal, df_games

def calculate_matrix_sos(df_record, df_games):
    record_lookup = {}
    for _, row in df_record.iterrows():
        record_lookup[(int(row['year']), row['team'])] = (int(row['wins']), int(row['losses']))
    
    sos_records = []
    
    for year in df_games['year'].unique():
        df_year_games = df_games[df_games['year'] == year]
        
        team_opponents = {}
        for _, game in df_year_games.iterrows():
            home, away = game['home_team'], game['away_team']
            team_opponents.setdefault(home, []).append(away)
            team_opponents.setdefault(away, []).append(home)

        for team, opponents in team_opponents.items():
            opponent_win_percentages = []
            
            for opp in opponents:
                opp_record = record_lookup.get((year, opp), (0, 0))
                opp_wins, opp_losses = opp_record[0], opp_record[1]
                
                played_as_home = ((df_year_games['home_team'] == team) & (df_year_games['away_team'] == opp)).any()
                played_as_away = ((df_year_games['away_team'] == team) & (df_year_games['home_team'] == opp)).any()
                
                if played_as_home:
                    pass 
                
                total_opp_games = opp_wins + opp_losses
                if total_opp_games > 0:
                    win_pct = opp_wins / total_opp_games
                else:
                    win_pct = 0.5
                    
                opponent_win_percentages.append(win_pct)

            if opponent_win_percentages:
                mean_sos = sum(opponent_win_percentages) / len(opponent_win_percentages)
            else:
                mean_sos = 0.5
                
            sos_records.append({'year': year, 'team': team, 'sos': round(mean_sos, 4)})
    
    return pd.DataFrame(sos_records)

def calculate_close_games(df_games):
    close_net = defaultdict(int)
    close_games = []
    for _, row in df_games.iterrows():
        if abs(row['home_points'] - row['away_points']) <= 8:
            if row['home_points'] > row['away_points']:
                close_net[(int(row['year']), row['home_team'])] += 1
                if close_net[(int(row['year']), row['away_team'])] > 0: 
                    close_net[(int(row['year']), row['away_team'])] -= 1 
            else:
                close_net[(int(row['year']), row['away_team'])] += 1
                if close_net[(int(row['year']), row['home_team'])] > 0: 
                    close_net[(int(row['year']), row['home_team'])] -= 1 
    for (year, team), net in close_net.items():
        close_games.append({'year': year, 'team': team, 'close_games': net})
    return pd.DataFrame(close_games)      



def merge_datasets():
    df_recruiting, df_record, df_performance, df_portal, df_games = load_all_years()
    df_recruiting["year"] = df_recruiting["year"].astype(int)
    df_performance["year"] = df_performance["year"].astype(int)
    df_games["year"] = df_games["year"].astype(int)
    df_sos = calculate_matrix_sos(df_record, df_games)
    df_close_games = calculate_close_games(df_games)
    df_master = df_performance.copy()
    df_master["organic_talent_index"] = df_master.apply(
        lambda row: get_organic_talent_index(row["team"], row["year"], df_recruiting), axis = 1
    )

    df_master = pd.merge(df_master, df_record, on=["team", "year"], how="left")
    df_master = pd.merge(df_master, df_portal, on=["team", "year"], how="left")
    df_master = pd.merge(df_master, df_sos, on=["team", "year"], how="left")
    df_master = pd.merge(df_master, df_close_games, on=["team", "year"], how="left")
    return df_master

if __name__ == "__main__":
    print("Generating master transfer portal era analytics dataset...")
    df_final = merge_datasets()
    
    print("\n--- SAMPLE MASTER OUTPUT DATA ---")
    columns_to_show = ['team', 'year', 'expected_wins', 'organic_talent_index', 'wins',\
                        'losses', 'net_rating', 'sos', 'close_games']
    # Filter to look at a small sample slice of verified records
    print(df_final[columns_to_show].dropna().head(15))
    
    connection.close()