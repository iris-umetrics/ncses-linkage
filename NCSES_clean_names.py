#!/usr/bin/env python
# coding: utf-8
"""
# Overview

This code to cleans and normalize person name data as well as month and year of birth.
It is designed to work with a source_names.csv file, which contains the following:
    1. first_name: Concatenation of all given names, i.e., first(s) and middle(s)
    2. last_name
    4. mob: month of birth
    5. yob: year of birth

Key steps of this program:
    1. Lookup nickname file
    1. Pull the source data input (INPUT_FILE)
    3. Clean and normalize each field.
    4. Apply the nickname lookup function to normalized first word of each first name.
    5. Output a production CSV (OUTPUT_FILE) ready to be hashed.

"""

from pathlib import Path
import string
import unidecode
import csv

# # Configuration

# Values within Path("...") can be changed to an absolute or a relative file location
# e.g.  Path("rawdata.csv"); Path("C:/data/rawdata.csv"); Path("~/downloads/data.csv")
INPUT_FILE = Path("./source_names.csv").resolve(strict=True)
NICKNAME_FILE = Path("./nickname_mapping.csv").resolve(strict=True)
OUTPUT_FILE = Path("./clean_names.csv").resolve()

# We agreed on the empty string as a suitable missing/null value
MISSING_VALUE = ""

# These are required; other fields in INPUT_FILE will be ignored.
INPUT_FIELDS = ["first_middle", "last_name", "mob", "yob"]

# This is the list and order of the output fields.
# The output field names are intentionally different from input field names.
OUTPUT_FIELDS = [
    "given",
    "family",
    "month",
    "year",
    "complete",
    "given_first_word",  # this trio breaks first/middle after the first word
    "given_middle_initial",  # .
    "given_all_but_first",  # .
    "given_nickname",
    "given_all_but_final",  # this trio breaks first/middle before the final word
    "given_final_initial",  # .
    "given_final_word",  # .
]


def main():

    print("Reading from {}.".format(INPUT_FILE))
    input_table = load_input(INPUT_FILE)
    print("{} rows to process.".format(len(input_table)))

    nicknames = load_nicknames(NICKNAME_FILE)

    output_table = [process_row(i, row, nicknames) for i, row in enumerate(input_table)]

    write_output(output_table, OUTPUT_FILE)
    print("Written to {}.".format(OUTPUT_FILE))


def load_input(input_file):
    with input_file.open(encoding="utf-8") as infile:
        reader = csv.DictReader(infile)
        # If there is an excessively large quantity of records (multimillions)
        # then we may want instead stream via generators to a tempfile.
        return [row for row in reader]


def load_nicknames(lookup_file):
    with Path(lookup_file).open(encoding="utf-8") as infile:
        reader = csv.DictReader(infile)
        # If there is an excessively large quantity of records (multimillions)
        # then we may want instead stream via generators to a tempfile.
        return {
            initial_name_clean(row["raw_name"]): initial_name_clean(row["name_group"])
            for row in reader
            if row["raw_name"] == initial_name_clean(row["raw_name"])
        }


def process_row(i, row, nicknames):
    if (i + 1) % 5 == 0:
        print("Processing row {}...".format(i + 1))

    # Create the building blocks for the output: normalized given, family, month, year.
    normalized_row = normalize(row)

    # Use the normalized fields to form first word, final word, initials, etc.
    working_row = add_parsed_name_versions(normalized_row)

    # Create the nickname, either from the table or falling back to the plain name.
    very_first = working_row["given_first_word"]
    working_row["given_nickname"] = nicknames.get(very_first, very_first)

    # Remove all spaces from all fields
    final_row = {}
    for key in working_row:
        final_row[key] = working_row[key].replace(" ", "")
    return final_row


def normalize(row):
    return {
        "given": initial_name_clean(row["first_name"]),
        "family": initial_name_clean(row["last_name"]),
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

    r["given_first_word"] = given[0]

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
    with output_file.open("w", encoding="utf-8") as outfile:
        writer = csv.DictWriter(
            outfile, restval=MISSING_VALUE, fieldnames=OUTPUT_FIELDS
        )
        writer.writeheader()
        for row in output_table:
            writer.writerow(row)


if __name__ == "__main__":
    main()
