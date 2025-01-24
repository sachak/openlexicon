call "venv\Scripts\activate"
mkdir temp
move "openlexiconApp\migrations\__init__.py" temp
cd "openlexiconApp\migrations"
RD /S /Q "__pycache__"
del *.* /Q
cd ../..
move "temp\__init__.py" "openlexiconApp\migrations"
rmdir temp
:: del db.sqlite3
:: Need to go to pgAdmin4, delete and recreate database django_openlexicon
python3 manage.py makemigrations
python3 manage.py migrate
python3 manage.py shell < initialize_su.py
call "deactivate"
