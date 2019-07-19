#!/usr/bin/env python
# coding: utf-8
"""
IRIS-NCSES Name Cleaning

See README.md for details.
"""

#
# IMPORTS
#

import csv
import string
import time
from pathlib import Path

import unidecode

#
# CONFIGURATION
#

# Change values of these as needed.
INPUT_FILENAME = r"./source_names.csv"
OUTPUT_FILENAME = r"./clean_names.csv"

#
# FIXED CONSTANTS
#

# This nickname file is being distributed along with the scripts.
NICKNAME_FILENAME = r"./nickname_mapping.csv"

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
    "given_nickname",
    "given_first_word",
    "given_middle_initial",
    "given_all_but_first",
    "given_all_but_final",
    "given_final_initial",
    "given_final_word",
]

#
# MAIN
#


def main():
    """Primary execution to run when this file is directly executed"""

    nicknames = load_nicknames(NICKNAME_FILENAME)
    input_table = load_input(INPUT_FILENAME)

    # Raise an exception unless input field is present in the input table.
    assert set(INPUT_FIELDS) <= set(input_table[0]), "Not all input fields were found."

    output_table = process_all_rows(input_table, nicknames)

    write_output(output_table, OUTPUT_FILENAME, OUTPUT_FIELDS)


def load_nicknames(filename):
    """Create a raw_name -> name_group dict from two-field nickname lookup in filename"""
    lookup_path = Path(filename).resolve(strict=True)
    print("Creating nickname lookup from {}.".format(lookup_path))
    with lookup_path.open(encoding="utf-8-sig") as infile:
        reader = csv.DictReader(infile)
        return {row["raw_name"]: row["name_group"] for row in reader}


def load_input(filename):
    """Create and validate the fields found in a source file"""
    input_path = Path(filename).resolve(strict=True)
    print("Reading source names from {}.".format(input_path))
    # utf-8-sig should provide a little more flexibility, e.g., SSMS outputs a BOM
    with input_path.open(encoding="utf-8-sig") as infile:
        reader = csv.DictReader(infile)
        # If there is an excessively large quantity of records (multimillions)
        # then we may want instead stream via generators to a tempfile.
        return [row for row in reader]


def process_all_rows(input_table, nicknames):
    print("{:,} rows to process.".format(len(input_table)))
    result = [process_row(i, row, nicknames) for i, row in enumerate(input_table)]
    print("{:,} rows complete.".format(len(result)))
    return result


def process_row(i, row, nicknames):
    if (i + 1) % 100000 == 0:
        print("    ...processing row {:,}...".format(i + 1))

    # Create the building blocks for the output: normalized given, family, month, year.
    normalized_row = normalize(row)

    # Use the normalized fields to form first word, final word, initials, etc.
    working_row = add_parsed_name_versions(normalized_row)

    # Create the nickname, either from the table or falling back to the plain name.
    very_first = working_row.get("given_first_word", MISSING_VALUE)
    working_row["given_nickname"] = nicknames.get(very_first, very_first)

    # Remove all spaces from all output fields (NOT from external IDs, etc.)
    final_row = {}
    for key, value in working_row.items():
        if key in OUTPUT_FIELDS:
            value = value.replace(" ", "")
        final_row[key] = value
    return final_row


def normalize(row):
    """Validate and clean each raw row into a new row."""
    # Move as-is anything that is not one of the required INPUT_FIELDS
    new_row = {k: v for k, v in row.items() if k not in INPUT_FIELDS}
    # Create a cleaned version of each of the INPUT_FIELDS
    new_row["given"] = clean_name(row["name_first_middle"])
    new_row["family"] = clean_name(row["name_last"])
    # For months, minimum = 1 and maximum = 12
    new_row["month"] = clean_integer(row["mob"], minimum=1, maximum=12)
    # In the data we're matching, birth years prior to 1902 all appear to be null
    new_row["year"] = clean_integer(row["yob"], minimum=1902, maximum=2010)
    return new_row


def clean_name(raw, remove_spaces=False):
    """Clean each input name down to lowercase ascii letters and spaces"""
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
    """Filter (stringed) integer field to allow only the specified range"""
    try:
        # Strip out any leading zeros or nonsense
        numbered = int(raw_input)
    except (ValueError, TypeError):
        # Anything that cannot be converted to an integer returns null
        return MISSING_VALUE
    if numbered not in range(minimum, maximum + 1):
        # Anything outside the acceptable range returns null
        return MISSING_VALUE
    return str(numbered)


def add_parsed_name_versions(r):
    """Create the new parsed versions of the input fields"""
    given = r["given"].split()

    try:
        r["given_first_word"] = given[0]
    except IndexError:
        # Indicates that given has no words; i.e., no given name at all.
        r["complete"] = r["family"]
        # With no given name, the function's job here is done.
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


def write_output(output_table, output_file, output_fields):
    """Write out the CSV"""
    # Create the directory for this file if it doesn't already exist.
    output_path = Path(output_file).resolve()
    output_path.parent.mkdir(exist_ok=True)

    # Derive the fieldnames from the first row.
    fields = sorted(set(field for row in output_table for field in row))
    assert set(output_fields) <= set(fields), "Not all output fields were created."

    with output_path.open("w", newline="", encoding="utf-8") as outfile:
        writer = csv.DictWriter(outfile, restval=MISSING_VALUE, fieldnames=fields)
        writer.writeheader()
        for row in output_table:
            writer.writerow(row)
    print("Cleaned output written to {}.".format(output_path))


if __name__ == "__main__":
    scriptfile = Path(__file__).resolve()
    starttime = time.time()
    print("\n{} launched.".format(scriptfile))
    main()
    elapsed = int(time.time() - starttime)
    print("{} complete in {} seconds.\n".format(scriptfile, elapsed))
