"""Stored accounts, courses, applications, and reviews."""
import os
from cryptography.fernet import Fernet
from django.contrib.auth.models import User
from django.db import models


def cipher():
    """Build the field cipher from a deployment secret."""
    key = os.getenv('DATA_ENCRYPTION_KEY')
    if not key:
        raise RuntimeError('DATA_ENCRYPTION_KEY is required')
    return Fernet(key.encode())


class EncryptedTextField(models.TextField):
    """Encrypt personal fields before storage and decrypt after loading."""

    def from_db_value(self, value, expression, connection):
        """Decrypt a stored personal value when Django loads a record."""
        return cipher().decrypt(value.encode()).decode() if value else value

    def to_python(self, value):
        """Keep already decoded application values as plain strings."""
        return value

    def get_prep_value(self, value):
        """Encrypt a personal value before a database write."""
        return cipher().encrypt(value.encode()).decode() if value else value


class Profile(models.Model):
    """Personal details stored separately from the Django login record."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    surname = EncryptedTextField()
    given_name = EncryptedTextField()
    patronymic = EncryptedTextField()
    phone = EncryptedTextField()
    email = EncryptedTextField()
    email_digest = models.CharField(max_length=64, unique=True)
    address = EncryptedTextField()
    consented_at = models.DateTimeField()


class Course(models.Model):
    """A course available to learners."""
    title = models.CharField(max_length=120, unique=True)
    description = models.TextField()
    active = models.BooleanField(default=True)


class Application(models.Model):
    """A learner request with a strictly ordered status."""
    NEW = 'new'
    ACTIVE = 'active'
    DONE = 'done'
    STATUS = [(NEW, 'Новая'), (ACTIVE, 'Идет обучение'), (DONE, 'Обучение завершено')]
    PAYMENT = [('cash', 'Наличными'), ('transfer', 'Переводом по номеру телефона')]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    course = models.ForeignKey(Course, on_delete=models.PROTECT)
    start_date = models.DateField()
    payment = models.CharField(max_length=10, choices=PAYMENT)
    status = models.CharField(max_length=10, choices=STATUS, default=NEW)
    created_at = models.DateTimeField(auto_now_add=True)


class Review(models.Model):
    """One learner review for a completed application."""
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name='review')
    rating = models.PositiveSmallIntegerField()
    text = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)


class LoginAttempt(models.Model):
    """Shared database counter for login attempts by IP and login digest."""
    key = models.CharField(max_length=64, unique=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    expires_at = models.DateTimeField()
