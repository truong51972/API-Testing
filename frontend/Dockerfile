# Stage 1: Build stage with uv
# This stage installs dependencies into a virtual environment.
FROM python:3.11-slim-bookworm AS builder

# Copy the uv binary from the official image
COPY --from=ghcr.io/astral-sh/uv@sha256:2381d6aa60c326b71fd40023f921a0a3b8f91b14d5db6b90402e65a635053709 /uv /uvx /bin/

# Set the working directory
WORKDIR /app

# Set environment variables to optimize Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create a virtual environment in /app/.venv
# This makes it easy to copy the entire environment later
RUN uv venv

# Copy dependency definition files
COPY pyproject.toml uv.lock /app/

# Install dependencies into the virtual environment using the lockfile
# uv automatically detects and uses the .venv directory
RUN uv sync --locked

# ---

# Stage 2: Production stage
# This stage creates the final, lean image.
FROM python:3.11-slim-bookworm

# Create a non-root user and group for security
RUN addgroup --system appgroup && adduser --system --group appuser

# Set the working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy the virtual environment from the builder stage
COPY --from=builder /app/.venv ./.venv

# Prepend the virtual environment's bin directory to the PATH.
# This is the key fix that allows the container to find "gunicorn".
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code into the container
# The --chown flag ensures the appuser owns these files
COPY --chown=appuser:appgroup . .

# Switch to the non-root user
USER appuser

# Expose the port the app runs on
EXPOSE 8000

# The following lines assume you have an entrypoint.sh script.
# If your entrypoint.sh script runs the gunicorn command,
# you should change the CMD line to just: CMD ["/app/entrypoint.sh"]
RUN chmod +x /app/entrypoint.sh

# Start the application using Gunicorn.
# This now works because gunicorn is found in the updated PATH.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "APIT.wsgi:application"]