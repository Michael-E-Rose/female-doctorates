"""Prepares regression master for university-year panel."""

import tomllib
from pathlib import Path

import itertools
import pandas as pd

from _100_load_hochschulschriften import write_stats

with open("./config.toml", "rb") as f:
    config = tomllib.load(f)

DISSERTATIONS_FILE = Path(config["paths"]["dissertations_file"])
UNIVERSITY_DIR = Path(config["paths"]["university_dir"])
TARGET_FILE = Path(config["paths"]["dissertations_master"]) / "cohort.csv"


def compute_counts(data, agg_cols, label):
    """Compute the number of rows along the given columns."""
    return (data.groupby(agg_cols).size()
                .reset_index(name=label))


def generate_combinations(group, year_min, year_max):
    """Generate all combinations of year and discipline for a given university."""
    disciplines = group['discipline'].unique()
    years = range(year_min, year_max + 1)
    data = {
        'University': group['University'].iloc[0],
        'year': [year for year in years for _ in disciplines],
        'discipline': [discipline for _ in years for discipline in disciplines]
    }
    return pd.DataFrame(data).sort_values(["year", "discipline"])


if __name__ == '__main__':
    # Read file
    df = pd.read_csv(DISSERTATIONS_FILE, index_col=0)
    mask = df["faculty"] == "Law"
    df.loc[mask, "discipline"] = "law"
    df["discipline"] = df["discipline"].fillna("philology")

    # Generate balanced panel
    universities = sorted(df['University'].unique())
    years = df["year"].unique()
    disciplines = df['discipline'].unique()
    panel = pd.DataFrame(
        list(itertools.product(universities, years, disciplines)),
        columns=['University', 'year', 'discipline']
    )
    cols = list(panel.columns)

    # Merge states
    states = pd.read_csv(UNIVERSITY_DIR / "geocoordinates.csv", index_col=0,
                         usecols=["university", "territory"])
    panel = panel.join(states, on="University")

    # Merge counts
    diss_count = compute_counts(df, cols, "diss_count")
    panel = panel.merge(diss_count, on=cols, how="left")
    panel["diss_count"] = panel["diss_count"].fillna(0).astype("uint8")
    fem_count = compute_counts(df[df["female"] == 1], cols, "fem_count")
    panel = panel.merge(fem_count, on=cols, how="left")
    panel["fem_count"] = panel["fem_count"].fillna(0).astype("uint8")

    # Merge treatment indicators
    treatment = pd.read_csv(UNIVERSITY_DIR / "admissions.csv", index_col=0)
    treatment = treatment.rename(columns={"year": "treatment"})
    panel = panel.join(treatment, on="territory")
    assert panel["treatment"].isna().sum() == 0
    panel["post"] = (panel["year"] > panel["treatment"]).astype("uint8")

    # Write out
    print(f"Writing out {panel.shape[0]:,} observations")
    panel.to_csv(TARGET_FILE, index=False)
    write_stats({"doctor_N_obs": panel.shape[0]})
