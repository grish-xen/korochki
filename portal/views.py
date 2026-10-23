"""Small JSON API with server-side validation and access control."""
import hashlib
import hmac
import json
import re
from datetime import date, timedelta
from pathlib import Path
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.exceptions import RequestDataTooBig
from django.db import IntegrityError, transaction
from django.http import FileResponse, Http404, JsonResponse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .models import Application, Course, LoginAttempt, Profile, Review

NAME = re.compile(r'^[А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?$')
PATRONYMIC = re.compile(r'^[А-ЯЁ][а-яё]+(?:[ -](?:[А-ЯЁ][а-яё]+|оглы|кызы))?$')
LOGIN = re.compile(r'^[A-Za-z]{6,20}$')
PHONE = re.compile(r'^8\([0-9]{3}\)[0-9]{3}-[0-9]{2}-[0-9]{2}$')
EMAIL = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
PASSWORD = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[$#@!])[A-Za-z0-9$#@!]{8,}$')


def error(message, status=400, fields=None):
    """Return a safe, consistent validation error."""
    return JsonResponse({'error': message, 'fields': fields or {}}, status=status)


def body(request):
    """Read one JSON object; never accept a large or malformed payload."""
    try:
        raw = request.body
    except RequestDataTooBig as exc:
        raise ValueError('Слишком большой запрос') from exc
    if len(raw) > 1024 * 1024:
        raise ValueError('Слишком большой запрос')
    value = json.loads(raw or b'{}')
    if not isinstance(value, dict):
        raise ValueError('Ожидается объект JSON')
    return value


def string_field(data, name, *, lowercase=False):
    """Accept only JSON strings for text fields and normalize surrounding space."""
    value = data.get(name)
    if not isinstance(value, str):
        return ''
    value = value.strip()
    return value.lower() if lowercase else value


def email_lookup_digest(email):
    """Make a keyed, non-reversible email index for uniqueness checks."""
    return hmac.new(settings.SECRET_KEY.encode(), email.encode(), hashlib.sha256).hexdigest()


def require_user(request, staff=False):
    """Check the current server session for each protected operation."""
    if not request.user.is_authenticated:
        return error('Войдите в аккаунт', 401)
    if staff and not request.user.is_staff:
        return error('Недостаточно прав', 403)
    return None


def serialize_application(item):
    """Return one application without exposing another user's profile."""
    review = getattr(item, 'review', None)
    return {'id': item.id, 'course': item.course.title, 'start_date': item.start_date.isoformat(),
            'payment': item.payment, 'status': item.status, 'status_label': item.get_status_display(),
            'created_at': item.created_at.isoformat(), 'username': item.user.username,
            'review': {'rating': review.rating, 'text': review.text} if review else None}


@require_http_methods(['GET'])
def session(request):
    """Provide CSRF token and the current account role."""
    return JsonResponse({'csrf': get_token(request), 'cookie_ack': request.COOKIES.get('cookie_ack') == '1', 'user': request.user.username if request.user.is_authenticated else None,
                         'staff': bool(request.user.is_authenticated and request.user.is_staff)})


@require_http_methods(['POST'])
def cookie_ack(request):
    """Remember that the visitor read the necessary-cookie notice."""
    response = JsonResponse({'ok': True})
    response.set_cookie('cookie_ack', '1', max_age=31536000, httponly=True, secure=not settings.DEBUG, samesite='Lax')
    return response


@require_http_methods(['GET'])
def courses(request):
    """List active courses from the catalogue."""
    return JsonResponse({'courses': list(Course.objects.filter(active=True).values('id', 'title', 'description'))})


@require_http_methods(['GET'])
def search(request):
    """Search course titles using a literal query, rejecting markup and patterns."""
    term = request.GET.get('q', '').strip()
    if not 2 <= len(term) <= 50 or not re.fullmatch(r'[А-Яа-яЁёA-Za-z0-9 -]+', term):
        return error('Введите от 2 до 50 букв или цифр без специальных символов')
    return JsonResponse({'courses': list(Course.objects.filter(active=True, title__icontains=term).values('id', 'title', 'description'))})


@require_http_methods(['POST'])
def register(request):
    """Validate and store a unique account with encrypted personal details."""
    try:
        data = body(request)
    except (ValueError, json.JSONDecodeError):
        return error('Проверьте данные формы')
    fields = {}
    username = string_field(data, 'username')
    surname = string_field(data, 'surname')
    given_name = string_field(data, 'given_name')
    patronymic = string_field(data, 'patronymic')
    phone = string_field(data, 'phone')
    email = string_field(data, 'email', lowercase=True)
    address = string_field(data, 'address')
    password = data.get('password') if isinstance(data.get('password'), str) else ''
    if not LOGIN.fullmatch(username): fields['username'] = '6–20 латинских букв'
    if not NAME.fullmatch(surname) or len(surname) > 20: fields['surname'] = 'Русские буквы, первая заглавная, до 20 символов'
    if not NAME.fullmatch(given_name) or len(given_name) > 20: fields['given_name'] = 'Русские буквы, первая заглавная, до 20 символов'
    if not PATRONYMIC.fullmatch(patronymic) or len(patronymic) > 20: fields['patronymic'] = 'Русские буквы, до 20 символов'
    if not PHONE.fullmatch(phone): fields['phone'] = 'Формат: 8(999)999-99-99'
    if not EMAIL.fullmatch(email) or len(email) > 20: fields['email'] = 'Корректный адрес почты до 20 символов'
    if not 1 <= len(address) <= 100: fields['address'] = 'Укажите адрес до 100 символов'
    if not PASSWORD.fullmatch(password): fields['password'] = 'От 8 символов: латинские строчная и заглавная буквы, цифра и один из $#@!'
    if data.get('consent') is not True: fields['consent'] = 'Необходимо согласие на обработку данных'
    digest = email_lookup_digest(email)
    if 'username' not in fields and User.objects.filter(username__iexact=username).exists():
        fields['username'] = 'Логин уже занят'
    if 'email' not in fields and Profile.objects.filter(email_digest=digest).exists():
        fields['email'] = 'Почта уже используется'
    if fields: return error('Исправьте поля формы', fields=fields)
    try:
        with transaction.atomic():
            user = User.objects.create_user(username=username, password=password)
            Profile.objects.create(user=user, surname=surname, given_name=given_name, patronymic=patronymic,
                                   phone=phone, email=email, email_digest=digest, address=address, consented_at=timezone.now())
    except IntegrityError:
        return error('Логин или почта уже используется', 409)
    login(request, user)
    return JsonResponse({'ok': True}, status=201)


@require_http_methods(['POST'])
def login_view(request):
    """Authenticate with a bounded per-IP and login retry counter."""
    try: data = body(request)
    except (ValueError, json.JSONDecodeError): return error('Проверьте данные формы')
    username = string_field(data, 'username')[:50]
    password = data.get('password') if isinstance(data.get('password'), str) else ''
    key = hashlib.sha256((request.META.get('REMOTE_ADDR', '') + ':' + username.lower()).encode()).hexdigest()
    now = timezone.now()
    with transaction.atomic():
        attempt, _ = LoginAttempt.objects.select_for_update().get_or_create(
            key=key, defaults={'expires_at': now + timedelta(minutes=15)})
        if attempt.expires_at <= now:
            attempt.attempts = 0
            attempt.expires_at = now + timedelta(minutes=15)
        if attempt.attempts >= 5:
            return error('Слишком много попыток. Повторите через 15 минут', 429)
        user = authenticate(request, username=username, password=password)
        if user is None:
            attempt.attempts += 1
            if attempt.attempts == 5:
                attempt.expires_at = now + timedelta(minutes=15)
            attempt.save(update_fields=['attempts', 'expires_at'])
            return error('Логин или пароль некорректен', 401)
        attempt.delete()
    login(request, user)
    return JsonResponse({'ok': True, 'staff': user.is_staff})


@require_http_methods(['POST'])
def logout_view(request):
    """Invalidate the current server session."""
    logout(request)
    return JsonResponse({'ok': True})


@require_http_methods(['GET', 'POST'])
def applications(request):
    """Create an application or list only the current user's applications."""
    denied = require_user(request)
    if denied: return denied
    if request.method == 'GET':
        items = Application.objects.filter(user=request.user).select_related('course', 'user', 'review').order_by('-created_at')
        return JsonResponse({'applications': [serialize_application(item) for item in items]})
    try: data = body(request)
    except (ValueError, json.JSONDecodeError): return error('Проверьте данные формы')
    try:
        course_id = data.get('course_id')
        start_date = data.get('start_date')
        if type(course_id) is not int or course_id < 1 or not isinstance(start_date, str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', start_date):
            raise ValueError('Invalid course or date')
        course = Course.objects.get(pk=course_id, active=True)
        start = date.fromisoformat(start_date)
    except (Course.DoesNotExist, ValueError, TypeError):
        return error('Выберите курс и корректную дату')
    if start <= timezone.localdate(): return error('Дата начала должна быть в будущем')
    if data.get('payment') not in dict(Application.PAYMENT): return error('Выберите способ оплаты')
    item = Application.objects.create(user=request.user, course=course, start_date=start, payment=data['payment'])
    return JsonResponse({'application': serialize_application(item)}, status=201)


@require_http_methods(['POST'])
def review(request, pk):
    """Allow one review from the owner after course completion."""
    denied = require_user(request)
    if denied: return denied
    try: item = Application.objects.get(pk=pk, user=request.user)
    except Application.DoesNotExist: return error('Заявка не найдена', 404)
    if item.status != Application.DONE or Review.objects.filter(application=item).exists(): return error('Отзыв доступен после завершения обучения и только один раз', 409)
    try:
        data = body(request)
        raw_rating = data.get('rating')
        if type(raw_rating) is int:
            rating = raw_rating
        elif isinstance(raw_rating, str) and re.fullmatch(r'[1-5]', raw_rating):
            rating = int(raw_rating)
        else:
            raise ValueError('Invalid rating')
    except (ValueError, TypeError, json.JSONDecodeError): return error('Проверьте отзыв')
    content = string_field(data, 'text')
    if not 1 <= rating <= 5 or not 1 <= len(content) <= 1000: return error('Оценка от 1 до 5 и текст до 1000 символов обязательны')
    Review.objects.create(application=item, rating=rating, text=content)
    return JsonResponse({'ok': True}, status=201)


@require_http_methods(['GET'])
def admin_applications(request):
    """List ten applications per page with an optional status filter."""
    denied = require_user(request, staff=True)
    if denied: return denied
    try: page = max(1, int(request.GET.get('page', '1')))
    except ValueError: return error('Номер страницы должен быть числом')
    status = request.GET.get('status', '')
    if status and status not in dict(Application.STATUS): return error('Неизвестный статус')
    items = Application.objects.select_related('course', 'user', 'review').order_by('-created_at')
    if status: items = items.filter(status=status)
    total = items.count()
    return JsonResponse({'applications': [serialize_application(item) for item in items[(page-1)*10:page*10]],
                         'total': total, 'page': page, 'pages': max(1, (total + 9) // 10)})


@require_http_methods(['POST'])
def change_status(request, pk):
    """Advance an application through the only allowed status sequence."""
    denied = require_user(request, staff=True)
    if denied: return denied
    try: data = body(request)
    except (ValueError, json.JSONDecodeError): return error('Проверьте данные')
    with transaction.atomic():
        try: item = Application.objects.select_for_update().get(pk=pk)
        except Application.DoesNotExist: return error('Заявка не найдена', 404)
        next_status = {Application.NEW: Application.ACTIVE, Application.ACTIVE: Application.DONE}.get(item.status)
        if data.get('status') != next_status: return error('Статус можно менять только последовательно', 409)
        item.status = next_status
        item.save(update_fields=['status'])
    return JsonResponse({'application': serialize_application(item)})


@require_http_methods(['GET'])
def frontend(request, path=''):
    """Serve the built client and its same-origin assets."""
    root = (settings.BASE_DIR / 'frontend' / 'dist').resolve()
    candidate = (root / path).resolve()
    if path and candidate.is_file() and candidate.is_relative_to(root): return FileResponse(candidate.open('rb'))
    index = root / 'index.html'
    if not index.exists(): raise Http404('Сначала выполните npm run build')
    return FileResponse(index.open('rb'), content_type='text/html')
