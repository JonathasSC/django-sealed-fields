from django.urls import include, path

urlpatterns = [
    path("", include("serve_files.urls")),
]
