import zipfile
import json
import os
from typing import List, Dict, Any
import tqdm

JAR_FILES_TO_PROCESS: List[str] = [
    "K:\Repo\Python\contentcreatie\content\wit\Content_wit.jar",
    "K:\Repo\Python\contentcreatie\content\geel\Translate_nl-NL_to_nl_2025_08_24_14_45_17_259.jar",
    "K:\Repo\Python\contentcreatie\content\geel\Translate_nl-NL_to_nl_2025_08_24_15_00_30_980.jar"
]


class JarScrubber:
    """
    A class to handle the scrubbing of sensitive data from JSON files within a JAR archive.
    """
    def __init__(self, keys_to_remove: List[str], values_to_scrub: Dict[str, List[str]]):
        """
        Initializes the JarScrubber with scrubbing rules.

        :param keys_to_remove: list, A list of dictionary keys to remove entirely.
        :param values_to_scrub: dict, A dictionary where keys are dictionary keys to inspect
                                (e.g., 'references'), and values are a list of string values
                                that should cause the parent key-value pair to be removed.
        """
        self.keys_to_remove = keys_to_remove
        self.values_to_scrub = values_to_scrub

    def _scrub_recursive(self, data: Any) -> Any:
        """
        Recursively scrubs specified keys and values from a JSON-like object.

        :param data: Any, The object (dict, list, or primitive) to be scrubbed.
        :return: Any, The scrubbed object.
        """
        if isinstance(data, dict):
            # Remove specified keys
            for key in self.keys_to_remove:
                if key in data:
                    del data[key]

            # Scrub entries based on value for specified parent keys
            for parent_key, bad_values in self.values_to_scrub.items():
                if parent_key in data and isinstance(data[parent_key], dict):
                    target_dict = data[parent_key]
                    keys_to_delete = [
                        key for key, value in target_dict.items() if value in bad_values
                    ]
                    for key in keys_to_delete:
                        del target_dict[key]

            # Recurse into the dictionary's values
            return {key: self._scrub_recursive(value) for key, value in data.items()}

        if isinstance(data, list):
            # Recurse into the list's items
            return [self._scrub_recursive(item) for item in data]

        # Return primitives and other types as is
        return data

    def process_jar(self, input_path: str) -> None:
        """
        Reads a JAR file, scrubs its JSON contents, and saves it as a new JAR file.

        :param input_path: str, The file path of the source JAR file.
        :return: None, This function writes a file and prints to the console.
        """
        if not os.path.isfile(input_path):
            print(f"\nError: Input file not found at '{input_path}'. Skipping.")
            return

        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_scrubbed{ext}"

        print(f"\nProcessing '{os.path.basename(input_path)}'...")

        try:
            with zipfile.ZipFile(input_path, 'r') as source_zip:
                with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as dest_zip:
                    for item in tqdm.tqdm(source_zip.infolist()):
                        file_content = source_zip.read(item.filename)

                        if item.filename.endswith('.json'):
                            try:
                                json_string = file_content.decode('utf-8')
                                data = json.loads(json_string)
                                scrubbed_data = self._scrub_recursive(data)
                                scrubbed_json_string = json.dumps(scrubbed_data, indent=2)
                                file_content = scrubbed_json_string.encode('utf-8')
                                print(f"  - Scrubbed: {item.filename}")
                            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                                print(f"  - Warning: Could not process JSON file '{item.filename}'. Copying as-is. Error: {e}")

                        dest_zip.writestr(item, file_content)

            print(f"Successfully created scrubbed JAR: '{output_path}'")

        except zipfile.BadZipFile:
            print(f"Error: The file '{input_path}' is not a valid JAR/ZIP file.")
            if os.path.exists(output_path):
                os.remove(output_path)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            if os.path.exists(output_path):
                os.remove(output_path)


def main() -> None:
    """
    Initiates the JAR scrubbing process for all files listed in JAR_FILES_TO_PROCESS.
    """
    if not JAR_FILES_TO_PROCESS:
        print("The 'JAR_FILES_TO_PROCESS' list is empty. Please edit the script to add file paths.")
        return

    scrub_config = {
        "keys_to_remove": ["commentList", "publishedBy", "lastModifiedBy","createdBy"],
        "values_to_scrub": {"references": ["OwnerED", "PublishedBy"]}
    }
    
    scrubber = JarScrubber(
        keys_to_remove=scrub_config["keys_to_remove"],
        values_to_scrub=scrub_config["values_to_scrub"]
    )
    
    print(f"Found {len(JAR_FILES_TO_PROCESS)} file(s) to process.")
    for jar_path in JAR_FILES_TO_PROCESS:
        scrubber.process_jar(jar_path)

    print("\nAll tasks complete.")


if __name__ == "__main__":
    main()