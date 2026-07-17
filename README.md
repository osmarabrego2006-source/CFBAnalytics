# CFB Data Scraper

A side project asking a simple question: does recruiting talent actually translate to wins, and how much does the transfer portal change that equation? Everyone has opinions about which programs "overachieve" or "underachieve" relative to their recruiting. This is my attempt to put some numbers behind that.

## How it works

It pulls recruiting rankings, team records, game results, and transfer portal moves from the [CFBD API](https://collegefootballdata.com/) into a local SQLite database, then crunches that into a few derived stats; an organic talent index, strength of schedule, and close-game record to see which of them actually correlate with winning.

## The files

`- `db_setup.py` - sets up the SQLite tables, run once
- `ingest.py` - pulls from the CFBD API and backfills the database
- `analysis.py` - the actual analytics: joins everything together into one dataset
- `dashboard.py` - just prints a sample of that dataset for now, no real visualization yet
- `test_env.py` - quick sanity check that your API key works before you run anything real

## Getting it running

You'll need a free API key from CFBD. Install the dependencies:
```
pip install cfbd python-dotenv pandas
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
python ingest.py        # backfill historical data (edit the year range at the bottom if you want a different window)
python analysis.py      # build the merged dataset
```

## What's in the database

- **recruiting** - team, year, recruiting points (2018–2025)
- **record** - team, year, wins, losses
- **performance** - expected wins vs. actual wins, per CFBD's model
- **games** - every completed game, score included
- **transfer_portal** - players in/out and a net talent rating per team, per year

Recruiting data goes back to 2018 because I need multiple recruiting classes to estimate a team's talent in any given year (more on that below). Everything else only goes back to 2021, since that's roughly when the transfer portal became a real factor.

## The actual thinking behind it

The rough hypothesis is that a team's performance in a given year comes down to:

- **Strength of schedule** - average win % of who they played
- **"Organic" talent** - not just this year's recruiting class, but a weighted blend of the last four classes, since freshmen rarely start, juniors and redshirt sophomores are usually your core, and your best players often leave early. Right now that's a flat weighting (FR 20% / SO 30% / JR 35% / SR 15%), which is a simplification I want to revisit.
- **Blue chip ratio** - blue-chip recruits as a share of the whole class, since a team can have a low average ranking but still have a stacked top end
- **Transfer portal net rating** - how much talent a team gained or lost through the portal, since that's now a bigger lever than recruiting for some programs
- **Close games** - net one-score record, as a rough proxy for how much of a team's record is luck/clutch play rather than being the better team

Coaching stability and returning-player counts are on the list but not built yet.

## Where it stands

The pipeline and the analysis layer work end to end. I can pull data and get a merged dataset out. There's no real visualization yet; `dashboard.py` is a placeholder that just prints rows to confirm the join is doing what I expect.
