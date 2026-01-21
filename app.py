import logging
"""
Telelocust - Flask-based load testing orchestration application.
This module provides a REST API for managing and executing Locust load tests.
It allows clients to start load testing runs, monitor their status, and download results.

Configuration:
    HTTP_PORT (int): Port on which the Flask application runs (5123)
    SUT (str): System Under Test URL (http://localhost:5123)
    DATA_PATH (str): Directory path for storing test data and results (./data/)
Key Components:
    - /runs/start (POST): Initiates a new load test with specified parameters
    - /runs/<token> (GET): Retrieves the status and results of a load test run
    - /runs/<token>/download (GET): Downloads test results as a ZIP file
    - / (GET): Health check endpoint
    - /up (GET): Simple counter endpoint for monitoring
The application manages:
    - runs: Dictionary tracking the status of each load test execution
    - processes: Dictionary maintaining subprocess references for active tests
    - parameters: Configuration parameters for load tests (users, spawn rate, duration, etc.)
Locustfile handling:
    - Reads locustfile.py as base64-encoded data
    - Allows clients to provide custom locustfiles via JSON payload
    - Decodes and writes locustfiles to disk before execution
Test execution:
    - Spawns Locust subprocesses with CLI parameters
    - Generates CSV, JSON, and log outputs for each test run
    - Provides real-time status monitoring and result retrieval
"""

import time
import json
import os
import subprocess
from flask import send_file
import zipfile
import io

from flask import Flask
from flask import request

HTTP_PORT = int(os.environ.get('TELELOCUST_HTTP_PORT', 5123))
SUT = "http://localhost:5123"
DATA_PATH = "./data/"

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def read_locustfile_as_base64(filepath='locustfile.py'):
    with open(filepath, 'rb') as f:
        return __import__('base64').b64encode(f.read()).decode('utf-8') 
    

parameters = {
    'host': SUT,
    'users': 10,
    'spawn_rate': 2,
    'run_time': '5s',
    'locustfile_base64':  read_locustfile_as_base64(),
}


app = Flask(__name__)
counter = 0
runs = {}
processes = {}


@app.route('/')
def hello():
    return 'Hello, World!'

@app.route('/runs/start', methods=['POST'])
def start():

    data = request.get_json() or {}
    parameters.update(data)

    token = str(time.time())
    runs[token] = {'status': 'started'}
    print(f"Starting run {token}")
    os.makedirs(data_dir(token), exist_ok=False)
    
    with open(data_dir(token) + '/locustfile.py', 'wb') as f:
        f.write(__import__('base64').b64decode(parameters['locustfile_base64'].encode('utf-8')))    

    processes[token] = subprocess.Popen(
        [
            'locust',
            '-f', data_dir(token) + '/locustfile.py',
            '--headless',
            '-u', str(parameters['users']),
            '-r', str(parameters['spawn_rate']),
            '--run-time', parameters['run_time'],
            '--host', parameters['host'],
            '--csv', f"{data_dir(token)}/loadtest", '--csv-full-history',
            '--logfile', f"{data_dir(token)}/locust.log",
            '--json-file', f"{data_dir(token)}/result",
            # '--json'
        ],
        # stdout=subprocess.PIPE
        )
    return {'token': token}, 201, {'Location': f'/runs/{token}'}

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
        runs[token]['exit_code'] = retcode,
        runs[token]['finished_at'] = time.time(),
        # Read JSON result file
        with open(f"{data_dir(token)}/result.json", 'r') as f:
            runs[token]['result'] = json.load(f)    

    return runs[token]  

@app.route('/runs/<token>/download', methods=['GET'])
def download(token):
    
    if token not in runs:
        return {'error': 'Token not found'}, 404
    
    run_dir = data_dir(token)
    if not os.path.exists(run_dir):
        return {'error': 'Run directory not found'}, 404
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(run_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, run_dir)
                zip_file.write(file_path, arcname)
    
    zip_buffer.seek(0)
    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'run_{token}.zip'
    )


@app.route('/up')
def up():
    global counter
    counter += 1
    print(counter)
    return {"counter": counter}


def data_dir(token):
    return f"{DATA_PATH}/{token}"


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=HTTP_PORT)
