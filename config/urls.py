from django.contrib import admin
from django.urls import path

from expenses import views

urlpatterns = [
    path('', views.home, name='home'),
    path('activity/', views.activity, name='activity'),
    path('add/', views.add_transaction, name='add'),
    path('admin/', admin.site.urls),
]
