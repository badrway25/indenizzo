from django.urls import path

from . import views

app_name = "crm"

urlpatterns = [
    path("contact/", views.contact, name="contact"),
    path("contact/thank-you/", views.contact_thank_you, name="contact_thank_you"),
]
