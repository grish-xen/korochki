"""Проверяет основные действия в заданной базе с откатом изменений."""

import json
import secrets
import string
from datetime import timedelta
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.test import Client
from django.utils import timezone
from portal.models import Application, Course, Review


class Command(BaseCommand):
    """Проверяет регистрацию, вход, заявки, статусы и отзывы."""

    help = "Run a rollback-only smoke test against the configured MySQL database"

    def handle(self, *args, **options):
        """Вызывает API и откатывает все созданные записи."""
        if connection.vendor != "mysql":
            raise CommandError("The smoke test requires the configured MySQL database")
        suffix = "".join(secrets.choice(string.ascii_letters) for _ in range(8))
        username = "Smoke" + suffix
        email = suffix.lower() + "@x.ru"
        password = "Aa1!" + "".join(
            secrets.choice(string.ascii_letters + string.digits) for _ in range(12)
        )
        client = Client(enforce_csrf_checks=True, SERVER_NAME="localhost")

        def send(path, data, csrf):
            """Отправляет запрос к API с защитой CSRF."""
            return client.post(
                path,
                data=json.dumps(data),
                content_type="application/json",
                HTTP_X_CSRFTOKEN=csrf,
            )

        def expect(response, status):
            """Завершает проверку с кратким сообщением при ошибке API."""
            if response.status_code != status:
                raise CommandError(
                    f"{response.wsgi_request.path} returned {response.status_code}, expected {status}"
                )

        with transaction.atomic():
            csrf = client.get("/api/session").json()["csrf"]
            expect(
                send(
                    "/api/register",
                    {
                        "username": username,
                        "password": password,
                        "surname": "Иванова",
                        "given_name": "Анна",
                        "patronymic": "Петровна",
                        "phone": "8(999)123-45-67",
                        "email": email,
                        "address": "Москва",
                        "consent": True,
                    },
                    csrf,
                ),
                201,
            )
            user = User.objects.get(username=username)
            if not user.check_password(password):
                raise CommandError("Password hashing failed")
            csrf = client.get("/api/session").json()["csrf"]
            course = Course.objects.first()
            if Course.objects.count() != 3 or course is None:
                raise CommandError("The course catalogue is incomplete")
            start_date = (timezone.localdate() + timedelta(days=3)).isoformat()
            expect(
                send(
                    "/api/applications",
                    {
                        "course_id": course.id,
                        "start_date": start_date,
                        "payment": "cash",
                    },
                    csrf,
                ),
                201,
            )
            application = Application.objects.get(user=user)
            expect(
                send(
                    f"/api/applications/{application.id}/review",
                    {"rating": 5, "text": "Хорошо"},
                    csrf,
                ),
                409,
            )
            expect(send("/api/logout", {}, csrf), 200)

            admin_name = "Admin" + suffix
            User.objects.create_user(
                username=admin_name, password=password, is_staff=True
            )
            csrf = client.get("/api/session").json()["csrf"]
            expect(
                send(
                    "/api/login", {"username": admin_name, "password": password}, csrf
                ),
                200,
            )
            csrf = client.get("/api/session").json()["csrf"]
            expect(client.get("/api/admin/applications"), 200)
            expect(
                send(
                    f"/api/admin/applications/{application.id}/status",
                    {"status": "active"},
                    csrf,
                ),
                200,
            )
            expect(
                send(
                    f"/api/admin/applications/{application.id}/status",
                    {"status": "done"},
                    csrf,
                ),
                200,
            )
            expect(send("/api/logout", {}, csrf), 200)

            csrf = client.get("/api/session").json()["csrf"]
            expect(
                send("/api/login", {"username": username, "password": password}, csrf),
                200,
            )
            csrf = client.get("/api/session").json()["csrf"]
            expect(
                send(
                    f"/api/applications/{application.id}/review",
                    {"rating": 5, "text": "Хорошо"},
                    csrf,
                ),
                201,
            )
            if Review.objects.filter(application=application).count() != 1:
                raise CommandError("Review was not stored")
            transaction.set_rollback(True)
        self.stdout.write(
            self.style.SUCCESS("MySQL smoke test passed; test data rolled back")
        )
