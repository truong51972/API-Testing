# Django Development Docker Setup

This guide explains how to run your Django application in development mode using Docker, which replaces your usual command `python manage.py runserver localhost:8001`.

## What's New

- **Development-focused Docker setup** that runs Django's development server instead of Gunicorn
- **Port 8001** as requested (instead of the production port 8000)
- **Hot reloading** enabled for development
- **Volume mounting** for live code changes during development
- **PostgreSQL database** included for local development

## Quick Start

### 1. Set up environment variables

Copy the example environment file and modify as needed:

```bash
cp .env.example .env
```

Edit `.env` with your preferred settings:
```env
POSTGRES_DB=frontend
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
DEBUG=True
SECRET_KEY=your-secret-key-here
```

### 2. Build and run with Docker Compose

```bash
# Build the development Docker image
docker-compose -f docker-compose.yml build

# Run the complete development stack (Django + PostgreSQL)
docker-compose -f docker-compose.yml up

# Or run in detached mode (background)
docker-compose -f docker-compose.yml up -d
```

### 3. Access your application

Your Django application will be available at:
- **Local**: http://localhost:8001
- **Development server**: The Django development server will restart automatically when you make code changes

## Available Commands

### Start development environment
```bash
docker-compose -f docker-compose.yml up
```

### Stop development environment
```bash
docker-compose -f docker-compose.yml down
```

### View logs
```bash
# All services
docker-compose -f docker-compose.yml logs

# Specific service only
docker-compose -f docker-compose.yml logs django-dev
```

### Run Django management commands
```bash
# Make migrations
docker-compose -f docker-compose.yml exec django-dev python manage.py makemigrations

# Run migrations
docker-compose -f docker-compose.yml exec django-dev python manage.py migrate

# Create superuser
docker-compose -f docker-compose.yml exec django-dev python manage.py createsuperuser

# Collect static files
docker-compose -f docker-compose.yml exec django-dev python manage.py collectstatic
```

### Access Django shell
```bash
docker-compose -f docker-compose.yml exec django-dev python manage.py shell
```

## Development Workflow

1. **Make code changes** in your local files (they're mounted as volumes)
2. **Django development server automatically restarts** when files change
3. **Refresh your browser** to see changes at http://localhost:8001
4. **Database persists** between container restarts

## File Structure

- `docker-compose.yml` - Development Docker Compose configuration
- `Dockerfile` - Development-optimized Dockerfile
- `.env.example` - Environment variables template
- `frontend/` - Your Django project directory (mounted as volume)

## Database

PostgreSQL runs in a separate container and persists data in a Docker volume. The database will be available at:
- **Host**: db (from django-dev container)
- **Port**: 5432

## Troubleshooting

### Port already in use
If port 8001 is already in use:
```bash
# Stop other services using the port
# Or modify the port mapping in docker-compose.yml
```

### Reset database
```bash
# Remove the postgres_data volume
docker-compose -f docker-compose.yml down -v
```

### View container status
```bash
docker-compose -f docker-compose.yml ps
```

## Production vs Development

- **Development**: Uses Django's built-in server with hot reloading
- **Production**: Uses Gunicorn with multiple workers (existing setup)

For production deployment, use the original `docker-compose.yml` and `Dockerfile`.