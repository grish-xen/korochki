"""Создаёт таблицу для учёта попыток входа."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0002_seed_courses"),
    ]

    operations = [
        migrations.CreateModel(
            name="LoginAttempt",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("key", models.CharField(max_length=64, unique=True)),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("expires_at", models.DateTimeField()),
            ],
        ),
    ]
