from django.urls import path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
# from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.inspectors import CoreAPICompatInspector, NotHandled

schema_view = get_schema_view(
    openapi.Info(
        title='CyberT API',
        description='API documentation',
        contact=openapi.Contact(email='Adilan.Akhramovich@gmail.com'),
        default_version='v1',
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

swagger_urlpatterns = [
    path(
        'swagger/',
        schema_view.with_ui('swagger', cache_timeout=0),
        name='schema-swagger-ui'
    ),
    path(
        'redoc/',
        schema_view.with_ui('redoc', cache_timeout=0),
        name='schema-redoc'
    ),
]


# class FilterDescriptionInspector(CoreAPICompatInspector):
#     def get_filter_parameters(self, filter_backend):
#         if isinstance(filter_backend, DjangoFilterBackend):
#             return [
#                 self.change_description_if_none(param=param)
#                 for param in super().get_filter_parameters(filter_backend)
#             ]
#         return NotHandled
#
#     @staticmethod
#     def change_description_if_none(param):
#         filter_default = {'': f'Filter the returned list by {param.name}'}
#         param.description = filter_default.get(
#             param.description, param.description
#         )
#         return param

