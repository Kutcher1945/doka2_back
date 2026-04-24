from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dota', '0008_lobby_assigned_bot'),
    ]

    operations = [
        migrations.AddField(
            model_name='lobby',
            name='bot_steam_id',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
