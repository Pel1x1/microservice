FROM python:3.12-slim

WORKDIR /code

COPY ./requirements.txt /code/
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app /code/app

# PORT задаёт среда запуска (Serverless Containers передаёт 8080), по умолчанию 80
ENV PORT=80
EXPOSE 80
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --no-access-log"]
