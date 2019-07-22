import csv

FILENAME = "test/clean_names.csv"
with open(FILENAME, encoding="utf-8") as infile:
    reader = csv.DictReader(infile)
    for i, field in enumerate(reader.fieldnames):
        print(i, field)
