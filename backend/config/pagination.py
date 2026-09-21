from rest_framework.pagination import PageNumberPagination


class DefaultPageNumberPagination(PageNumberPagination):
    """支持前端传入 page_size 参数的自定义分页类"""
    page_size_query_param = 'page_size'
    max_page_size = 1000
