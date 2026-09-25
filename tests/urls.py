from django.urls import include, path

urlpatterns = [
    path("", include("sealed_fields.serve.urls")),
]
