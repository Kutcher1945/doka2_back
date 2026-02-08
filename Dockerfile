FROM python:3.8
ENV PYTHONUNBUFFERED=1
WORKDIR /code
COPY requirements.txt /code/
RUN pip3 install -r requirements.txt
COPY . /code/

ENV DJANGO_SETTINGS_MODULE=core.settings
ENV DJANGO_ALLOW_ASYNC_UNSAFE=true
ENV PYTHONUNBUFFERED=1
COPY ./setup_gunicorn.sh /setup_gunicorn.sh
RUN chmod +x /setup_gunicorn.sh

# CMD ["/setup_gunicorn.sh"]