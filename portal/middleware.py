"""Добавляет заголовки безопасности к каждому ответу."""


class SecurityHeadersMiddleware:
    """Применяет ограничения безопасности к ответам API и HTML."""

    def __init__(self, get_response):
        """Сохраняет следующий обработчик запроса."""
        self.get_response = get_response

    def __call__(self, request):
        """Добавляет защитные заголовки и запрещает кэширование ответов API."""
        response = self.get_response(request)
        response["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        )
        response["X-Frame-Options"] = "DENY"
        response["X-Content-Type-Options"] = "nosniff"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
        )
        response["Cross-Origin-Resource-Policy"] = "same-origin"
        response["X-Permitted-Cross-Domain-Policies"] = "none"
        if request.path.startswith("/api/"):
            response["Cache-Control"] = "no-store"
        return response
