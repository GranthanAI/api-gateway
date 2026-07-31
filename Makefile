.PHONY: help install run clean token get-otp

help:
	@echo "API Gateway Makefile targets:"
	@echo "  install   - Install python dependencies using uv"
	@echo "  run       - Launch the FastAPI API Gateway local server"
	@echo "  token     - Generate a valid JWT token for a test user"
	@echo "  get-otp   - Get active verification OTP for an email (e.g. make get-otp EMAIL=user@example.com)"
	@echo "  clean     - Clean temporary python files and virtualenv"

install:
	uv sync

run:
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

token:
	@uv run python -c "import jwt, datetime; print(jwt.encode({'sub': '11111111-1111-1111-1111-111111111111', 'email': 'testuser@example.com', 'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)}, 'supersecretjwtkeyforauthservicelocaldvelopment12345', algorithm='HS256'))"

get-otp:
	uv run --project ../auth-service python ../auth-service/get_otp.py --email $(or $(EMAIL),testuser@example.com)

clean:
	rm -rf .venv __pycache__


