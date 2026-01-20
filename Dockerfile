FROM locustio/locust
ENTRYPOINT ["/bin/bash"]
CMD ["-c", "while true; do sleep 1; done"]
