from django.contrib import admin
from .models import Database, DatabaseColumn, DatabaseObject

class DatabaseAdmin(admin.ModelAdmin):
    list_display = ('name', 'language',)
    ordering = ["name"]

class DatabaseColAdmin(admin.ModelAdmin):
    list_display = ('database', 'name', 'code',)
    ordering = ["database", "name"]

admin.site.register(Database, DatabaseAdmin)
admin.site.register(DatabaseColumn, DatabaseColAdmin)
admin.site.register(DatabaseObject)
