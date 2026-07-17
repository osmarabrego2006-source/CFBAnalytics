from analysis import df_final

columns_to_show = ['team', 'year', 'expected_wins', 'organic_talent_index', 'wins',\
                        'losses', 'net_rating', 'sos', 'close_games']
# Filter to look at a small sample slice of verified records
print(df_final[columns_to_show].dropna().head(15))