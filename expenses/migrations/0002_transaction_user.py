import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def give_old_rows_an_owner(apps, schema_editor):
    # Rows made before login existed: hand them to the first account, or drop them if there is none.
    Transaction = apps.get_model('expenses', 'Transaction')
    User = apps.get_model(*settings.AUTH_USER_MODEL.split('.'))
    first = User.objects.order_by('id').first()
    if first:
        Transaction.objects.filter(user__isnull=True).update(user=first)
    else:
        Transaction.objects.filter(user__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to=settings.AUTH_USER_MODEL),
        ),
        migrations.RunPython(give_old_rows_an_owner, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='transaction',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to=settings.AUTH_USER_MODEL),
        ),
    ]
