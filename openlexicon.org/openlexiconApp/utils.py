from .models import Database, DatabaseColumn

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
                except:database = Database.objects.get(name=db_pk)
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
                for attr in ["id", "code", "size", "type"]:
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

default_DbColList = [f"Lexique383__{col_name}" for col_name in ['phon', 'lemme', 'cgram', 'freqlemfilms2', 'freqfilms2', 'nblettres', 'puorth', 'puphon', 'nbsyll', 'cgramortho']]

try: default_db = Database.objects.get(name="Lexique383")
except: default_db = Database.objects.none()
