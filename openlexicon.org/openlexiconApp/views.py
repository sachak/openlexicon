from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render
from .datatable import ServerSideDatatableView
from .models import DatabaseObject, Database, DatabaseColumn, ColType
from .utils import *
import json
import os

# https://datatables.net/examples/data_sources/server_side.html
def home(request):
    if request.method == "GET":
        # Get default database and columns for table header format
        columns = dict(DbColMap(default_DbColList).column_dict) # make a copy of default dict
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
            col_types = {}
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
                            col_types[col.code] = col.type
                    else:
                        col_types[col_filter[0].code] = col_filter[0].type
        objs = []
        for item in data["data"]:
            jsonDict = {}
            dbObj = DatabaseObject()
            for attr in item.keys():
                dbattr = attr
                itemAttr = item[attr]
                if attr == word_col:
                    dbattr = "ortho"
                elif col_types[attr] in [ColType.INT, ColType.FLOAT]: # remove all spaces from columns declared as int/float
                    itemAttr = itemAttr.replace(" ", "")
                try:
                    setattr(dbObj, dbattr, itemAttr)
                    if attr != word_col:
                        jsonDict[dbattr] = itemAttr
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
