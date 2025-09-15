import json
import argparse
import jsonschema
import os

def validate_json(json_file, schema_file):
    """
    Validates a JSON file against a JSON schema.

    Args:
        json_file (str): The path to the JSON file to validate.
        schema_file (str): The path to the JSON schema file.
    """
    # Check if the provided file paths exist
    if not os.path.exists(schema_file):
        print(f"Error: Schema file not found at '{schema_file}'")
        return

    if not os.path.exists(json_file):
        print(f"Error: JSON data file not found at '{json_file}'")
        return

    # Load the schema file
    try:
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format in schema file '{schema_file}': {e}")
        return
    except Exception as e:
        print(f"An error occurred while reading the schema file: {e}")
        return

    # Load the JSON data file
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format in data file '{json_file}': {e}")
        return
    except Exception as e:
        print(f"An error occurred while reading the data file: {e}")
        return

    # Perform validation
    try:
        jsonschema.validate(instance=data, schema=schema)
        print(f"✅ Validation successful: '{json_file}' conforms to the schema in '{schema_file}'")
    except jsonschema.exceptions.ValidationError as err:
        print(f"❌ Validation FAILED: '{json_file}' does not conform to the schema.")
        print(f"Error: {err.message}")
        # Provide more context for the error
        if err.instance:
            print(f"On instance: {err.instance}")
        if err.path:
            print(f"Path to error: {list(err.path)}")
    except jsonschema.exceptions.SchemaError as err:
        print(f"❌ Schema Error: The schema file '{schema_file}' is invalid.")
        print(f"Error details: {err.message}")


if __name__ == "__main__":
    # Set up command-line argument parser
    parser = argparse.ArgumentParser(
        description="Validate a JSON file against a JSON schema.",
        epilog="Example usage: python validate_moby_games.py seed-data/Samples/MobyGames-SNES-Truncated.json MobyGames.Schema.json"
    )
    parser.add_argument(
        "json_file",
        help="The path to the JSON data file to validate."
    )
    parser.add_argument(
        "schema_file",
        help="The path to the JSON schema file."
    )
    args = parser.parse_args()

    # Run the validation function
    validate_json(args.json_file, args.schema_file)