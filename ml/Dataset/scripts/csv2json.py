import csv
import json

def csv_to_json(csv_file, json_file):
    # Open the CSV file for reading
    with open(csv_file, mode='r') as csvfile:
        # Read the CSV file into a dictionary
        csv_reader = csv.DictReader(csvfile)
        
        # Convert the CSV to a list of dictionaries
        data = list(csv_reader)
    
    # Open the JSON file for writing
    with open(json_file, mode='w') as jsonfile:
        # Write the data to the JSON file
        json.dump(data, jsonfile, indent=4)

# Example usage:
csv_to_json('data.csv', 'output.json')
