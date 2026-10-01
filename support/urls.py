from django.urls import path

from .views import SupportTicketListView

urlpatterns = [
    path('', SupportTicketListView.as_view(), name='support-ticket-list'),
]
