from django.contrib import admin
from .models import Database, DatabaseColumn, DatabaseObject, Tag

class DatabaseAdmin(admin.ModelAdmin):
    list_display = ('name', 'language',)
    ordering = ["name"]
    actions=['force_delete_selected']

    def get_actions(self, request):
        actions = super(DatabaseAdmin, self).get_actions(request)
        del actions['delete_selected']
        return actions

    def force_delete_selected(self, request, queryset):
        for obj in queryset:
            obj.delete()

class DatabaseColAdmin(admin.ModelAdmin):
    list_display = ('database', 'name', 'type', 'min', 'max')
    ordering = ["database", "name"]

class DatabaseObjAdmin(admin.ModelAdmin):
    list_display = ('id', 'database', 'ortho', )
    ordering = ["ortho"]

admin.site.register(Database, DatabaseAdmin)
admin.site.register(DatabaseColumn, DatabaseColAdmin)
admin.site.register(DatabaseObject, DatabaseObjAdmin)
admin.site.register(Tag)
