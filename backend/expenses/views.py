from django.db.models import Q
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied

from .models import Category, Transaction
from .serializers import CategorySerializer, TransactionSerializer


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer

    def get_queryset(self):
        # default categories (user=None) + the user's own
        return Category.objects.filter(Q(user=None) | Q(user=self.request.user))

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        # default categories (user=None) cannot be edited by normal users
        if serializer.instance.user_id is None:
            raise PermissionDenied('Default categories cannot be changed.')
        serializer.save()

    def perform_destroy(self, instance):
        if instance.user_id is None:
            raise PermissionDenied('Default categories cannot be deleted.')
        instance.delete()


class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    forced_type = None  # set in subclasses

    def get_queryset(self):
        qs = Transaction.objects.filter(user=self.request.user)
        if self.forced_type:
            qs = qs.filter(type=self.forced_type)
        else:
            tx_type = self.request.query_params.get('type')
            if tx_type in ('income', 'expense'):
                qs = qs.filter(type=tx_type)
        return qs

    def perform_create(self, serializer):
        extra = {'type': self.forced_type} if self.forced_type else {}
        serializer.save(user=self.request.user, **extra)


class ExpenseViewSet(TransactionViewSet):
    forced_type = 'expense'


class IncomeViewSet(TransactionViewSet):
    forced_type = 'income'
