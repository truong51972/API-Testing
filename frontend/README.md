# APIT (Agent Programmatic Intergration Testing) (WIP)
Table of contents

1. [Project Overview](#project-overview)
2. [Project Progress](#project-progress)
3. [Usage](#usage)
4. [Miscellaneous](#miscellaneous)


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
#### 1. Create Virtual Environment (for pip method):

Windows
```bat
python venv .venv
.venv\Scripts\activate
```
Linux
```bat
python3 -m venv .venv
source .venv/bin/activate
```

#### 2. Install Dependencies
##### 2.1 Using uv (Recommended method)
With the below command line, uv will automatically create a virtual environment for you and install the dependencies. See more [here](https://github.com/astral-sh/uv) or for my brief tutorial [here](#how-to-use-uv-for-better-dependency-management).
```bat
uv sync --locked
```
##### 2.2 Using pip (Old method)
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
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:8000

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
python manage.py runserver
```
Linux
```bat
python3 manage.py runserver
```

### Production Machine
#### 1. Create .env File
```
# Environment Variables
PRODUCTION_ENVIRONMENT=True

# Django Settings
DEBUG=False
DJANGO_SECRET_KEY=YOUR_DJANGO_SECRET_KEY
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:8000

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
docker compose up -d --build
```

#### 3. Making Database Migration

##### makemigrations
```bat
docker compose exec django-web python manage.py makemigrations
```
##### migrate
```bat
docker compose exec django-web python manage.py migrate
```


#### 4. Run Server
Simply run `docker compose up -d --build` and access the web using https://localhost:8000 or https://127.0.0.1:8000.

## Miscellaneous
### How to use uv for better dependency management
#### Installation
See more [here](https://docs.astral.sh/uv/getting-started/installation/).
Linux
```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```
Window
```bat
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
#### 

