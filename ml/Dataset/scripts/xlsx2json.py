# This script reads data from an Excel file and converts it into a JSON format.
# No header rows in xlsx file.
# Change the index number as needed.


import openpyxl
import json

def xlsx_to_json(xlsx_file, json_file):
    # Load the Excel workbook
    workbook = openpyxl.load_workbook(xlsx_file)
    sheet = workbook.active

    data = []
    index = 1  # Initialize index

    # Loop min_row is starting row!
    for row in sheet.iter_rows(min_row=1, values_only=True):
        entry = {
            "Number": str(index),
            "Requirement1": row[1],  
            "Requirement2": row[2], 
            "Label": row[3]  
        }
        data.append(entry)
        
        index += 1

    # Write to a JSON file
    with open(json_file, 'a') as jsonfile:
        json.dump(data, jsonfile, indent=4)

# Example usage:
xlsx_to_json('Dataset.xlsx', 'Dataset.json')
