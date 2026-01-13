"""Extracts student data from dissertation entries (education, school, etc.)."""

import tomllib
from pathlib import Path

import pandas as pd
import re
from numpy import nan

with open("./config.toml", "rb") as f:
    config = tomllib.load(f)

DISSERTATIONS_FILE = Path(config["paths"]["dissertations_file"])
INSTITUTE_FILE = Path(config["paths"]["university_dir"]) / "geocoordinates.csv"
TARGET_FILE = Path(config["paths"]["characteristics_file"])

_thuringia = {
    'Reuß ä. L.',
    'Reuß j. L.'
    'Sachsen-Altenburg',
    'Sachsen-Coburg',
    'Sachsen-Coburg und Gotha',
    'Sachsen-Meiningen',
    'Sachsen-Weimar-Eisenach',
    'Schaumburg-Lippe',
    'Schwarzburg-Rudolstadt',
    'Schwarzburg-Sondershausen',
    'Thüringen'
}
_mecklenburg = {
    'Mecklenburg-Schwerin',
    'Mecklenburg-Strelitz',
    'Mecklenburg'
}

def get_locations(studies):
    """Extract locations from studies."""
    try:
        if studies.endswith("S."):
            studies = studies[:-2].strip()
    except AttributeError:
        return set()
    locations = studies.split(", ")
    locations = [re.sub(r'\s*\d+\s*', ' ', s).strip() for s in locations]
    return set(locations)


if __name__ == '__main__':
    # Read in
    cols = ["id", "uuid", "University", "discipline", "year", "Vorbildung",
            "Staatsangehörigkeit", "Studium"]
    df = pd.read_csv(DISSERTATIONS_FILE, usecols=cols, index_col="id")

    # Indicate school
    mask = df["Vorbildung"].notna()
    pat = re.compile(r'(?i)gymn\.?|gym\.?(?!\w)', re.IGNORECASE)
    df.loc[mask, "Gymnasium"] = df["Vorbildung"].str.contains(pat).astype("Int8")

    # Mark domestic students
    citizens = df[["University", "Staatsangehörigkeit"]].dropna()
    citizens["Staatsangehörigkeit"] = citizens["Staatsangehörigkeit"].str.replace(" u.", ",")
    data = pd.read_csv(INSTITUTE_FILE, index_col="university")
    citizens = citizens.join(data[["territory"]], on="University")
    citizens["Staatsangehörigkeit"] = citizens["Staatsangehörigkeit"].str.split(", ")
    citizens = citizens.explode("Staatsangehörigkeit")
    citizens["domestic"] = (citizens["Staatsangehörigkeit"] != citizens["territory"]).astype("Int8")
    jena = citizens["University"] == "Jena"
    citizens.loc[jena, "domestic"] = citizens.loc[jena, "Staatsangehörigkeit"].isin(_thuringia).astype("Int8")
    rostock = citizens["University"] == "Rostock"
    citizens.loc[rostock, "domestic"] = citizens.loc[rostock, "Staatsangehörigkeit"].isin(_mecklenburg).astype("Int8")
    citizens = citizens.sort_values("domestic", ascending=False)
    citizens = citizens[~citizens.index.duplicated()]["domestic"]
    df = df.join(citizens)

    # Count studies
    mask = df["Studium"].notna()
    df.loc[mask, "n_study"] = df["Studium"].apply(get_locations).str.len()
    pat = re.compile(r'(?<!\w)(?:Techn\.|T\W*H\.)(?!\w)', re.IGNORECASE)
    df.loc[mask, "technical"] = df["Studium"].str.contains(pat, na=False).astype("Int8")

    # Write out
    cols = ["Gymnasium", "domestic", "n_study", "technical"]
    df[cols].to_csv(TARGET_FILE, float_format="%.0f")
