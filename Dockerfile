FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /opt/app

RUN addgroup --system app \
    && adduser --system --ingroup app app

COPY requirements.txt ./

RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY src ./src

RUN chown -R app:app /opt/app

USER app

EXPOSE 8000

CMD ["python", "src/main.py"]