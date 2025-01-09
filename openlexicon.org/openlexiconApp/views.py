from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Max, Min
from django.http import JsonResponse
from django.shortcuts import render
from .datatable import ServerSideDatatableView
from .models import DatabaseObject, Database, DatabaseColumn
from .utils import *
import json
import os

# https://datatables.net/examples/data_sources/server_side.html
def home(request):
    if request.method == "GET":
        # Get default database and columns for table header format
        columns = dict(DbColMap(default_DbColList).column_dict) # make a copy of default dict
        for key, value in columns.items():
            database_columns = list(DatabaseColumn.objects.filter(database=key))
            for i in range(len(value)):
                columns[key][i] = next(x for x in database_columns if x.code == value[i])
    return render(request, 'openlexiconServer.html', {'table_name': settings.SITE_NAME, 'columns': columns})

@login_required
def import_data(request):
    # TODO : Do some filters on files uploaded (json only, injection, etc.)
    if request.method == 'POST' and request.FILES['json_file']:
        json_file = request.FILES['json_file']
        try:
            col_file = request.FILES['col_file']
            col_data = json.load(col_file)
        except:
            col_data = {}

        word_col = request.POST.get("word_col")
        db_name = os.path.splitext(json_file.name)[0]
        db_filter = Database.objects.filter(name=db_name)
        data = json.load(json_file)
        if not db_filter.exists():
            db = Database.objects.create(name=db_name)
        else:
            db = db_filter[0]
        # Create database columns if they do not exist
        if len(data["data"]) > 0:
            model = data["data"][0]
            for key in model.keys():
                if key != word_col:
                    col_filter = DatabaseColumn.objects.filter(database=db, code=key)
                    if not col_filter.exists():
                        col = DatabaseColumn.objects.create(database=db, code=key)
                        # if we have info on column provided by col_file.json, we replace default values with the ones provided
                        if key in col_data:
                            for attr in ["name", "size", "type"]:
                                setattr(col, attr, col_data[key][attr])
                            col.save()
        objs = []
        for item in data["data"]:
            jsonDict = {}
            dbObj = DatabaseObject()
            for attr in item.keys():
                dbattr = attr
                if attr == word_col:
                    dbattr = "ortho"
                try:
                    setattr(dbObj, dbattr, item[attr])
                    if attr != word_col:
                        jsonDict[dbattr] = item[attr]
                except:
                    continue
            objs.append(dbObj)
            dbObj.jsonData = jsonDict
            dbObj.database = db
        DatabaseObject.objects.bulk_create(objs) # bulk to avoid multiple save requests
        messages.success(request, ("Fichier importé !"))
    return render(request, 'importForm.html')

# https://github.com/umesh-krishna/django_serverside_datatable/tree/master
class ItemListView(ServerSideDatatableView):
    def get(self, request, *args, **kwargs):
        column_list = kwargs.get('column_list', [])
        # Populate column_list with default if no column_list provided
        if column_list == []:
            column_list = default_DbColList
        self.dbColMap = DbColMap(column_list)
        self.queryset = DatabaseObject.objects.filter(database__in=self.dbColMap.databases)
        return super(ItemListView, self).get(request, *args, **kwargs)

# NOTE : to return min/max for slider creation
def filter_data(request):
    if request.method == 'POST':
        database, colName = DbColMap.get_db_col_from_string(request.POST.get('colName'))
        col_data = DatabaseObject.objects.filter(database=Database.objects.get(name=database)).select_related("database").values_list(f"jsonData__{colName}", flat=True).distinct()
        return JsonResponse({"min": min(col_data), "max": max(col_data)})
