"""Pagination มาตรฐานของทุก list endpoint"""
from rest_framework.pagination import PageNumberPagination


class DefaultPagination(PageNumberPagination):
    """แบ่งหน้าแบบ page number — frontend ส่ง ?page= และ ?page_size= ได้"""

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 200
