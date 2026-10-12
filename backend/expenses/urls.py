from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, ExpenseViewSet, IncomeViewSet, TransactionViewSet

router = DefaultRouter()
router.register('categories', CategoryViewSet, basename='category')
router.register('transactions', TransactionViewSet, basename='transaction')
router.register('expenses', ExpenseViewSet, basename='expense')
router.register('income', IncomeViewSet, basename='income')

urlpatterns = router.urls
