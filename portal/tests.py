"""End-to-end API checks for validation, access, CSRF, and status rules."""
import hashlib
import json
from datetime import timedelta
from django.contrib.auth.models import User
from django.db import connection
from django.test import Client, TestCase
from django.utils import timezone
from .models import Application, Course, Profile, Review


class PortalFlowTests(TestCase):
    """Exercise the protected learner and administrator paths."""

    def setUp(self):
        """Give each test a browser that enforces CSRF validation."""
        self.client = Client(enforce_csrf_checks=True)
        self.csrf = self.client.get('/api/session').json()['csrf']

    def post(self, path, payload, csrf=True):
        """Submit a JSON request with an optional CSRF token."""
        headers = {'HTTP_X_CSRFTOKEN': self.csrf} if csrf else {}
        return self.client.post(path, data=json.dumps(payload), content_type='application/json', **headers)

    def register(self, username='Student'):
        """Register one valid learner and refresh the rotated token."""
        response = self.post('/api/register', {
            'username': username, 'password': 'Strong1!', 'surname': 'Иванова',
            'given_name': 'Анна', 'patronymic': 'Петровна', 'phone': '8(999)123-45-67',
            'email': f'{username.lower()}@x.ru', 'address': 'Москва', 'consent': True,
        })
        self.csrf = self.client.get('/api/session').json()['csrf']
        return response

    def test_registration_encrypts_profile_and_hashes_password(self):
        """A valid registration stores no clear-text personal data or password."""
        self.assertEqual(self.register().status_code, 201)
        user = User.objects.get(username='Student')
        self.assertNotEqual(user.password, 'Strong1!')
        self.assertTrue(user.check_password('Strong1!'))
        with connection.cursor() as cursor:
            cursor.execute('SELECT surname FROM portal_profile WHERE user_id = %s', [user.id])
            raw = cursor.fetchone()[0]
        self.assertNotEqual(raw, 'Иванова')
        self.assertEqual(user.profile.surname, 'Иванова')
        self.assertNotEqual(user.profile.email_digest, hashlib.sha256(b'student@x.ru').hexdigest())
        self.assertEqual(self.register().status_code, 400)

    def test_consent_validation_and_csrf(self):
        """Missing consent and missing CSRF token both prevent registration."""
        payload = {'username': 'Student', 'password': 'Strong1!', 'surname': 'Иванова', 'given_name': 'Анна',
                   'patronymic': 'Петровна', 'phone': '8(999)123-45-67', 'email': 's@x.ru', 'address': 'Москва'}
        self.assertEqual(self.post('/api/register', payload).status_code, 400)
        payload['consent'] = True
        self.assertEqual(self.post('/api/register', payload, csrf=False).status_code, 403)

    def test_registration_rejects_non_string_fields_and_foreign_digits(self):
        """Malformed JSON types and Unicode lookalike digits never enter a profile."""
        payload = {
            'username': 'Student', 'password': 'Strong1!', 'surname': 'Иванова',
            'given_name': 'Анна', 'patronymic': 'Петровна',
            'phone': '8(٩٩٩)123-45-67', 'email': 'student@x.ru',
            'address': {'city': 'Москва'}, 'consent': True,
        }
        response = self.post('/api/register', payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn('phone', response.json()['fields'])
        self.assertIn('address', response.json()['fields'])
        self.assertFalse(User.objects.filter(username='Student').exists())

    def test_application_rejects_malformed_types_and_review_rating(self):
        """Course, date, and rating use their declared types and ranges."""
        self.assertEqual(self.register().status_code, 201)
        course = Course.objects.first()
        start = (timezone.localdate() + timedelta(days=2)).isoformat()
        for course_id in (True, {'id': course.id}, str(course.id)):
            self.assertEqual(self.post('/api/applications', {
                'course_id': course_id, 'start_date': start, 'payment': 'cash',
            }).status_code, 400)
        self.assertEqual(self.post('/api/applications', {
            'course_id': course.id, 'start_date': {'date': start}, 'payment': 'cash',
        }).status_code, 400)
        response = self.post('/api/applications', {
            'course_id': course.id, 'start_date': start, 'payment': 'cash',
        })
        self.assertEqual(response.status_code, 201)
        item = Application.objects.get()
        item.status = Application.DONE
        item.save(update_fields=['status'])
        for rating in (3.5, True, {'rating': 5}):
            self.assertEqual(self.post(f'/api/applications/{item.id}/review', {
                'rating': rating, 'text': 'Хорошо',
            }).status_code, 400)
        self.assertEqual(self.post(f'/api/applications/{item.id}/review', {
            'rating': 5, 'text': {'message': 'Хорошо'},
        }).status_code, 400)
        self.assertFalse(Review.objects.exists())

    def test_application_status_review_and_access(self):
        """Learners see only their records and can review a completed course once."""
        self.register()
        course = Course.objects.first()
        start = (timezone.localdate() + timedelta(days=2)).isoformat()
        response = self.post('/api/applications', {'course_id': course.id, 'start_date': start, 'payment': 'cash'})
        self.assertEqual(response.status_code, 201)
        item = Application.objects.get()
        self.assertEqual(item.status, Application.NEW)
        self.assertEqual(self.post(f'/api/applications/{item.id}/review', {'rating': 5, 'text': 'Отлично'}).status_code, 409)
        self.assertEqual(self.post(f'/api/admin/applications/{item.id}/status', {'status': 'active'}).status_code, 403)
        self.client.logout()
        other = User.objects.create_user(username='Another', password='Another1!')
        self.client.force_login(other)
        self.csrf = self.client.get('/api/session').json()['csrf']
        self.assertEqual(self.client.get('/api/applications').json()['applications'], [])
        self.assertEqual(self.post(f'/api/applications/{item.id}/review', {'rating': 5, 'text': 'Чужой'}).status_code, 404)
        self.client.logout()
        admin = User.objects.create_user(username='Administrator', password='Another1!', is_staff=True)
        self.client.force_login(admin)
        self.csrf = self.client.get('/api/session').json()['csrf']
        self.assertEqual(self.post(f'/api/admin/applications/{item.id}/status', {'status': 'done'}).status_code, 409)
        self.assertEqual(self.post(f'/api/admin/applications/{item.id}/status', {'status': 'active'}).status_code, 200)
        self.assertEqual(self.post(f'/api/admin/applications/{item.id}/status', {'status': 'done'}).status_code, 200)
        self.client.logout()
        self.client.force_login(item.user)
        self.csrf = self.client.get('/api/session').json()['csrf']
        self.assertEqual(self.post(f'/api/applications/{item.id}/review', {'rating': 5, 'text': 'Отлично'}).status_code, 201)
        self.assertEqual(Review.objects.count(), 1)
        self.assertEqual(self.post(f'/api/applications/{item.id}/review', {'rating': 4, 'text': 'Ещё'}).status_code, 409)

    def test_search_rejects_patterns_and_markup(self):
        """The course search accepts words and rejects pattern syntax."""
        self.assertEqual(self.client.get('/api/search?q=Основы').status_code, 200)
        self.assertEqual(self.client.get('/api/search?q=.*').status_code, 400)
        self.assertEqual(self.client.get('/api/search?q=%3Cscript%3E').status_code, 400)

    def test_cookie_notice_and_security_headers(self):
        """The acknowledgement cookie and browser protections are issued."""
        response = self.post('/api/cookie-ack', {})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.cookies['cookie_ack']['httponly'])
        self.assertEqual(response.cookies['cookie_ack']['samesite'], 'Lax')
        self.assertEqual(self.client.get('/api/session').json()['cookie_ack'], True)
        response = self.client.get('/api/courses')
        self.assertIn("default-src 'self'", response['Content-Security-Policy'])
        self.assertEqual(response['X-Frame-Options'], 'DENY')
        self.assertEqual(response['Cache-Control'], 'no-store')

    def test_login_locks_after_five_failed_attempts(self):
        """The sixth attempt is blocked even with a valid password."""
        self.register()
        self.post('/api/logout', {})
        for _ in range(5):
            response = self.post('/api/login', {'username': 'Student', 'password': 'Wrong1!'})
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json()['error'], 'Логин или пароль некорректен')
        self.assertEqual(self.post('/api/login', {'username': 'Student', 'password': 'Strong1!'}).status_code, 429)
