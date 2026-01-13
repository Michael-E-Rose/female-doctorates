"""Prepares master file with dissertation-specific data."""

import tomllib
from pathlib import Path

import pandas as pd

with open("./config.toml", "rb") as f:
    config = tomllib.load(f)

DISSERTATIONS = Path(config["paths"]["dissertations_file"])
UNIVERSITY_DIR = Path(config["paths"]["university_dir"])
STUDENTS_FILE = Path(config["paths"]["characteristics_file"])
NOVELTY_FILE = Path(config["paths"]["novelty_file"])
TARGET_FILE = Path(config["paths"]["dissertations_master"]) / "individual.csv"


if __name__ == '__main__':
    # Read dissertations
    cols = ["id", "year", "University", "discipline", "faculty",
            "female", "Wikipedia", "language"]
    df = pd.read_csv(DISSERTATIONS, index_col="id", usecols=cols)
    mask = df["faculty"] == "Law"
    df.loc[mask, "discipline"] = "law"
    df["discipline"] = df["discipline"].fillna("philology")

    # Merge states
    states = pd.read_csv(UNIVERSITY_DIR / "geocoordinates.csv", index_col=0,
                         usecols=["university", "territory"])
    df = df.join(states, on="University")

    # Add student characteristics
    students = pd.read_csv(STUDENTS_FILE, index_col=0)
    df = df.join(students)

    # Estimate language
    df["german"] = (df["language"] == "German").astype("uint8")
    df = df.drop(columns="language")

    # Add novelty estimate
    cols =["id", "novel", "num_phrases"]
    novelty = pd.read_csv(NOVELTY_FILE, usecols=cols, index_col=cols[0])
    df = df.join(novelty)

    # Merge treatment indicators
    treatment = pd.read_csv(UNIVERSITY_DIR / "admissions.csv", index_col=0)
    treatment = treatment.rename(columns={"year": "treatment"})
    df = df.join(treatment, on="territory")
    assert df["treatment"].isna().sum() == 0
    df["post"] = (df["year"] > df["treatment"]).astype("uint8")

    # Write out
    df.to_csv(TARGET_FILE, float_format="%.0f")
