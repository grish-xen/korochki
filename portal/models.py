"""Модели пользователей, курсов, заявок и отзывов."""

import os
from cryptography.fernet import Fernet
from django.contrib.auth.models import User
from django.db import models


def cipher():
    """Создаёт шифр для полей из секретного ключа окружения."""
    key = os.getenv("DATA_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("DATA_ENCRYPTION_KEY is required")
    return Fernet(key.encode())


class EncryptedTextField(models.TextField):
    """Шифрует личные данные при записи и расшифровывает при чтении."""

    def from_db_value(self, value, expression, connection):
        """Расшифровывает значение при загрузке записи из базы."""
        return cipher().decrypt(value.encode()).decode() if value else value

    def to_python(self, value):
        """Оставляет уже расшифрованные значения строками."""
        return value

    def get_prep_value(self, value):
        """Шифрует личное значение перед записью в базу."""
        return cipher().encrypt(value.encode()).decode() if value else value


class Profile(models.Model):
    """Личные данные, отделённые от учётной записи Django."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    surname = EncryptedTextField()
    given_name = EncryptedTextField()
    patronymic = EncryptedTextField()
    phone = EncryptedTextField()
    email = EncryptedTextField()
    email_digest = models.CharField(max_length=64, unique=True)
    address = EncryptedTextField()
    consented_at = models.DateTimeField()


class Course(models.Model):
    """Курс, доступный слушателям."""

    title = models.CharField(max_length=120, unique=True)
    description = models.TextField()
    active = models.BooleanField(default=True)


class Application(models.Model):
    """Заявка слушателя с последовательной сменой статуса."""

    NEW = "new"
    ACTIVE = "active"
    DONE = "done"
    STATUS = [(NEW, "Новая"), (ACTIVE, "Идет обучение"), (DONE, "Обучение завершено")]
    PAYMENT = [("cash", "Наличными"), ("transfer", "Переводом по номеру телефона")]
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="applications"
    )
    course = models.ForeignKey(Course, on_delete=models.PROTECT)
    start_date = models.DateField()
    payment = models.CharField(max_length=10, choices=PAYMENT)
    status = models.CharField(max_length=10, choices=STATUS, default=NEW)
    created_at = models.DateTimeField(auto_now_add=True)


class Review(models.Model):
    """Отзыв слушателя по завершённой заявке."""

    application = models.OneToOneField(
        Application, on_delete=models.CASCADE, related_name="review"
    )
    rating = models.PositiveSmallIntegerField()
    text = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)


class LoginAttempt(models.Model):
    """Счётчик попыток входа по IP-адресу и логину."""

    key = models.CharField(max_length=64, unique=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    expires_at = models.DateTimeField()
