import os
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from .core.config import settings, validate_production_config
from .rate_limit import limiter
from .middleware import HTTPSRedirectMiddleware, RequestIDMiddleware
from .csrf import CSRFMiddleware
from .error_handler import handle_http_exception, handle_validation_exception, handle_generic_exception

from .db import Base, engine, get_db
from .routers import auth, users, availability, notifications, dogs, websocket, messages
from .fcm import initialize_firebase
from .logging_config import configure_logging, get_logger
from .sentry_config import init_sentry
from prometheus_fastapi_instrumentator import Instrumentator
import signal
import sys


# Initialize logging first (before any other imports that might log)
configure_logging()
logger = get_logger(__name__)

# Initialize Sentry for error tracking
init_sentry()


def create_app() -> FastAPI:
	# Validate production configuration before starting
	if settings.app_env == "prod":
		validate_production_config()

	logger.info("application_starting", environment=settings.app_env)

	# Initialize Firebase for push notifications
	initialize_firebase()

	app = FastAPI(
		title="Regami API",
		version="1.0.0",
		description="""
## Regami - Dog Care Matching Platform

Connect dog owners to arrange mutual care, walks, and playdates.

### Features

* **Authentication**: JWT-based user registration and login
* **Dog Profiles**: Create and manage multiple dog profiles with photos
* **Availability**: Post when you need care or can offer care
* **Matching**: Find compatible matches based on location, time, and dog compatibility
* **Real-time Messaging**: WebSocket-based chat between matched users
* **Push Notifications**: FCM notifications for matches and messages

### API Versioning

All endpoints are versioned. Use `/v1/` prefix for current API version.
Legacy endpoints (without version prefix) are deprecated and will be removed in future versions.

### Authentication

Most endpoints require authentication. Include JWT token in Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

Get your token by calling `/v1/auth/login` or `/v1/auth/register`.

### Rate Limiting

API is rate limited to prevent abuse:
- Authentication endpoints: 5 requests per minute
- General endpoints: 60 requests per minute

### Error Responses

All errors follow this format:
```json
{
	"detail": "Error message in user's language",
	"request_id": "unique-request-id"
}
```

### Language Support

API supports French (fr) and English (en). Set `Accept-Language` header:
```
Accept-Language: fr-FR,fr;q=0.9,en;q=0.8
```
		""",
		docs_url="/docs",
		redoc_url="/redoc",
		openapi_url="/openapi.json",
		contact={
			"name": "Regami Support",
			"url": "https://regami.com/support",
			"email": "support@regami.com",
		},
		license_info={
			"name": "Proprietary",
		},
	)

	# Add rate limiter
	app.state.limiter = limiter
	app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

	# Add custom exception handlers for error sanitization
	app.add_exception_handler(HTTPException, handle_http_exception)  # type: ignore[arg-type]
	app.add_exception_handler(RequestValidationError, handle_validation_exception)  # type: ignore[arg-type]
	app.add_exception_handler(Exception, handle_generic_exception)  # type: ignore[arg-type]

	# CORS for local web dev (Vite default port 5173)
	origins = [o.strip() for o in settings.cors_origins.split(',') if o.strip()]
	app.add_middleware(
		CORSMiddleware,
		allow_origins=origins,
		allow_credentials=True,
		allow_methods=["*"],
		allow_headers=["*"],
	)

	# Request ID tracing for all requests
	app.add_middleware(RequestIDMiddleware)

	# CSRF protection for state-changing requests
	app.add_middleware(CSRFMiddleware)

	# HTTPS enforcement in production
	if settings.app_env == "prod":
		app.add_middleware(HTTPSRedirectMiddleware)

	# Health endpoint with optional DB check
	@app.get("/health")
	def health(check: str = Query(None, description="Check type: 'db' for database verification")):
		response = {"status": "ok"}

		# Optional database connection check
		if check == "db":
			try:
				with engine.connect() as conn:
					conn.execute(text("SELECT 1"))
				response["database"] = "connected"
			except Exception as e:
				response["status"] = "degraded"
				response["database"] = "unreachable"
				response["error"] = str(e)
				return JSONResponse(status_code=503, content=response)

		return response

	# DB init - controlled by settings
	if settings.reset_db_on_startup:
		Base.metadata.drop_all(bind=engine)
		Base.metadata.create_all(bind=engine)

	# Static files for local uploads
	if settings.storage_backend == "local":
		os.makedirs(settings.storage_local_dir, exist_ok=True)
		# Serve local uploads under /static/uploads
		uploads_mount = settings.storage_local_dir
		app.mount("/static/uploads", StaticFiles(directory=uploads_mount), name="uploads")

	# Routers - v1 API
	app.include_router(auth.router, prefix="/v1/auth", tags=["v1", "auth"])
	app.include_router(users.router, prefix="/v1/users", tags=["v1", "users"])
	app.include_router(availability.router, prefix="/v1/availability", tags=["v1", "availability"])
	app.include_router(notifications.router, prefix="/v1/notifications", tags=["v1", "notifications"])
	app.include_router(dogs.router, prefix="/v1/dogs", tags=["v1", "dogs"])
	app.include_router(messages.router, prefix="/v1/messages", tags=["v1", "messages"])
	app.include_router(websocket.router, prefix="/v1", tags=["v1", "websocket"])

	# Legacy routes (without /v1 prefix) - redirect to v1 for backward compatibility
	app.include_router(auth.router, prefix="/auth", tags=["legacy", "auth"], deprecated=True)
	app.include_router(users.router, prefix="/users", tags=["legacy", "users"], deprecated=True)
	app.include_router(availability.router, prefix="/availability", tags=["legacy", "availability"], deprecated=True)
	app.include_router(notifications.router, prefix="/notifications", tags=["legacy", "notifications"], deprecated=True)
	app.include_router(dogs.router, prefix="/dogs", tags=["legacy", "dogs"], deprecated=True)
	app.include_router(messages.router, prefix="/messages", tags=["legacy", "messages"], deprecated=True)
	app.include_router(websocket.router, tags=["legacy", "websocket"], deprecated=True)

	# Prometheus metrics instrumentation
	Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
	logger.info("prometheus_metrics_enabled", endpoint="/metrics")

	# Graceful shutdown handler (for Lambda and container interruptions)
	def handle_shutdown(sig, frame):
		"""Graceful shutdown handler for SIGTERM/SIGINT.

		Called when:
		- Lambda is being shut down
		- ECS/Fargate task is stopping
		- Spot instance is being interrupted
		"""
		logger.info("shutdown_initiated", signal=sig)
		try:
			# Close database connections
			engine.dispose()
			logger.info("database_connections_closed")
		except Exception as e:
			logger.error("shutdown_error", error=str(e))
		sys.exit(0)

	# Register shutdown handlers (not needed for Lambda, but safe to register)
	signal.signal(signal.SIGTERM, handle_shutdown)
	signal.signal(signal.SIGINT, handle_shutdown)

	return app


app = create_app()

