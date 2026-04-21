from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dota', '0007_lobby_dota_lobby_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='lobby',
            name='assigned_bot',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='lobbies',
                to='dota.bot',
            ),
        ),
    ]
