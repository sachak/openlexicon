from .models import Database, DatabaseColumn, ColType, ColSize
from openlexicon.render_data import debug_log
import chardet
from io import StringIO
from pandas.api.types import is_string_dtype, is_float_dtype, is_numeric_dtype
import pandas as pd
import re

text_file_keys = {
    "nom": "name",
    "description": "info",
    "site web": "website",
    "langue": "language"
}

def save_many_relations(db_name, container, selected_items):
    selected = set(selected_items)
    db = getattr(container, db_name)
    saved = set(db.all())

    items_to_delete = saved.difference(selected)
    items_to_save = selected.difference(saved)

    # Deleting unselected items
    if len(items_to_delete) > 0:
        db.remove(*items_to_delete)

    db.add(*items_to_save)

    return items_to_delete

def get_database_info(text_file):
    lines = text_file.read().splitlines()
    database_info = {}
    col_info = {}
    getting_col_info = False
    for line in lines:
        line_split = line.decode("utf-8").split("\t")
        line_key = line_split[0].lower()
        if getting_col_info: # currently getting columns description
            col_info[line_key] = line_split[1].strip()
        elif line_key in ["tags", "champs oblig"]: # list fields
            database_info[line_key] = [x.lower().strip() for x in line_split[1].split(",")]
        elif line_key == "champs": # encountered champs. All lines after that should be columns description
            getting_col_info = True
        else: # name, description, website and language fields
            for key in text_file_keys.keys():
                if line_key.casefold() == key.casefold():
                    database_info[text_file_keys[key]] = line_split[1].strip()
                    break
    return database_info, col_info

def get_column_info(df, db, database_info, col_info, word_col_idx):
    mandatory_columns = database_info["champs oblig"]
    col_dict = {}
    for col_count, col in enumerate(df.columns):
        if col_count != word_col_idx:
            col_type = df[col].dtype
            col_filter = DatabaseColumn.objects.filter(database=db, code=col)
            if not col_filter.exists(): # Create column
                size = ColSize.MEDIUM
                if is_string_dtype(col_type):
                    type = ColType.TEXT
                elif is_float_dtype(col_type):
                    type = ColType.FLOAT
                elif is_numeric_dtype(col_type):
                    type = ColType.INT
                    size = ColSize.SMALL
                else:
                    raise Exception(f"No valid type for column {col}, type detected {col_type}")
                col_obj = DatabaseColumn.objects.create(
                    database=db,
                    code=col,
                    name=col,
                    type=type,
                    size=size,
                    mandatory=col.lower() in mandatory_columns,
                    description=None if col.lower() not in col_info else col_info[col.lower()]
                )
                col_dict[col] = col_obj
            else: # Get existing column
                col_dict[col] = col_filter[0]
    return col_dict

def remove_spaces(x):
    if isinstance(x, str):
        if re.match("^-?[\d ]{1,}(\.\d{1,})?$", x): # match float or int
            x = x.replace(" ", "")
            try: return int(x)
            except: return float(x)
    return x

def load_tsv_file(tsv_file):
    # check encoding and decode if needed
    rawdata = tsv_file.read()
    chardet_data = chardet.detect(rawdata)
    encoding = chardet_data["encoding"]
    enc_confidence = chardet_data["confidence"]
    default_encoding = "utf-8"

    if encoding != default_encoding:
        # TODO : return error
        if encoding is None:
            debug_log(f"Could not detect file {tsv_file.name} encoding -> skip", -1)
        elif enc_confidence < 0.7:
            debug_log(f"Chardet confidence {enc_confidence} for file {tsv_file.name} -> skip", -1)
        else:
            # go back to file first row to read again and decode
            tsv_file.seek(0)
            tsv_file = tsv_file.read().decode(encoding)
            df = pd.read_csv(StringIO(tsv_file), sep='\t', keep_default_na=False, na_values=[''])
    else:
        tsv_file.seek(0)
        df = pd.read_csv(tsv_file, sep="\t", keep_default_na=False, na_values=[''])
    # Remove spaces from cells with numbers only
    for col in list(df.columns):
        df[col] = df[col].apply(remove_spaces)
    return df

# Object with pattern column_list ["database__column1", "database__column2"] and pattern column_dict {"database": ["column1", "column2"]}
class DbColMap:
    def __init__(self, column_list):
        self.column_list = column_list
        self.set_column_dict()

    # From column_list with pattern ["database__column1", "database__column2"], create column_dict with pattern {DatabaseObject: ["column1", "column2"]}
    def set_column_dict(self):
        self.column_dict = {} # for datatable
        self.string_column_dict = {} # for template
        self.col_string = [] # for template (format will be 1__2,1__3, first number is db.id and second col.id)
        last_db_pk = None
        self.databases = []
        for col in self.column_list:
            db_pk, col_pk = DbColMap.get_db_col_from_string(col)
            # Avoid making multiple requests to get same database
            if db_pk != last_db_pk:
                try:database = Database.objects.get(id=db_pk)
                except:database = Database.objects.get(code=db_pk)
                last_db_pk = db_pk
            if database not in self.column_dict:
                self.databases.append(database)
                self.string_column_dict[database.id] = []
                self.column_dict[database] = [col_pk]
            else:
                self.column_dict[database].append(col_pk)
        # Get DatabaseColumn objects
        for db in self.databases:
            try:column_queryset = DatabaseColumn.objects.filter(database=db, id__in=self.column_dict[db]).select_related("database")
            except:column_queryset = DatabaseColumn.objects.filter(database=db, code__in=self.column_dict[db]).select_related("database")
            self.column_dict[db] = []
            for col in column_queryset:
                col_dict = {}
                for attr in ["id", "code", "size", "type", "description"]:
                    col_dict[attr] = getattr(col, attr)
                self.string_column_dict[db.id].append(col_dict)
                self.column_dict[db].append(col)
                self.col_string.append(f"{db.id}__{col.id}")
        self.col_string = ",".join(self.col_string)

    @staticmethod
    def get_db_col_from_string(string):
        # string has pattern database__column. Split and return the elements
        col_elts = string.split("__", 1)
        db_pk = col_elts[0]
        col_pk = col_elts[1]
        return db_pk, col_pk

    @staticmethod
    def listify_string(string):
        return string.split(export_sep)

export_sep = ","

default_DbColList = [f"Lexique4__{col_name}" for col_name in ['phon', 'lemme', 'cgram', 'freqlemfilms2', 'freqfilms2', 'nblettres', 'puorth', 'puphon', 'nbsyll', 'cgramortho']]

try: default_db = Database.objects.get(code="Lexique4")
except: default_db = Database.objects.none()
