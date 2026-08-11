# CFB Data Scraper

A side project asking a simple question: does recruiting talent actually translate to wins, and how much does the transfer portal change that equation?

## How it works

It pulls recruiting rankings, team records, game results, transfer portal moves, and team/conference metadata from the CFBD API (https://collegefootballdata.com/) into a local SQLite database, then crunches that into a few derived stats - an organic talent index, strength of schedule, and close-game record - to see which of them actually correlate with winning. A Streamlit dashboard sits on top: pick a conference, pick a team, and see how that team's wins, recruiting talent, and transfer portal activity have moved together over time - plus a league-wide view showing how each of those stats actually correlates with wins across every team-season, which is the closest thing to an answer to this project's opening question right now.

## The files

- `db_setup.py` - sets up the SQLite tables, run once
- `ingest.py` - pulls from the CFBD API and backfills the database
- `analysis.py` - the analytics layer: joins everything into one dataset and exposes lookups the dashboard uses for navigation
- `dashboard.py` - the Streamlit app: conference → team → team stats, with charts and a summary
- `.streamlit/config.toml` - the app's color theme and font
- `test_env.py` - check that API key works before you run anything real

## Getting it running

You'll need a free API key from CFBD. Install the dependencies:
```
pip install cfbd python-dotenv pandas streamlit altair requests Pillow
```

Drop your key in a `.env` file:
```
CFBD_API_KEY=your_key_here
```

Then check the connection works:
```
python test_env.py
```

## Using it

```
python db_setup.py      # create the schema
python ingest.py        # backfill historical data + team/conference/logo metadata
python analysis.py      # sanity-check the merged dataset and print correlation with wins
streamlit run dashboard.py   # launch the dashboard
```

`ingest.py`'s year range is set at the bottom of the file if you want a different window than the current default.

## What's in the database

- **recruiting** - team, year, recruiting points (2018–2025)
- **record** - team, year, wins, losses
- **performance** - expected wins vs. actual wins, per CFBD's model
- **games** - every completed game, score included
- **transfer_portal** - players in/out and a net talent rating per team, per year
- **team_conference** - team, year, conference (year-scoped, since realignment happens)
- **logos** - team → logo URL (not year-scoped, since a team's logo doesn't change with realignment)

Recruiting data goes back to 2018 because I need multiple recruiting classes to estimate a team's talent in any given year (more on that below). Everything else only goes back to 2021, since that's roughly when the transfer portal became a real factor.

## The actual thinking behind it

The rough hypothesis is that a team's performance in a given year comes down to:

- **Strength of schedule** - average win % of who they played
- **"Organic" talent** - not just this year's recruiting class, but a weighted blend of the last four classes, since freshmen rarely start, juniors and redshirt sophomores are usually your core, and your best players often leave early. Right now that's a flat weighting (FR 20% / SO 30% / JR 35% / SR 15%), which is a simplification I want to revisit.
- **Transfer portal net rating** - how much talent a team gained or lost through the portal, since that's now a bigger lever than recruiting for some programs
- **Close games** - net one-score record (wins minus losses in games decided by 8 points or fewer), as a rough proxy for how much of a team's record is luck/clutch play rather than being the better team.

## Where it stands

The pipeline and analysis layer work end to end, including team/conference/logo metadata for navigation. The dashboard has four screens: pick a conference, pick a team, see that team's Wins, Organic Talent Index, and Transfer Portal Net Rating charted over time with a short auto-generated summary - or skip straight to a league-wide view showing correlation-with-wins for all four hypothesis variables (organic talent, transfer portal, strength of schedule, close games) across every team-season, plus scatter plots for the two biggest ones.
