from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render
from .datatable import ServerSideDatatableView
from .models import DatabaseObject, Database, DatabaseColumn, ColType, Tag
from .utils import *
import json
import os
import pandas as pd

# https://datatables.net/examples/data_sources/server_side.html
def home(request, column_list=[]):
    # Get default database and columns for table header format
    if column_list == []:
        column_list = default_DbColList
    else:
        column_list = DbColMap.listify_string(column_list)
    dbColMap = DbColMap(column_list)
    all_columns = DatabaseColumn.objects.all().select_related("database").order_by("database__name", "id")
    all_columns_dict = {}
    for col in all_columns:
        if col.database not in all_columns_dict:
            all_columns_dict[col.database] = [col]
        else:
            all_columns_dict[col.database].append(col)
    return render(request, 'openlexiconServer.html', {'table_name': settings.SITE_NAME, 'columns': json.dumps(dbColMap.string_column_dict), 'col_string': dbColMap.col_string, 'all_columns': all_columns_dict, "database_order": list(dbColMap.string_column_dict.keys())})

@login_required
def import_data(request):
    # TODO : Do some filters on files uploaded (json only, injection, etc.)
    if request.method == 'POST':
        tsv_file = request.FILES['tsv_file']

        #######################
        #### Database info ####
        #######################

        if 'text_file' in request.FILES:
            database_info, col_info = get_database_info(request.FILES['text_file'])
            db_name = database_info["name"]
        else:
            database_info, col_info = {}, {}
            db_name = os.path.splitext(tsv_file.name)[0]
        db_code = db_name.replace(" ", "")

        # Check if database exists, else create it
        db_filter = Database.objects.filter(code=db_code)
        if not db_filter.exists():
            db = Database.objects.create(code=db_code, name=db_name)
        else:
            db = db_filter[0]

        # Set database info from text file
        for key in database_info:
            if key == "tags":
                tags = []
                for tag in database_info["tags"]:
                    tag_filter = Tag.objects.filter(name=tag.capitalize())
                    if not tag_filter.exists(): # Create tag
                        tag = Tag.objects.create(name=tag.capitalize())
                        tags.append(tag)
                    else:
                        tags.append(tag_filter[0])
                # Delete old many to many tags and save new ones
                # TODO : delete tags with no relation to database left
                save_many_relations("tags", db, tags)
            elif key != "champs oblig":
                setattr(db, key, database_info[key])
        db.save()

        # Load TSV file
        data_df = load_tsv_file(tsv_file)
        word_col_idx = int(request.POST.get("word_col"))

        # Database columns
        if len(data_df) > 0:
            col_dict = get_column_info(data_df, db, database_info, col_info, word_col_idx)
        objs = []

        ################################
        #### Create DatabaseObjects ####
        ################################

        for index, row in data_df.iterrows():
            jsonDict = {}
            dbObj = DatabaseObject()
            for col_count, col_name in enumerate(data_df.columns.values):
                dbattr = col_name
                itemAttr = row[col_name]
                if pd.isnull(itemAttr):
                    itemAttr = None
                if col_count == word_col_idx:
                    dbattr = "ortho"
                else:
                    col = col_dict[col_name]
                    if itemAttr is not None and col.type in [ColType.INT, ColType.FLOAT]:
                        if col.min == None or itemAttr < col.min:
                            col.min = itemAttr
                        if col.max == None or itemAttr > col.max:
                            col.max = itemAttr
                if col_count != word_col_idx:
                    jsonDict[dbattr] = itemAttr
                else:
                    setattr(dbObj, dbattr, itemAttr)
            objs.append(dbObj)
            dbObj.jsonData = jsonDict
            dbObj.database = db
        DatabaseObject.objects.bulk_create(objs) # bulk to avoid multiple save requests
        DatabaseColumn.objects.bulk_update(col_dict.values(), fields=["min", "max"])
        # Update database number of rows
        db.nbRows = DatabaseObject.objects.filter(database=db).count()
        db.save()
        messages.success(request, ("Fichier importé !"))
    return render(request, 'importForm.html')

# https://github.com/umesh-krishna/django_serverside_datatable/tree/master
class ItemListView(ServerSideDatatableView):
    def get(self, request, *args, **kwargs):
        column_list = kwargs.get('column_list') # column_list is provided by home view, we always have a column_list in ItemListView
        column_list = column_list.split(",")
        self.dbColMap = DbColMap(column_list)
        return super(ItemListView, self).get(request, *args, **kwargs)
