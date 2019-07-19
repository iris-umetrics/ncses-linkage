#!/usr/bin/env python
# coding: utf-8
"""
IRIS-NCSES Name Cleaning Overview

This code cleans and normalizes name fields, month, and year of birth.
It takes in a source name CSV which contains the following:
    1. name_first_middle (concatenation of all given names: first(s) and/or middle(s))
    2. name_last (last name as provided by source)
    3. mob (month of birth)
    4. yob (year of birth)
Any other fields in the CSV will be ignored.

Key steps of this program:
    1. Create nickname lookup from nickname csv (NICKNAME_FILENAME)
    2. Pull the source data input (INPUT_FILENAME)
    3. Clean and normalize each field.
    4. Apply nickname lookup function to assign a first name group from first given name.
    5. Output OUTPUT_FILENAME in a CSV ready to be hashed.

"""

TESTING_ONLY = True

from pathlib import Path
import string
import unidecode
import csv

#
# CONFIGURATION
#

# Values within Path("...") can be changed to an absolute or a relative file location
# e.g.  Path("rawdata.csv"); Path("C:/data/rawdata.csv"); Path("~/downloads/data.csv")
INPUT_FILENAME = "./source_names.csv"
OUTPUT_FILENAME = "./clean_names.csv"
NICKNAME_FILENAME = "./nickname_mapping.csv"

if TESTING_ONLY:
    INPUT_FILENAME = "C:/Users/matvan/AppData/Local/Temp/9/__test_extract2.csv"
    OUTPUT_FILENAME = "C:/Users/matvan/AppData/Local/Temp/9/__test_cleaned2.csv"

# We agreed on the empty string as a suitable missing/null value
MISSING_VALUE = ""

# These are required; other fields in INPUT_FILENAME will be ignored.
INPUT_FIELDS = ["name_first_middle", "name_last", "mob", "yob"]

# This is the list and order of the output fields.
# The output field names are intentionally different from input field names.
OUTPUT_FIELDS = [
    "given",
    "family",
    "month",
    "year",
    "complete",
    "given_first_word",  # 1a. this trio breaks first/middle after the first word
    "given_middle_initial",  # 1b.
    "given_all_but_first",  # 1c.
    "given_nickname",
    "given_all_but_final",  # 2a. this trio breaks first/middle before the final word
    "given_final_initial",  # 2b.
    "given_final_word",  # 2c.
]


def main():

    nicknames = load_nicknames(NICKNAME_FILENAME)

    input_table = load_input(INPUT_FILENAME)

    print("{} rows to process.".format(len(input_table)))

    output_table = [process_row(i, row, nicknames) for i, row in enumerate(input_table)]

    write_output(output_table, OUTPUT_FILENAME)
    print("Written to {}.".format(OUTPUT_FILENAME))


def load_nicknames(lookup_filename):
    lookup_path = Path(lookup_filename).resolve(strict=True)
    print("Creating nickname lookup from {}.".format(lookup_path))
    with lookup_path.open(encoding="utf-8-sig") as infile:
        reader = csv.DictReader(infile)
        # If there is an excessively large quantity of records (multimillions)
        # then we may want instead stream via generators to a tempfile.
        return {
            initial_name_clean(row["raw_name"]): initial_name_clean(row["name_group"])
            for row in reader
            if row["raw_name"] == initial_name_clean(row["raw_name"])
        }


def load_input(input_filename):
    input_path = Path(input_filename).resolve(strict=True)
    print("Reading source names from {}.".format(input_path))
    with input_path.open(encoding="utf-8-sig") as infile:
        reader = csv.DictReader(infile)
        # If there is an excessively large quantity of records (multimillions)
        # then we may want instead stream via generators to a tempfile.
        all_input = [row for row in reader]
    for field in INPUT_FIELDS:
        assert (
            field in all_input[0]
        ), f"Required field {field} does not appear to be in the headers."
    return all_input


def process_row(i, row, nicknames):
    if (i + 1) % 10000 == 0:
        print("Processing row {}...".format(i + 1))

    # Create the building blocks for the output: normalized given, family, month, year.
    normalized_row = normalize(row)

    # Use the normalized fields to form first word, final word, initials, etc.
    working_row = add_parsed_name_versions(normalized_row)

    # Create the nickname, either from the table or falling back to the plain name.
    very_first = working_row.get("given_first_word", "")
    working_row["given_nickname"] = nicknames.get(very_first, very_first)

    # Remove all spaces from all fields
    final_row = {}
    for key in working_row:
        final_row[key] = working_row[key].replace(" ", "")
    return final_row


def normalize(row):
    return {
        "given": initial_name_clean(row["name_first_middle"]),
        "family": initial_name_clean(row["name_last"]),
        "month": clean_integer(row["mob"], minimum=1, maximum=12),
        "year": clean_integer(row["yob"], minimum=1902, maximum=2010),
    }


def initial_name_clean(raw, remove_spaces=False):
    working = raw
    # Strip unicode down to ascii (e.g. Ë becomes E; ñ becomes n)
    working = unidecode.unidecode_expect_ascii(working)
    # Make all lowercase
    working = working.lower()
    # Remove absolutely everything except the lowercase letters and spaces
    acceptable = string.ascii_lowercase
    if not remove_spaces:
        acceptable = acceptable + " "
    return "".join(c for c in working if c in acceptable)


def clean_integer(raw_input, minimum, maximum):
    # For months, minimum = 1 and maximum = 12
    # For years, any UMETRICS date prior to 1902 is a null.
    # So we are using: 1902, 2010.
    # Strip out any leading zeros or nonsense
    try:
        numbered = int(raw_input)
    except (ValueError, TypeError):
        # Anything that cannot be converted to an integer returns null
        return MISSING_VALUE
    if numbered not in range(minimum, maximum + 1):
        # Anything outside the acceptable range returns null
        return MISSING_VALUE
    return str(numbered)


def add_parsed_name_versions(r):
    given = r["given"].split()

    try:
        r["given_first_word"] = given[0]
    except IndexError:
        # Indicates that given has no words; i.e., no given name at all.
        r["complete"] = r["family"]
        return r

    multiple_given = len(given) > 1
    # If there is only one word in the given name, these will all be blanks
    if multiple_given:
        r["given_final_word"] = given[-1]
        r["given_all_but_first"] = "".join(given[1:])
        r["given_all_but_final"] = "".join(given[:-1])

    # Initials for the 'middle given'
    if r.get("given_all_but_first"):
        r["given_middle_initial"] = r["given_all_but_first"][0]
    # and for the 'final middle'
    if r.get("given_final_word"):
        r["given_final_initial"] = r["given_final_word"][0]

    r["complete"] = "".join((r["given"], r["family"]))
    return r


def write_output(output_table, output_file):
    output_path = Path(output_file).resolve()
    # Create the directory for this file if it doesn't already exist.
    output_path.parent.mkdir(exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as outfile:
        writer = csv.DictWriter(
            outfile, restval=MISSING_VALUE, fieldnames=OUTPUT_FIELDS
        )
        writer.writeheader()
        for row in output_table:
            writer.writerow(row)


if __name__ == "__main__":
    main()
