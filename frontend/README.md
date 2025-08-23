# APIT (Agent Programmatic Intergration Testing) (WIP)
Table of contents

1. [Project Overview](#project-overview)
2. [Project Progress](#project-progress)
3. [Usage](#usage)
## Project Overview



## Project Progress
| Objective    | Progress |
| -------- | ------- |
| Initialize Django Project | Finished :white_check_mark:    |
| Prepare Docker Configuration | Finished :white_check_mark:     |
| User Login, Logout, Registration| Finished :white_check_mark:|
| Design Database Schema | In Progress :wrench:    | $420    |
| User Info Modification| Not Started :x:|
| Test Case Views| Not Started :x:|

## Usage
### Local Machine
#### 1. Create Virtual Environment:

Windows
```bat
python venv venv
venv\Scripts\activate
```
Linux
```bat
python3 -m venv venv
source venv/bin/activate
```

#### 2. Install Dependencies

Windows
```bat
pip install -r requirements.txt
```
Linux
```
pip3 install -r requirements.txt
```

#### 3. Create .env File
```
# Environment Variables
PRODUCTION_ENVIRONMENT=False

# Django Settings
DEBUG=True
DJANGO_SECRET_KEY=YOUR_DJANGO_SECRET_KEY
DJANGO_ALLOWED_HOSTS=localhost
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:8001

# Database Settings
DATABASE_ENGINE=postgresql_psycopg2
DATABASE_NAME=YOUR_DATABASE_NAME
DATABASE_USERNAME=YOUR_DATABASE_USERNAME
DATABASE_PASSWORD=YOUR_DATABASE_PASSWORD
DATABASE_PORT=YOUR_DATABASE_PORT

# Postgres Settings
POSTGRES_DB=YOUR_DATABASE_NAME
POSTGRES_USER=YOUR_DATABASE_USERNAME
POSTGRES_PASSWORD=YOUR_DATABASE_PASSWORD
```

#### 4. Make Database Migration
##### makemigrations
Windows
```bat
python manage.py makemigrations
```
Linux
```bat
python3 manage.py makemigrations
```
##### migrate
Windows
```bat
python manage.py migrate
```
Linux
```bat
python3 manage.py migrate
```

#### 5. Run Serverpython manage.py runserver
Windows
```bat
python manage.py runserver localhost:8001
```
Linux
```bat
python3 manage.py runserver localhost:8001
```

### Production Machine
#### 1. Create .env File
```
# Environment Variables
PRODUCTION_ENVIRONMENT=True

# Django Settings
DEBUG=False
DJANGO_SECRET_KEY=YOUR_DJANGO_SECRET_KEY
DJANGO_ALLOWED_HOSTS=localhost
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:8001

# Database Settings
DATABASE_ENGINE=postgresql_psycopg2
DATABASE_NAME=YOUR_DATABASE_NAME
DATABASE_USERNAME=YOUR_DATABASE_USERNAME
DATABASE_PASSWORD=YOUR_DATABASE_PASSWORD
DATABASE_PORT=YOUR_DATABASE_PORT

# Postgres Settings
POSTGRES_DB=YOUR_DATABASE_NAME
POSTGRES_USER=YOUR_DATABASE_USERNAME
POSTGRES_PASSWORD=YOUR_DATABASE_PASSWORD
```

#### 2. Docker Compose
```bat
docker-compose up -d --build
```

#### 3. Make Database Migration
Remember to shut down containers before making migrations.
```bat
docker-compose down --rmi all
```
##### makemigrations
```bat
docker-compose exec django-web python manage.py makemigrations
```
##### migrate
```bat
docker-compose exec django-web python manage.py migrate
```

#### 4. Run Server
Simply run `docker-compose up -d --build` and access the web using https://localhost:8001.


