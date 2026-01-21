from flask import Flask
import time
import os
import subprocess

HTTP_PORT = 5123
SUT = "http://localhost:5123"
DATA_PATH = "./data/"

logger = __import__('logging').getLogger(__name__)

app = Flask(__name__)
counter = 0
runs = {}
processes = {}


@app.route('/')
def hello():
    return 'Hello, World!'

@app.route('/runs/start', methods=['POST'])
def start():
    token = str(time.time())
    runs[token] = {'status': 'started'}
    print(f"Starting run {token}")
    runs[token]['dir'] = f"{DATA_PATH}/{token}"
    os.makedirs(runs[token]['dir'], exist_ok=False)
    processes[token] = subprocess.Popen(
        [
            'locust',
            '-f', 'locustfile.py',
            '--headless',
            '-u', '10',
            '-r', '2',
            '--run-time', '5s',
            '--host', SUT,
            '--csv', f"{runs[token]['dir']}/loadtest", '--csv-full-history'
        ])
    return {'token': token}

@app.route('/runs/<token>', methods=['GET'])
def status(token):  
    if token not in runs:
        return {'error': 'Token not found'}, 404

    proc = processes[token]
    retcode = proc.poll()
    if retcode is None:
        runs[token]['status'] = 'running'
    else:
        runs[token]['status'] = 'finished'



    return runs[token]

@app.route('/quick')
def quick_load_test():
    logger.info("Starting load test...")
    run = subprocess.run(
        [
            'locust',
            '-f', 'locustfile.py',
            '--headless',
            '-u', '10',
            '-r', '2',
            '--run-time', '5s',
            '--host', SUT,
            '--csv', 'test.csv', '--csv-full-history'
        ],
        capture_output=True,
        text=True
    )
    logger.info("Load test completed.")
    return "<pre>" + str(run)


@app.route('/up')
def up():
    global counter
    counter += 1
    print(counter)
    return {"counter": counter}


if __name__ == '__main__':
    app.run(debug=True, port=HTTP_PORT)
