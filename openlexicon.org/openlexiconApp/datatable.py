# https://github.com/umesh-krishna/django_serverside_datatable
# https://pypi.org/project/django-serverside-datatable/2.1.0/#files
from django.views import View
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse
from django.core.exceptions import ImproperlyConfigured
from django.db.models import QuerySet, F, Q, Subquery, OuterRef, Max, Min
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast
from collections import namedtuple
import operator
from .models import ExportMode, ColType
from .utils import default_db
from functools import reduce
from pyexcelerate import Workbook
import csv
import os
import io
from openlexicon.render_data import num_queries

order_dict = {'asc': '', 'desc': '-'}

class Echo:
    def write(self, value):
        return value

class DataTablesServer(object):
    def __init__(self, request, dbColMap, qs):
        self.dbColMap = dbColMap
        self.column_list = ["ortho"] + [x.replace("__", "__jsonData__", 1) for x in self.dbColMap.column_list] # change pattern for column_name from database__col_name to database__jsonData__col_name
        # values specified by the datatable for filtering, sorting, paging
        self.request_values = request.GET
        # results from the db
        self.result_data = None
        # total in the table after filtering
        self.cardinality_filtered = 0
        # total in the table unfiltered
        self.cardinality = 0
        self.user = request.user
        self.qs = qs
        self.run_queries()

    def output_result(self):
        output = dict()
        # output['sEcho'] = str(int(self.request_values['sEcho']))
        output['iTotalRecords'] = str(self.data_count)
        output['iTotalDisplayRecords'] = str(self.cardinality_filtered)
        data_rows = []

        for row in self.result_data:
            data_row = []
            for i in range(len(self.column_list)):
                val = row[self.column_list[i]]
                data_row.append(val)
            data_rows.append(data_row)
        output['aaData'] = data_rows
        output["min_max_dict"] = self.min_max_dict
        return output

    def run_queries(self):
        # pages has 'start' and 'length' attributes
        pages = self.paging()
        # the term you entered into the datatable search
        _filter, op = self.filtering()
        # the document field you chose to sort
        sorting = self.sorting()
        # custom filter
        qs = self.qs

        # Get min/max
        cast_col_list = [column for column_list in self.dbColMap.column_dict.values() for column in column_list] # split to databasecolumn list
        qs = qs.annotate( # Cast to Float or IntegerField
            **{f"{col.database.name}__{col.code}__cast":Cast(KeyTextTransform(col.code, "jsonData"), ColType.get_field_class(col.type)) for col in cast_col_list}
        )
        # TODO : if too slow, try to convert JSONField to normal field and add index=True to speed up aggregate operation
        min_max_dict = qs.aggregate( # Aggregate to min and max
            **{f"{col.database.name}__{col.code}__min":Min(f"{col.database.name}__{col.code}__cast") for col in cast_col_list if col.type != ColType.TEXT},
            **{f"{col.database.name}__{col.code}__max":Max(f"{col.database.name}__{col.code}__cast") for col in cast_col_list if col.type != ColType.TEXT}
        )
        # Format from {"database__colName__min": 0, "database__colName__max": 0} to {"database__colName": {"min": 0, "max":0}}
        self.min_max_dict = {}
        for id, value in min_max_dict.items():
            colElts = id.rsplit("__", 1)
            colName = colElts[0]
            if colName not in self.min_max_dict:
                self.min_max_dict[colName] = {}
            self.min_max_dict[colName][colElts[1]] = value

        # Determine database of reference (ref_db) for count and column grouping.
        ref_db = self.dbColMap.databases[0]
        if len(self.dbColMap.databases) > 1:
            if default_db in self.dbColMap.databases:
                ref_db = default_db
            self.data_count = qs.filter(database=ref_db).count()
        else:
            self.data_count = qs.count()

        if _filter:
            if op == "or":
                qs = qs.filter(
                    reduce(operator.or_, _filter))
            else:
                qs = qs.filter(
                    reduce(operator.and_, [x for x in _filter])
                )
                # We handle separately nested lists : they are tuples for jsonData, used to check if key is null in jsonData, or if it contains the desired string or range
                for or_tuple in [x for x in _filter if isinstance(x, list)]:
                    qs = qs.filter(reduce(operator.or_, [Q(x) for x in or_tuple]))

        # self.full_data = qs.values_list(*self.attr_list) # TODO : for export
        # Rename attributes (jsonData__attr) to column_list pattern (database__jsonData__attr)
        attr_list = [x.replace(x.split("jsonData", 1)[0], "") for x in self.column_list]
        # TODO : check if same column_names in several databases can be an issue
        # Group if several databases
        if len(self.dbColMap.databases) > 1:
            # https://stackoverflow.com/questions/68797164/how-to-merge-two-different-querysets-with-one-common-field-in-to-one-in-django
            # https://blog.gitguardian.com/10-tips-to-optimize-postgresql-queries-in-your-django-project/
            # ref_db is the only one for which rows will not change. If we have more than one database, we annotate the queryset of ref_db to add columns from other databases.
            data = qs.filter(database=ref_db).values("ortho", **{self.column_list[i]:F(attr_list[i]) for i in range(1, len(self.column_list)) if ref_db.name in self.column_list[i]})

            for db in [db for db in self.dbColMap.databases if db != ref_db]:
                db_qs = qs.filter(database=db, ortho=OuterRef('ortho'))
                data = data.annotate(**{self.column_list[i]:Subquery(db_qs.values(attr_list[i])[:1]) for i in range(1, len(self.column_list)) if db.name in self.column_list[i]})
        else:
            data = qs.values("ortho", **{self.column_list[i]:F(attr_list[i]) for i in range(1, len(self.column_list))})
        if sorting == "":
            sorting = "ortho"
        data = data.order_by('%s' % sorting)
        len_data = data.count()

        # Pagination
        # If index is in 20000 last ones, reverse queryset to get faster indexing. Inspired by : https://www.reddit.com/r/django/comments/4dn0mo/how_to_optimize_pagination_for_large_queryset/
        _index = int(pages.start)
        _nb_pages = int(pages.length - pages.start)
        _end_index = min(_index + _nb_pages, len_data)
        PAGE_THRESHOLD = 20000
        if len_data > PAGE_THRESHOLD * 2 and len_data - _index < PAGE_THRESHOLD:
            reversed_data = data.order_by(f"-{sorting}")
            _old_index = _index
            _index = len_data - _end_index
            _end_index = len_data - _old_index
            reversed_data = reversed_data[_index:_end_index]
            data = reversed(reversed_data)
        else:
            data = data[_index:_end_index]

        self.result_data = data

        # length of filtered set
        if _filter:
            self.cardinality_filtered = len_data
        else:
            self.cardinality_filtered = len_data
        self.cardinality = pages.length - pages.start

    def filtering(self):
        # build your filter spec
        filter = []
        # search for single value (table search field)
        if (self.request_values.get('search[value]')) and (self.request_values['search[value]'] != ""):
            op = "or"
            for i in range(len(self.column_list)):
                if self.request_values['columns[%d][searchable]' % i] == 'true':
                    filter.append(
                        Q(**{'%s__icontains' % self.column_list[i]: self.request_values['search[value]']}))
        # search for each column (column search field)
        else:
            op = "and"
            for i in range(len(self.column_list)):
                column_list = self.request_values.getlist(f'columns[{i}][search][value][]')
                col_elt = self.request_values.get(f'columns[{i}][search][value]')
                if (col_elt and col_elt != ""): # characters
                    filter.append((f"{self.column_list[i].replace('__jsonData', '')}__cast__icontains", col_elt))
                elif (column_list and len(column_list) == 2) : # numbers. WARNING : range does not work with JSONField on SQLite. It works with Postgresql. We need to use cast for numbers to be considered as such and not as text.
                    filter.append((f"{self.column_list[i].replace('__jsonData', '')}__cast__range", column_list))
        q_list = []
        for query in filter:
            if "__cast__" in query[0]: # if jsonData, use original query filter only if DatabaseObject has relevant database (has other database OR apply original query filter)
                col_elts = query[0].split("__", 1)
                database_name = col_elts[0]
                col_name = col_elts[1]
                q_list.append((~Q((f'database__name', database_name)) | Q((query[0], query[1]))))
            else:
                q_list.append(Q(query))
        return q_list, op

    def sorting(self):
        order = ''
        if ("order[0][column]" in self.request_values.keys()):
            # column number
            column_number = int(self.request_values["order[0][column]"])
            # sort direction
            sort_direction = self.request_values['order[0][dir]']

            order = ('' if order == '' else ',') +order_dict[sort_direction]+self.column_list[column_number]

        return order

    def paging(self):
        pages = namedtuple('pages', ['start', 'length'])
        if (self.request_values['start'] != "") and (self.request_values['length'] != -1):
            pages.start = int(self.request_values['start'])
            pages.length = pages.start + int(self.request_values['length'])

        return pages


