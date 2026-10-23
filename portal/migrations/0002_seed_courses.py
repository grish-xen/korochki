"""Seed the three programmes specified by the assignment."""
from django.db import migrations


def seed_courses(apps, schema_editor):
    """Create catalogue records without changing existing titles."""
    Course = apps.get_model('portal', 'Course')
    entries = [
        ('Основы алгоритмизации и программирования', 'От первых алгоритмов до понятного работающего кода.'),
        ('Основы веб-дизайна', 'Композиция, типографика и удобные интерфейсы для разных экранов.'),
        ('Основы проектирования баз данных', 'Таблицы, связи и запросы для надёжного хранения данных.'),
    ]
    for title, description in entries:
        Course.objects.get_or_create(title=title, defaults={'description': description})


class Migration(migrations.Migration):
    """Add initial course choices."""
    dependencies = [('portal', '0001_initial')]
    operations = [migrations.RunPython(seed_courses, migrations.RunPython.noop)]
