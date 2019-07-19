# IRIS-NCSES Linkage Repository

This repository includes scripts and support files for 2019 IRIS-NCSES record linkage.

## Setup

```python -m pip install --user -r requirements.txt```

## Input File Cleaning

```python NCSES_clean_names.py```

### Overview

This code cleans and normalizes name fields, month, and year of birth. Key steps:

1. Create nickname lookup from nickname csv (`NICKNAME_FILENAME`)
2. Pull the source data input (`INPUT_FILENAME`)
3. Clean and normalize each field.
4. Apply nickname lookup function to assign a first name group from first given name.
5. Output to a ready-to-hash CSV (`OUTPUT_FILENAME`).

### Configuration

`INPUT_FILENAME` and `OUTPUT_FILENAME` should be customized as needed.

- They can be relative (`sourcenames.csv`, `./input/rawdata.csv`) or absolute (`C:/data/raw.csv`).
- Use forward slashes `/` in filenames, not backslash `\`. Windows natively handles either.

Other constants are fixed configurations that should not be changed independently.

### Input fields

The `INPUT_FIELDS` variable specifies the following fields that must be in the source name CSV:

- `name_first_middle`
   - concatenation of all given names: first(s) and/or middle(s)
- `name_last`
   - last name as provided by source
- `mob`
   - month of birth
- `yob`
   - year of birth

All other fields in the source CSV (e.g. IDs) will be passed directly to the cleaned CSV.

### Output fields

The script uses, the `OUTPUT_FIELDS` variable helps validate, these outgoing fields:

- cleaned versions of each input field, with new names for each field
    - `given`
    - `family`
    - `month`
    - `year`

- complete concatenated given + family
    - `complete`

- name group assigned from the first word of first name
    - `given_nickname`

- given name trio that breaks first/middle after the first word
    - `given_first_word`
    - `given_middle_initial`
    - `given_all_but_first`

- given name trio that breaks first/middle before the last word
    - `given_all_but_final`
    - `given_final_initial`
    - `given_final_word`
