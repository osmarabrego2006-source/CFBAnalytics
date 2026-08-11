from analysis import merge_datasets, compute_correlations
from analysis import get_conferences, get_teams_by_conference, get_logo
import streamlit as st
import altair as alt
import requests
from io import BytesIO
from PIL import Image

alt.renderers.set_embed_options(actions=False)

CONFERENCE_LOGOS = {"SEC": "https://content.sportslogos.net/logos/153/4667/full/southeastern_conference_logo_primary_2018_sportslogosnet-5123.png", 
                    "American Athletic": "https://content.sportslogos.net/logos/153/5032/full/american_athletic_conference_logo_primary_20178032.png",
                    "Mountain West": "https://content.sportslogos.net/logos/153/4665/full/mountain_west_conference_logo_primary_20111652.png",
                    "Big Ten": "https://content.sportslogos.net/logos/153/4661/full/big_ten_conference_logo_primary_20115933.png",
                    "Conference USA": "https://content.sportslogos.net/logos/153/4663/full/conference_usa_logo_primary_2023_sportslogosnet-4562.png",
                    "Big 12": "https://content.sportslogos.net/logos/153/4662/full/big_12_conference_logo_alternate_20188833.png",
                    "Mid-American": "https://content.sportslogos.net/logos/153/4664/full/mid-american_conference_logo_primary_2008_sportslogosnet-6826.png",
                    "Sun Belt": "https://content.sportslogos.net/logos/153/4668/full/sun_belt_conference_logo_primary_20207257.png",
                    "ACC": "https://content.sportslogos.net/logos/153/4659/full/atlantic_coast_conference_logo_primary_20146189.png",
                    "Pac-12": "https://content.sportslogos.net/logos/153/4666/full/pacific-12-conference-logo-primary-2026-466661912026.png",
                    "FBS Independents": "https://logos-world.net/wp-content/uploads/2025/01/Division-I-FBS-Independents-Logo-500x281.png"}

FBS_LOGO = "https://upload.wikimedia.org/wikipedia/en/thumb/c/cf/NCAA_football_icon_logo.svg/500px-NCAA_football_icon_logo.svg.png?utm_source=en.wikipedia.org&utm_campaign=parser&utm_content=thumbnail"

@st.cache_data
def load_master_data():
    return merge_datasets()

LOGO_BOX_SIZE = 200
LOGO_PADDING = 20

