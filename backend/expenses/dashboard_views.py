from django.db.models import Sum
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Transaction


class DashboardView(APIView):
    def get(self, request):
        qs = Transaction.objects.filter(user=request.user)
        income = qs.filter(type='income').aggregate(total=Sum('amount'))['total'] or 0
        expense = qs.filter(type='expense').aggregate(total=Sum('amount'))['total'] or 0
        return Response({
            'total_income': income,
            'total_expense': expense,
            'balance': income - expense,
        })
