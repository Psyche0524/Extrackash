from rest_framework.routers import DefaultRouter

from .views import SavingsGoalViewSet

router = DefaultRouter()
router.register('savings', SavingsGoalViewSet, basename='savings')

urlpatterns = router.urls