@st.cache_data
def get_logo_on_white(url):
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        logo = Image.open(BytesIO(response.content)).convert("RGBA")
        logo.thumbnail((LOGO_BOX_SIZE - LOGO_PADDING, LOGO_BOX_SIZE - LOGO_PADDING), Image.LANCZOS)
        background = Image.new("RGBA", (LOGO_BOX_SIZE, LOGO_BOX_SIZE), "white")
        offset = ((LOGO_BOX_SIZE - logo.width) // 2, (LOGO_BOX_SIZE - logo.height) // 2)
        background.paste(logo, offset, mask=logo)
        return background.convert("RGB")
    except Exception:
        return None

CHART_SURFACE = "#2e2d2a"
CHART_GRIDLINE = "#454440"
CHART_AXIS = "#5c594f"
CHART_MUTED = "#898781"
CHART_INK = "#ffffff"
CHART_FONT = "monospace"

DISPLAY_NAMES = {
    "team": "Team",
    "year": "Year",
    "wins": "Wins",
    "expected_wins": "Expected Wins",
    "organic_talent_index": "Organic Talent Index",
    "net_rating": "Transfer Portal Net Rating",
    "sos": "Strength of Schedule",
    "close_games_net": "Close Games Net",
}

def apply_chart_theme(chart):
    return (
        chart
        .configure_view(strokeWidth=0, fill=CHART_SURFACE)
        .configure(background=CHART_SURFACE)
        .configure_axis(
            grid=True,
            gridColor=CHART_GRIDLINE,
            gridDash=[1, 0],
            domainColor=CHART_AXIS,
            tickColor=CHART_AXIS,
            labelColor=CHART_MUTED,
            titleColor=CHART_MUTED,
            labelFont=CHART_FONT,
            titleFont=CHART_FONT,
        )
        .configure_title(color=CHART_INK, font=CHART_FONT, fontSize=14, anchor="start")
        .configure_legend(
            labelColor=CHART_MUTED,
            titleColor=CHART_MUTED,
            labelFont=CHART_FONT,
            titleFont=CHART_FONT,
            orient="top",
        )
    )

def get_team_chart_df(team):
    df = load_master_data()
    team_df = df[df["team"] == team].sort_values("year").reset_index(drop=True)
    chart_df = team_df[["team", "year", "wins", "expected_wins", "organic_talent_index", "net_rating"]].rename(columns=DISPLAY_NAMES)
    chart_df.index = [""] * len(chart_df)
    return chart_df

def trend_word(series):
    if series.iloc[-1] > series.iloc[0]:
        return "increased"
    if series.iloc[-1] < series.iloc[0]:
        return "decreased"
    return "stayed flat"

def render_team_summary(team, chart_df):
    stat_cols = ["Wins", "Organic Talent Index", "Transfer Portal Net Rating"]
    cols = st.columns(3)
    for col, stat in zip(cols, stat_cols):
        series = chart_df[stat]
        with col:
            st.metric(
                stat,
                f"{series.iloc[-1]:.1f}",
                delta=f"{series.iloc[-1] - series.iloc[0]:+.1f} since {int(chart_df['Year'].iloc[0])}",
            )
            st.caption(f"Range: {series.min():.1f} – {series.max():.1f}")
    first_year, last_year = int(chart_df["Year"].min()), int(chart_df["Year"].max())
    best_wins = int(chart_df["Wins"].max())
    best_year = int(chart_df.loc[chart_df["Wins"] == best_wins, "Year"].iloc[0])
    portal_sum = chart_df["Transfer Portal Net Rating"].sum()
    portal_word = "net positive" if portal_sum > 0 else "net negative" if portal_sum < 0 else "roughly neutral"
    st.write(
        f"From {first_year} to {last_year}, {team}'s win total {trend_word(chart_df['Wins'])}, "
        f"peaking at {best_wins} wins in {best_year}. Recruiting talent "
        f"(Organic Talent Index) {trend_word(chart_df['Organic Talent Index'])} over the same span, "
        f"while transfer portal activity was {portal_word} overall."
    )
    st.divider()

def render_team_chart(chart_df):
    def line_chart(field, color):
        title = DISPLAY_NAMES[field]
        base = alt.Chart(chart_df).encode(
            x=alt.X("Year:O", title="Year"),
            y=alt.Y(f"{title}:Q", title=title),
        )
        line = base.mark_line(strokeWidth=2, color=color)
        points = base.mark_point(filled=True, size=70, color=color)
        end_label = base.transform_filter(
            alt.datum.Year == chart_df["Year"].max()
        ).mark_text(align="left", dx=8, dy=-8, color=CHART_INK, font=CHART_FONT).encode(
            text=alt.Text(f"{title}:Q", format=".1f")
        )
        tooltip_layer = base.mark_point(opacity=0, size=200).encode(
            tooltip=[
                alt.Tooltip("Year:O", title="Year"),
                alt.Tooltip(f"{title}:Q", title=title, format=".1f"),
            ]
        )
        return (line + points + tooltip_layer + end_label).properties(title=title, height=180)

    def wins_vs_expected_chart():
        color_scale = alt.Scale(domain=["Wins", "Expected Wins"], range=["#3987e5", CHART_MUTED])
        dash_scale = alt.Scale(domain=["Wins", "Expected Wins"], range=[[1, 0], [4, 3]])
        long_df = chart_df.melt(
            id_vars=["Year"], value_vars=["Wins", "Expected Wins"],
            var_name="Metric", value_name="Value",
        )
        base = alt.Chart(long_df).encode(
            x=alt.X("Year:O", title="Year"),
            y=alt.Y("Value:Q", title="Wins"),
            color=alt.Color("Metric:N", title=None, scale=color_scale),
            strokeDash=alt.StrokeDash("Metric:N", scale=dash_scale, legend=None),
        )
        line = base.mark_line(strokeWidth=2)
        points = base.mark_point(filled=True, size=70)
        tooltip_layer = base.mark_point(opacity=0, size=200).encode(
            tooltip=[
                alt.Tooltip("Year:O", title="Year"),
                alt.Tooltip("Metric:N", title="Metric"),
                alt.Tooltip("Value:Q", title="Value", format=".1f"),
            ]
        )
        end_label = base.transform_filter(
            alt.datum.Year == chart_df["Year"].max()
        ).mark_text(align="left", dx=8, dy=-8, font=CHART_FONT).encode(
            text=alt.Text("Value:Q", format=".1f"),
            color=alt.value(CHART_INK),
        )
        return (line + points + tooltip_layer + end_label).properties(title="Wins vs. Expected Wins", height=180)

    wins_chart = wins_vs_expected_chart()
    talent_chart = line_chart("organic_talent_index", "#d95926")
    portal_chart = line_chart("net_rating", "#199e70")

    combined = apply_chart_theme(
        alt.vconcat(wins_chart, talent_chart, portal_chart).resolve_scale(x="shared")
    )
    st.altair_chart(combined, use_container_width=True)


def render_league_view(df):
    correlations = compute_correlations(df)
    cols = st.columns(4)
    for col, (field, corr) in zip(cols, correlations.items()):
        with col:
            st.metric(DISPLAY_NAMES[field], f"{corr:.2f}")
    st.caption(
        "Correlation with Wins across all team-seasons (2021-2025). "
        "1.0 = perfectly predictive, 0 = no relationship, negative = inverse relationship."
    )
    st.divider()

    chart_df = df[["team", "year", "wins", "organic_talent_index", "net_rating"]].rename(columns=DISPLAY_NAMES)
    chart_df.index = [""] * len(chart_df)

    def scatter(field, color):
        title = DISPLAY_NAMES[field]
        return alt.Chart(chart_df).mark_circle(size=40, opacity=0.5, color=color).encode(
            x=alt.X(f"{title}:Q", title=title),
            y=alt.Y("Wins:Q", title="Wins"),
            tooltip=[
                alt.Tooltip("Team:N", title="Team"),
                alt.Tooltip("Year:O", title="Year"),
                alt.Tooltip(f"{title}:Q", title=title, format=".1f"),
                alt.Tooltip("Wins:Q", title="Wins"),
            ],
        ).properties(title=f"{title} vs. Wins", height=280)
    talent_scatter = scatter("organic_talent_index", "#3987e5")
    portal_scatter = scatter("net_rating", "#199e70")
    st.altair_chart(
        apply_chart_theme(alt.hconcat(talent_scatter, portal_scatter)),
        use_container_width=True,
    )

st.session_state.setdefault("view", "home")
st.session_state.setdefault("selected_conference", None)
st.session_state.setdefault("selected_team", None)
st.write("College Football Analytics Platform")

if st.session_state.view == "home":
    if st.button("View League-Wide Trends"):
        st.session_state.view = "league"
        st.rerun()
    st.divider()
    conferences = get_conferences()
    for i in range(0, len(conferences), 3):
        row = conferences[i:i+3]
        cols = st.columns(3)
        for col, conf in zip(cols, row):
            with col.container(border=True):
                logo_url = CONFERENCE_LOGOS.get(conf)
                if logo_url:
                    composited = get_logo_on_white(logo_url)
                    if composited:
                        st.image(composited, use_container_width=True)
                if st.button(conf, use_container_width=True):
                    st.session_state.selected_conference = conf
                    st.session_state.view = "conference"
                    st.rerun()
elif st.session_state.view == "conference":
    conf = st.session_state.selected_conference
    st.subheader(conf, anchor=False)
    if st.button("← Back"):
        st.session_state.view = "home"
        st.rerun()
    st.divider()
    teams = get_teams_by_conference(conf)
    for i in range(0, len(teams), 3):
        row = teams[i:i+3]
        cols = st.columns(3)
        for col, team in zip(cols, row):
            with col.container(border=True):
                logo = get_logo(team)
                if logo:
                    composited = get_logo_on_white(logo)
                    if composited:
                        st.image(composited, use_container_width=True)
                if st.button(team, use_container_width=True):
                    st.session_state.selected_team = team
                    st.session_state.view = "team"
                    st.rerun()
elif st.session_state.view == "team":
    if st.button("← Back"):
        st.session_state.view = "conference"
        st.rerun()
    st.divider()
    st.subheader(st.session_state.selected_team, anchor=False)
    team_chart_df = get_team_chart_df(st.session_state.selected_team)
    render_team_summary(st.session_state.selected_team, team_chart_df)
    render_team_chart(team_chart_df)
elif st.session_state.view == "league":
    if st.button("← Back"):
        st.session_state.view = "home"
        st.rerun()
    st.divider()
    st.subheader("League-Wide Trends", anchor=False)
    render_league_view(load_master_data())