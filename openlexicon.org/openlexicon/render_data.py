from django.conf import settings
from django.db import connection, reset_queries

def debug_log(msg, level=0):
    if level <= settings.LOG_LEVEL:
        print(msg)

def num_queries(reset=True):
    for q in connection.queries:
        debug_log(q, 1)
    debug_log(len(connection.queries), 1)
    if reset:
        reset_queries()
