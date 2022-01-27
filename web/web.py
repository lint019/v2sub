#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from logging import Logger
import socket
from flask import Flask
from flask import render_template, send_file,make_response
from flask import request
# from multiprocessing import Process
from threading import Thread as Process
from queue import Queue

from copy import deepcopy


MSG = None

app = Flask(__name__)

MSG_INVALID_REQUEST = {'status': 'error', 'errmsg': 'invalid request'}



@app.route('/mobile')
def mobile():
    return render_template('mobile.html')
    
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/task', methods=['POST'])
def add_task():
    payload = request.get_json()

    MSG.put('create', payload)
    return json.dumps(MSG.get())


@app.route('/task/list', methods=['GET'])
def list_task():
    payload = {}
    exerpt = request.args.get('exerpt', None)
    if exerpt is None:
        payload['exerpt'] = False
    else:
        payload['exerpt'] = True

    payload['state'] = request.args.get('state', 'all')

    MSG.put('list', payload)
    return json.dumps(MSG.get())


@app.route('/task/state_counter', methods=['GET'])
def list_state():
    MSG.put('state', None)
    return json.dumps(MSG.get())


@app.route('/task/batch/<action>', methods=['POST'])
def task_batch(action):
    payload={'act': action, 'detail': request.get_json()}

    MSG.put('batch', payload)
    return json.dumps(MSG.get())

@app.route('/task/tid/<tid>', methods=['DELETE'])
def delete_task(tid):
    del_flag = request.args.get('del_file', False)
    payload = {}
    payload['tid'] = tid
    payload['del_file'] = False if del_flag is False else True

    MSG.put('delete', payload)
    return json.dumps(MSG.get())


@app.route('/task/tid/<tid>', methods=['PUT'])
def manipulate_task(tid):
    payload = {}
    payload['tid'] = tid

    act = request.args.get('act', None)
    if act == 'pause':
        payload['act'] = 'pause'
    elif act == 'resume':
        payload['act'] = 'resume'
    else:
        return json.dumps(MSG_INVALID_REQUEST)

    MSG.put('manipulate', payload)
    return json.dumps(MSG.get())


@app.route('/task/tid/<tid>/status', methods=['GET'])
def query_task(tid):
    payload = {}
    payload['tid'] = tid

    exerpt = request.args.get('exerpt', None)
    if exerpt is None:
        payload['exerpt'] = False
    else:
        payload['exerpt'] = True

    MSG.put('query', payload)
    p = MSG.get()
    return json.dumps(p)

@app.route('/task/tid/<tid>/qrcode', methods=['GET'])
def qrcode_task(tid):
    payload = {}
    payload['tid'] = tid

    exerpt = request.args.get('exerpt', None)
    if exerpt is None:
        payload['exerpt'] = False
    else:
        payload['exerpt'] = True

    MSG.put('qrcode', payload)
    filename = MSG.get()
    return send_file(filename, mimetype='image/gif')


@app.route('/default.pac', methods=['GET', 'POST'])
def pac():

    # host = request.host_addr
    host = request.host.split(':')[0]
    payload = {}
    if request.method == 'POST':
        payload['act'] = 'update'
        payload['param'] = request.get_json()
    else:
        payload['act'] = 'get'
        payload['param'] = host
    MSG.put('pac', payload)
    rsp = make_response(MSG.get())
    # rsp = make_response(pac_script%(proxy_string),200)
    rsp.headers['Content-Type']= 'text;'

    return rsp

    


@app.route('/config', methods=['GET', 'POST'])
def get_config():
    payload = {}
    if request.method == 'POST':
        payload['act'] = 'update'
        payload['param'] = request.get_json()
    else:
        payload['act'] = 'get'

    MSG.put('config', payload)
    return json.dumps(MSG.get())

@app.route('/start_all', methods=['GET', 'POST'])
def start_all():
    payload = {}
    if request.method == 'POST':
        payload['act'] = 'update'
        payload['param'] = request.get_json()
    else:
        payload['act'] = 'get'

    MSG.put('start_all', payload)
    return json.dumps(MSG.get())

@app.route('/subscribe', methods=['GET', 'POST'])
def subscrible():
    payload = {}
    if request.method == 'POST':
        payload['act'] = 'subscribe'
        payload['param'] = request.get_json()
    else:
        payload['act'] = 'get'

    MSG.put('subscribe', payload)
    return json.dumps(MSG.get())

@app.route('/offer', methods=['GET', 'POST'])
def offer():
    payload = {}
    if request.method == 'POST':
        payload['act'] = 'offer'
        payload['param'] = request.get_json()
    else:
        payload['act'] = 'get'

    MSG.put('offer', payload)
    return json.dumps(MSG.get())

@app.route('/reboot', methods=['GET', 'POST'])
def reboot():
    payload = {}
    if request.method == 'POST':
        payload['act'] = 'offer'
        payload['param'] = request.get_json()
    else:
        payload['act'] = 'get'

    MSG.put('reboot', payload)
    return json.dumps(MSG.get())


###
# test cases
###
@app.route('/test/<case>')
def test(case):
    return render_template('test/{}.html'.format(case))


class WebServer(Process):
    def __init__(self, msg_cli, host, port):
        super(WebServer, self).__init__()

        self.msg_cli = msg_cli

        self.host = host
        self.port = port

    def run(self):
        global MSG
        MSG = self.msg_cli
        app.run(host=self.host, port=int(self.port), use_reloader=False)


