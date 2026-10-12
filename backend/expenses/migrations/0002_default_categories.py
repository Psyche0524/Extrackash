from django.db import migrations

EXPENSE = ['Food', 'Transportation', 'Bills', 'Shopping', 'Entertainment', 'Education', 'Health', 'Other']
INCOME = ['Salary', 'Allowance', 'Business', 'Other Income']


def add_defaults(apps, schema_editor):
    Category = apps.get_model('expenses', 'Category')
    for name in EXPENSE:
        Category.objects.get_or_create(user=None, name=name, type='expense')
    for name in INCOME:
        Category.objects.get_or_create(user=None, name=name, type='income')


def remove_defaults(apps, schema_editor):
    apps.get_model('expenses', 'Category').objects.filter(user=None).delete()


class Migration(migrations.Migration):
    dependencies = [('expenses', '0001_initial')]
    operations = [migrations.RunPython(add_defaults, remove_defaults)]
