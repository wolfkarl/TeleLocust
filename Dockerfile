FROM locustio/locust

WORKDIR /app

# RUN ["which", "python"]

COPY Pipfile Pipfile
COPY Pipfile.lock Pipfile.lock

RUN pip install pipenv && pipenv install --deploy 

ADD app.py app.py
ADD locustfile.py locustfile.py

ENTRYPOINT ["python", "app.py"]

# ENTRYPOINT ["/bin/bash"]
# CMD ["-c", "while true; do sleep 1; done"]
