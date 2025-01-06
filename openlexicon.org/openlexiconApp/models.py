from django.db import models
from django_ckeditor_5.fields import CKEditor5Field

class ExportMode(models.TextChoices):
    CSV = "CSV"
    EXCEL = "EXCEL"

class Lang(models.TextChoices):
    FR = "French"
    EN = "English"
    DE = "Dutch"
    MULT = "Multiple languages"

class Database(models.Model):
    name = models.CharField(max_length=50, unique=True)
    info = CKEditor5Field(blank=True, null=True) # for tooltip
    language = models.CharField(max_length=20, choices=Lang.choices, default=Lang.FR)

class DatabaseObject(models.Model):
    database = models.ForeignKey(Database, on_delete=models.CASCADE)
    ortho = models.CharField(max_length=50, verbose_name="Word")
    jsonData = models.JSONField(null=True)