class ServerSideDatatableView(View):
    queryset = None
    dbColMap = None
    model = None

    def export(self, table, mode):
        qs = table.full_data
        if mode == ExportMode.CSV:
            echo_buffer = Echo()
            csv_writer = csv.writer(echo_buffer)

            # By using a generator expression to write each row in the queryset python calculates each row as needed, rather than all at once.
            rows = (csv_writer.writerow(row) for row in qs)

            response = StreamingHttpResponse(
                rows,
                content_type="text/csv",
                headers={"Content-Disposition": 'attachment; filename=Lexique.csv'}
            )

        # https://hakibenita.com/python-django-optimizing-excel-export
        elif mode == ExportMode.EXCEL:
            stream = io.BytesIO()

            workbook = Workbook()
            sheet = workbook.new_sheet("OpenLexicon", data= qs)

            workbook.save(stream)
            stream.seek(0)
            # TODO : try to make this work with StreamingHttpResponse
            response = HttpResponse(stream.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            response['Content-Disposition'] = 'attachment; filename=Lexique.xlsx'
        else:
            raise Exception("Invalid export format")

        return response


    def get(self, request, *args, **kwargs):
        export_mode = request.GET.get("export_mode")
        if export_mode != None and not request.GET.get("export_post"): # get ajax url for real export
            return JsonResponse({"url": request.build_absolute_uri()}, safe=False)
        table = DataTablesServer(
            request, self.dbColMap, self.get_queryset())
        if export_mode != None:
            return self.export(table, export_mode)
        else:
            return JsonResponse(table.output_result(), safe=False)

    def get_queryset(self):
        """
        Return the list of items for this view.

        The return value must be an iterable and may be an instance of
        `QuerySet` in which case `QuerySet` specific behavior will be enabled.
        """
        if self.queryset is not None:
            queryset = self.queryset
            if isinstance(queryset, QuerySet):
                queryset = queryset.all()
        elif self.model is not None:
            queryset = self.model._default_manager.all()
        else:
            raise ImproperlyConfigured(
                "%(cls)s is missing a QuerySet. Define "
                "%(cls)s.model, %(cls)s.queryset, or override "
                "%(cls)s.get_queryset()." % {
                    'cls': self.__class__.__name__
                }
            )

        return queryset
