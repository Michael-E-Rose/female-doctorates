"""Loads relevant dissertation data from source."""

import tomllib
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests
import spacy
from dotenv import dotenv_values
from tqdm import tqdm

with open("./config.toml", "rb") as f:
    config = tomllib.load(f)

SOURCE_FILE_URL = config["datasets"]["hochschulschriften"]
DISSERTATIONS_FILE = Path(config["paths"]["dissertations_file"])
REPLACEMENT_FILE = Path(config["paths"]["substitutions_file"])
TABLES_FOLDER = Path(config["paths"]["tables_dir"])
FIGURES_FOLDER = Path(config["paths"]["figures_dir"])
MODEL_NAME = config["models"]["noun_phrases"]
STATISTICS_DIR = Path(config["paths"]["statistics_dir"])

MIN_YEAR = 1890
MAX_YEAR = 1912

dotenv = dotenv_values()
tqdm.pandas()


def clean_sentences(text, model):
    """Remove locational sentences from text."""
    doc = model(text)
    sentences = list(doc.sents)
    if len(sentences) == 1:
        return text
    else:
        sentences = [sent.text for sent in sentences if not sent.text.startswith("Aus d")]
    return " ".join(sentences)


def read_hochschulschriften():
    """Read hochschulschriften main file."""
    headers = {
        "Authorization": f"token {dotenv['GITHUB_API']}",
        "Accept": "application/vnd.github.v3.raw"
    }
    response = requests.get(SOURCE_FILE_URL + "works.parquet", headers=headers)
    cols = ['id', 'uuid', 'volume', 'page', 'year', 'Hochschule', 'Fakultät',
            'faculty', 'Staatsangehörigkeit', 'discipline', 'Vorbildung',
            'Studium', 'Beruf', 'Titel', 'language', 'Schriftentyp', 'Einreichung',
            'Referenten', 'Prüfungstag']
    works = pd.read_parquet(BytesIO(response.content), columns=cols)
    response = requests.get(SOURCE_FILE_URL + "authors.parquet", headers=headers)
    cols = ['uuid', 'female', 'Wikipedia']
    authors = pd.read_parquet(BytesIO(response.content), columns=cols)
    return works.join(authors, on="uuid")


def write_stats(stat_dct):
    """Write out textfiles as "filename: content" pair."""
    for key, cont in stat_dct.items():
        fname = Path(STATISTICS_DIR, key).with_suffix(".txt")
        fname.write_text(f"{int(cont):,}")


if __name__ == '__main__':
    # Read file
    print("Reading 'hochschulschriften' data from GitHub...")
    df = read_hochschulschriften()
    df = df.rename(columns={"Hochschule": "University"})

    # Subset
    df = df[df["University"].str.startswith("U ")]
    df = df[df["year"].between(MIN_YEAR, MAX_YEAR)]
    df = df[~df["faculty"].isin({"Theology", "Medicine"})]
    df = df[~df["Schriftentyp"].isin({"Habilitations-Schrift", "Habilitationsschrift"})]
    df = df.drop(columns="Schriftentyp")

    # Clean titles
    corrections = {"Ueber": "Über", "—": "-", "Kenntniss": "Kenntnis",
                   "Verhältniss": "Verhältnis", "theil": "teil",
                   "speciell": "speziell", "'(": "(", ")'": ")",
                   "’": "'", "äusser": "äußer", "Instiut [!]": "Institut"}
    for old, new in corrections.items():
        df["Titel"] = df["Titel"].str.replace(old, new)
    abbreviations = pd.read_csv(REPLACEMENT_FILE, index_col=0)["new"].to_dict()
    for short, long in abbreviations.items():
        df["Titel"] = df["Titel"].str.replace(short, long)

    # Remove locational sentences
    print("Cleaning titles...")
    nlp = spacy.load(MODEL_NAME)
    df["Titel"] = df["Titel"].progress_apply(clean_sentences, model=nlp)

    # Write out
    df["University"] = df["University"].str.replace("U ", "")
    df.to_csv(DISSERTATIONS_FILE)
    print(f"... found {df.shape[0]:,} dissertations by {df['female'].sum():,} women")

    # Statistics
    stats = {"N_dissertations": df.shape[0],
             "N_women": df['female'].sum()}
    write_stats(stats)
