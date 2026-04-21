from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dota', '0006_add_vs_bots'),
    ]

    operations = [
        migrations.AddField(
            model_name='lobby',
            name='dota_lobby_id',
            field=models.BigIntegerField(blank=True, null=True),
        ),
    ]
