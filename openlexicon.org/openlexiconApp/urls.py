from django.urls import path, re_path
from .views import *

app_name = 'openlexiconApp'
urlpatterns = [
    path('serverTest', home, name="homeServer"),
    path('serverTest/<str:column_list>', home, name="homeServer"),
    path('import_data', import_data, name="import_data"),
    path('data/<str:column_list>', ItemListView.as_view(), name="data")
]
