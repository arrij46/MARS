# Extract specific Label Requirememnts from JSON Files, this code is for duplicates.

import json

# Input and output file names
input_file = "output.json"
output_file = "Duplicate.json"

# Read the input JSON file
with open(input_file, "r", encoding="utf-8") as f:
    data = json.load(f)

# Filter entries where Label == "Duplicate"
duplicates = [entry for entry in data if entry.get("Label") == "Duplicate"]

# Write filtered entries to a new JSON file
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(duplicates, f, indent=4, ensure_ascii=False)

print(f"✅ Extracted {len(duplicates)} Duplicate entries into '{output_file}'.")

