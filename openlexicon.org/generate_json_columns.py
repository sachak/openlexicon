import json
import easygui
import os
import re

def isfloat_regex(string):
    # We have defined a pattern for float value
    pattern = r'^[-+]?[0-9]*\.[0-9]+([eE][-+]?[0-9]+)?$'
    # Find the match and convert to boolean
    return bool(re.match(pattern, string))

def generate_col_json(json_file_path):
    # Load database json and get first entry, which we will use to try to guess dataType (int, float, text)
    data = json.load(open(json_file_path))
    model = data["data"][0]
    col_info = {}
    for key in model.keys():
        new_col_info = {"name": key}
        size = "medium"
        val_type = "text"
        if isfloat_regex(model[key]):
            val_type = "float"
        elif model[key].isdigit():
            val_type = "int"
            size = "small"
        new_col_info["type"] = val_type
        new_col_info["size"] = size
        col_info[key] = new_col_info

    with open(os.path.splitext(json_file_path)[0] + "_col.json", "w") as outfile:
        json.dump(col_info, outfile, indent=2)

json_file_path = easygui.fileopenbox(msg="Choose a JSON file", filetypes=[["*.json", "JSON Files"]])

if json_file_path is not None:
    generate_col_json(json_file_path)
else:
    print("Choose a JSON file to proceed")
