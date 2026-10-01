"""
URL configuration for sms_platform project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path

from billing.views import package_store_view, transaction_page_view
from campaigns.views import bulk_mail_view, bulk_sms_view, mail_history_view, scheduled_history_view, scheduled_message_view, sender_name_view, simple_message_view, sms_history_view
from support.views import support_page_view
from contacts.views import contact_mail_page_view, contacts_page_view
from users.views import UserListView

urlpatterns = [
    path('', include('users.urls')),
    path('packages/', package_store_view, name='package-store'),
    path('transactions/', transaction_page_view, name='transaction-page'),
    path('contacts/', contacts_page_view, name='contacts-page'),
    path('contact-mail/', contact_mail_page_view, name='contact-mail-page'),
    path('messages/sender-name/', sender_name_view, name='sender-name'),
    path('messages/simple/', simple_message_view, name='simple-message'),
    path('messages/bulk-sms/', bulk_sms_view, name='bulk-sms'),
    path('messages/sms-history/', sms_history_view, name='sms-history'),
    path('messages/bulk-mail/', bulk_mail_view, name='bulk-mail'),
    path('messages/mail-history/', mail_history_view, name='mail-history'),
    path('messages/scheduled/', scheduled_message_view, name='scheduled-message'),
    path('messages/scheduled-history/', scheduled_history_view, name='scheduled-history'),
    path('support/', support_page_view, name='support-page'),
    path('admin/', admin.site.urls),
    path('api/users/', UserListView.as_view(), name='user-list'),
    path('api/contacts/', include('contacts.urls')),
    path('api/campaigns/', include('campaigns.urls')),
    path('api/billing/', include('billing.urls')),
    path('api/support/', include('support.urls')),
]
