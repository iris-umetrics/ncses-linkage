#!/usr/bin/env python
# coding: utf-8

# # Overview
#
# This notebook contains code to clean and normalize person name data. It is designed to work with a source_names.csv file, which contains the following fields:
#
# 1. first_name: This should actually be a concatenation of a first name and a middle name, as per descriptions of the SED/SDR PII data structure
# 2. last_name: the last name
# 4. mob: month of birth
# 5. yob: year of birth
#
# Steps:
# 1. Pull in name file
# 2. Pull in nickname lookup file
# 3. Apply the name cleaning function to relevant fields
# 4. Apply the nickname normalization function to relevant fields
# 5. Output a production CSV to be passed to hashing script

# # Setup

from pathlib import Path
import string
import unidecode
import csv

# # Configuration

# Change the values within Path("...") to an absolute or relative file location
# e.g. Path("./data/rawdata.csv"); Path("C:/data/pii/prepped.csv"); Path("~/data.csv")

INPUT_FILE = Path("./source_names.csv").resolve(strict=True)

NICKNAME_LOOKUP = Path("./nickname_mapping.csv").resolve(strict=True)

OUTPUT_FILE = Path("./clean_names.csv").resolve()

NULL_VALUE = ""


def initial_name_field_clean(raw):
    working = raw
    # Strip unicode down to ascii (e.g. Ë becomes E; ñ becomes n)
    working = unidecode.unidecode_expect_ascii(working)
    # Make all lowercase
    return working.lower()


def final_name_field_clean(field):
    # Remove absolutely everything except the lowercase letters (via ASCII codes)
    return "".join(char for char in field if char in string.ascii_lowercase)


def clean_date_part(raw_input, minimum, maximum):
    # For months, minimum = 1 and maximum = 12
    # For years, any UMETRICS date prior to 1902 is a null. So we are using: 1902, 2010.
    # Strip out any leading zeros or nonsense
    try:
        numbered = int(raw_input)
    except (ValueError, TypeError):
        # Anything that cannot be converted to an integer returns null
        return NULL_VALUE
    if numbered not in range(minimum, maximum + 1):
        # Anything outside the acceptable range returns null
        return NULL_VALUE
    return str(numbered)


with INPUT_FILE.open(encoding="utf-8") as csvfile:
    reader = csv.DictReader(csvfile)
    input_table = (row for row in reader)
    # print(row["first_name"], row["last_name"], row["mob"], row["yob"])

    for row in input_table:
        initial_cleaning = {
            "first_middle": initial_name_field_clean(row["first_name"]),
            "last": initial_name_field_clean(row["last_name"]),
            "month": clean_date_part(row["mob"], 1, 12),
            "year": clean_date_part(row["yob"], 1902, 2010),
        }

        print(row)
        print(initial_cleaning)


# # Name Alias Lookup
# #
# # Many names have multiple aliases (e.g. Robert, Rob, Bob, etc.)
# # This section groups names based on common name-alias pairings,
# # then applies a single value to each group


# # Convert name values to lowercase
# lookup_input["raw_name"] = lookup_input["raw_name"].str.lower()
# lookup_input["name_group"] = lookup_input["name_group"].str.lower()


# # Join the alias table and the name table
# alias_working = name_working.merge(
#     lookup_input, how="left", left_on=fandmname, right_on="raw_name"
# )
# # Generate a flag to track the names impacted by the alias change for QA purposes
# alias_working["alias_impact_flag"] = np.where(
#     alias_working[fandmname] == alias_working["raw_name"], 1, 0
# )
# # Create a "first_nickname" field that contains the matching alias
# # The original cleaned first name is maintained so that matches can be run on both hashes
# alias_working["first_nickname"] = alias_working["name_group"].fillna(
#     alias_working[fandmname]
# )
# alias_working.drop(["raw_name", "name_group"], axis=1, inplace=True)


# # # Export CSV
# #
# # This script will create a file in the output directory named "clean_names.csv" that can be loaded into the hashing script. It can also generate a QC CSV for looking at the changes to the data.


# # Arrange the columns in order
# name_cleaned = alias_working[
#     [
#         fandmname,
#         "first_nickname",
#         "middle_names",
#         "middle_initial",
#         lname,
#         cname,
#         mob,
#         yob,
#     ]
# ]
# # Export production file
# name_cleaned.to_csv(output_directory + "clean_names.csv", encoding="utf_8", index=False)
