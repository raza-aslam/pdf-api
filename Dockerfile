FROM python:3.12

LABEL maintainer="raza-aslam"

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install poetry

COPY . /app/

RUN poetry config virtualenvs.create false

RUN poetry install

EXPOSE 8001

CMD ["poetry", "run", "uvicorn", "api_routes.main:app", "--host", "0.0.0.0", "--reload"]