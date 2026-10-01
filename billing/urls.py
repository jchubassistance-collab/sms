from django.urls import path

from .views import PackageListView, TransactionListView, purchase_package_view, purchase_status_view

urlpatterns = [
    path('packages/', PackageListView.as_view(), name='package-list'),
    path('transactions/', TransactionListView.as_view(), name='transaction-list'),
    path('packages/purchase/', purchase_package_view, name='purchase-package'),
    path('packages/purchase/<int:transaction_id>/status/', purchase_status_view, name='purchase-status'),
]
