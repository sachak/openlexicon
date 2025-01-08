# https://github.com/umesh-krishna/django_serverside_datatable
# https://pypi.org/project/django-serverside-datatable/2.1.0/#files
from django.views import View
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse
from django.core.exceptions import ImproperlyConfigured
from django.db.models import QuerySet, F
from collections import namedtuple
import operator
from .models import ExportMode
from django.db.models import Q
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
        self.column_list = ["ortho"] + [x.replace("__", "__jsonData__") for x in self.dbColMap.column_list] # change pattern for column_name from database__col_name to database__jsonData__col_name
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
        output['iTotalRecords'] = str(self.qs.count())
        output['iTotalDisplayRecords'] = str(self.cardinality_filtered)
        data_rows = []

        for row in self.result_data:
            data_row = []
            for i in range(len(self.column_list)):
                val = row[self.column_list[i]]
                data_row.append(val)
            data_rows.append(data_row)
        output['aaData'] = data_rows
        return output

    def group_data(self, data_list):
        # Keep only words with entries in all selected databases

        current_dict = None
        final_data = []
        for row in data_list:
            if current_dict is None or row["ortho"] != current_dict["ortho"]:
                current_dict = row
                final_data.append(current_dict)
            else:
                current_dict = {**current_dict, **row}
        final_data.append(current_dict)
        return final_data

    def run_queries(self):
        # pages has 'start' and 'length' attributes
        pages = self.paging()
        # the term you entered into the datatable search
        _filter, op = self.filtering()
        # the document field you chose to sort
        sorting = self.sorting()
        # custom filter
        qs = self.qs

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

        qs = qs.order_by("ortho")
        # self.full_data = qs.values_list(*self.attr_list) # TODO : for export
        # Rename attributes (jsonData__attr) to column_list pattern (database__jsonData__attr)
        attr_list = [x.replace(x.split("jsonData", 1)[0], "") for x in self.column_list]
        # TODO : check if same column_names in several databases can be an issue
        data = qs.values("ortho", **{self.column_list[i]:F(attr_list[i]) for i in range(1, len(self.column_list))}).distinct("ortho")
        print(data.count())
        # TODO : regroup
        # data =
        # if sorting != "":
        #     data = data.order_by('%s' % sorting)
        len_data = data.count()
        _index = int(pages.start)
        data = data[_index:_index + (pages.length - pages.start)]

        self.result_data = list(data)

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
                    filter.append((f"{self.column_list[i]}__icontains", col_elt))
                elif (column_list and len(column_list) == 2) : # numbers. WARNING : range does not work with JSONField on SQLite. It works on server with Postgresql.
                    filter.append((f"{self.column_list[i]}__range", column_list))
        q_list = []
        for query in filter:
            if "jsonData" in query[0]: # if jsonData, use original query filter only if DatabaseObject has relevant database (has other database OR apply original query filter)
                col_elts = query[0].split("__", 1)
                database_name = col_elts[0]
                col_name = col_elts[1]
                q_list.append((~Q((f'database__name', database_name)) | Q((col_name, query[1]))))
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
