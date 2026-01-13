"""Estimates novelty of dissertations."""

import tomllib
from pathlib import Path

import pandas as pd
import spacy
from tqdm import tqdm

from _100_load_hochschulschriften import write_stats

with open("./config.toml", "rb") as f:
    config = tomllib.load(f)

DISSERTATIONS = Path(config["paths"]["dissertations_file"])
TARGET_FILE = Path(config["paths"]["novelty_file"])
MODEL_NAME = config["models"]["noun_phrases"]
MAINTENANCE_FOLDER = Path(config["paths"]["maintenance_dir"])
FIGURES_FOLDER = Path(config["paths"]["figures_dir"])

tqdm.pandas()


def expost_cleaning(phrases):
    """Remove phrases containing clutter."""
    clutter = {"Prof", "Dr", "Hrn"}
    numbers = {"eins", "zwei", "drei", "vier", "fünf", "sechs", "sieben",
               "acht", "neun", "zehn", "elf", "zwölf"}
    clean = []
    for phrase in phrases:
        if not phrase:
            continue
        if any(c in phrase for c in clutter):
            continue
        if phrase.split()[0].lower() == "über":
            continue
        if phrase.split()[0].lower() in numbers:
            continue
        if phrase.lower().startswith("( aus d"):
            continue
        if phrase[0].isdigit():
            continue
        clean.append(phrase.strip("(„'").strip())
    return set(clean)


def extract_noun_phrases(text, model):
    """Extract noun phrases from text."""
    doc = model(text)
    clean_phrases = []
    for chunk in doc.noun_chunks:
        lemmas = [token.lemma_ for token in chunk
                  if token.pos_ != "DET" or token.i != chunk.start]
        lemmas = " ".join([w for w in lemmas if not w == "--"])  # parentheses, etc.
        clean_phrases.append(lemmas)
    return clean_phrases


if __name__ == '__main__':
    # Read dissertations
    cols = ["id", "Titel", "year", "language"]
    df = pd.read_csv(DISSERTATIONS, usecols=cols, index_col="id")
    df = df[df["language"] == "German"].drop(columns="language")
    df["Titel"] = df["Titel"].str.replace("[!]", "")

    # Extract noun phrases from dissertations
    nlp = spacy.load(MODEL_NAME, exclude=["attribute_ruler", "ner"])
    print("Extracting noun phrases....")
    df["noun_phrases"] = df["Titel"].progress_apply(extract_noun_phrases, model=nlp)
    df["noun_phrases"] = df["noun_phrases"].apply(expost_cleaning)

    # Estimate novelty
    known_phrases = set()
    for year, subset in df.groupby("year"):
        subset["novel_phrases"] = subset["noun_phrases"].apply(lambda x: x - known_phrases)
        df.loc[subset.index, "novel_phrases"] = subset["novel_phrases"]
        new_phrases = subset["novel_phrases"].explode().unique()
        known_phrases.update(new_phrases)
    df["novel"] = (df["novel_phrases"].str.len() > 0).astype("uint8")
    df["num_phrases"] = df["noun_phrases"].str.len().fillna(0).astype("uint16")

    # Maintenance
    novel_phrases = df["novel_phrases"].explode().dropna()
    novel_phrases = (novel_phrases.reset_index()
                                  .sort_values(by=["id", "novel_phrases"]))
    novel_phrases.to_csv(MAINTENANCE_FOLDER / "210_novel_phrases.csv", index=False)
    print(f"Found {novel_phrases.shape[0]:,} novel noun phrases in dissertations")

    # Write out
    df = df.drop(columns=["noun_phrases", "novel_phrases"])
    df.to_csv(TARGET_FILE, float_format="%.0f")

    # Statistics
    stats = {"novel_N_novel": df["novel"].sum(),
             "novel_N_terms": novel_phrases.shape[0]}
    write_stats(stats)
