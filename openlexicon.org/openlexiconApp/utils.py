from .models import Database

default_col_list = [f"Lexique383__{col_name}" for col_name in ['phon', 'lemme', 'cgram', 'freqlemfilms2', 'freqfilms2', 'nblettres', 'puorth', 'puphon', 'nbsyll', 'cgramortho']]

def getDbColFromString(string):
    # string has pattern database__column. Split and return the elements
    col_elts = string.split("__", 1)
    db_name = col_elts[0]
    col_name = col_elts[1]
    return db_name, col_name

# From col_list with pattern ["database__column1", "database__column2"], return col_dict with pattern {"database": ["column1", "column2"]}
def get_col_dict(col_list=[]):
    if col_list == []:
        col_list = default_col_list
    columns = {}
    last_db_name = None
    for col in col_list:
        db_name, col_name = getDbColFromString(col)
        # Avoid making multiple requests to get same database
        if db_name != last_db_name:
            database = Database.objects.get(name=db_name)
            last_db_name = db_name
        if database not in columns:
            columns[database] = [col_name]
        else:
            columns[database].append(col_name)
    return columns
