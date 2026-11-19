from django.contrib import admin

from . import models


@admin.register(models.Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['date', 'user', 'kind', 'description', 'category', 'amount']
    list_filter = ['kind', 'category']
    search_fields = ['description', 'note']


admin.site.register([models.Account, models.Budget, models.Goal, models.Contribution, models.Debt, models.Investment, models.Household])
