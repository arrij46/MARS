import json
from openpyxl import Workbook

# Input and output file names
input_file = "neutrals.json"
output_file = "neutrals.xlsx"

# Read data from JSON file
with open(input_file, "r", encoding="utf-8") as f:
    data = json.load(f)

# Create a new Excel workbook and sheet
wb = Workbook()
ws = wb.active
ws.title = "Neutrals"

# Write header row (keys of the first JSON object)
if data:
    headers = list(data[0].keys())
    ws.append(headers)

    # Write data rows
    for entry in data:
        ws.append([entry.get(h, "") for h in headers])

# Save the Excel file
wb.save(output_file)

print(f"✅ JSON data successfully written to '{output_file}'")
