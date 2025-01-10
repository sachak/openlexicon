from .models import Database, DatabaseColumn

# Object with pattern column_list ["database__column1", "database__column2"] and pattern column_dict {"database": ["column1", "column2"]}
class DbColMap:
    def __init__(self, column_list):
        self.column_list = column_list
        self.set_column_dict()

    # From column_list with pattern ["database__column1", "database__column2"], create column_dict with pattern {DatabaseObject: ["column1", "column2"]}
    def set_column_dict(self):
        self.column_dict = {}
        last_db_name = None
        for col in self.column_list:
            db_name, col_name = DbColMap.get_db_col_from_string(col)
            # Avoid making multiple requests to get same database
            if db_name != last_db_name:
                database = Database.objects.get(name=db_name)
                last_db_name = db_name
            if database not in self.column_dict:
                self.column_dict[database] = [col_name]
            else:
                self.column_dict[database].append(col_name)
        self.databases = list(self.column_dict.keys())
        # Get DatabaseColumn objects
        for db in self.databases:
            self.column_dict[db] = DatabaseColumn.objects.filter(database=db, code__in=self.column_dict[db]).select_related("database")

    @staticmethod
    def get_db_col_from_string(string):
        # string has pattern database__column. Split and return the elements
        col_elts = string.split("__", 1)
        db_name = col_elts[0]
        col_name = col_elts[1]
        return db_name, col_name

default_DbColList = [f"Lexique383__{col_name}" for col_name in ['phon', 'lemme', 'cgram', 'freqlemfilms2', 'freqfilms2', 'nblettres', 'puorth', 'puphon', 'nbsyll', 'cgramortho']] # + [f"Voisins__{col_name}" for col_name in ["NbVoisOrth", "VoisOrth"]] #+ [f"Manulex-Ortho__{col_name}" for col_name in ["SYNT", "CP_F", "CP_D", "CP_U", "CP_SFI", "CE1_F", "CE1_SFI", "CE2-CM2_D", "CP-CM2_F"]] + [f"Manulex-Lemmes__{col_name}" for col_name in ["SYNT", "CP_F", "CP_D", "CP_U", "CP_SFI", "CE1_F", "CE1_SFI", "CE2-CM2_D", "CP-CM2_F"]]

try: default_db = Database.objects.get(name="Lexique383")
except: default_db = Database.objects.none()
