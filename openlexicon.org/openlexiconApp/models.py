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
    lemme = models.CharField(max_length=50, verbose_name="Lemme")
    cgram = models.CharField(max_length=20, verbose_name="Grammatical category", null=True)
    jsonData = models.JSONField(null=True)

    class Meta:
        unique_together = ('database', 'ortho', 'cgram', 'lemme',)

class DatabaseColumn(models.Model):
    database = models.ForeignKey(Database, on_delete=models.CASCADE)
    code = models.CharField(max_length=50, verbose_name="Code")
    name = models.CharField(max_length=50, verbose_name="Nom")
    size = models.CharField(max_length=10, verbose_name="Taille", default=ColSize.MEDIUM)
    type = models.CharField(max_length=10, verbose_name="Type de données", default=ColType.TEXT) # try to assume type if not given ?

    class Meta:
        unique_together = ('database', 'code',)
