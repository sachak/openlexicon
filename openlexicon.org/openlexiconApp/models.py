from django.db import models
from django_ckeditor_5.fields import CKEditor5Field

class ColSize(models.TextChoices):
    LARGE = "large"
    MEDIUM = "medium"
    SMALL = "small"

class ColType(models.TextChoices):
    TEXT = "text"
    FLOAT = "float"
    INT = "int"

    @staticmethod
    def get_field_class(type):
        if type == ColType.TEXT:
            return models.CharField()
        elif type == ColType.INT:
            return models.IntegerField()
        elif type == ColType.FLOAT:
            return models.FloatField()

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
    nbRows = models.IntegerField(null=True)

class DatabaseObject(models.Model):
    database = models.ForeignKey(Database, on_delete=models.CASCADE, db_index=True)
    ortho = models.CharField(max_length=50, verbose_name="Word")
    lemme = models.CharField(max_length=50, verbose_name="Lemme", null=True)
    cgram = models.CharField(max_length=20, verbose_name="Grammatical category", null=True)
    jsonData = models.JSONField(null=True)

    class Meta:
        unique_together = ('database', 'ortho', 'cgram', 'lemme',)

class DatabaseColumn(models.Model):
    database = models.ForeignKey(Database, on_delete=models.CASCADE, db_index=True)
    code = models.CharField(max_length=50, verbose_name="Code")
    name = models.CharField(max_length=50, verbose_name="Nom")
    size = models.CharField(max_length=10, verbose_name="Taille", default=ColSize.MEDIUM)
    type = models.CharField(max_length=10, verbose_name="Type de données", default=ColType.TEXT) # try to assume type if not given ?
    min = models.FloatField(null=True)
    max = models.FloatField(null=True)

    class Meta:
        unique_together = ('database', 'code',)
