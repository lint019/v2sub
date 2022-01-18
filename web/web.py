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

url_map={
    'https://www.youtube.com':['*googlevideo.com*','*googlevideo*','*google*','*youtube.com*'],        
    'https://www.github.com':['*github*','*'],
    'https://www.twitter.com':['*twimg*','*t.co*','*twitter*'],
    'https://www.gettr.com':['*gettr.com*'],
    'https://www.gtv.org':['*gtv.org*'],
    'https://www.xvideos.com':['*xvideos.com*'],
    'https://www.pornhub.com':['*pornhub.com*'],
}


MSG_INVALID_REQUEST = {'status': 'error', 'errmsg': 'invalid request'}

pac_script0 = (
'function FindProxyForURL(url, host)'
'{  '
'   '
'   url = url.toLowerCase();    '
'   host = host.toLowerCase();  '
'   '
'   var hostOrDomainIs = function(host, val) {  '
'      return (host === val) || dnsDomainIs(host, "." + val);   '
'   };  '
'   '
'   var hostIs = function(host, val) {  '
'	  return (host === val);    '
'   };  '
'       '
'       '
'   if (isPlainHostName(host))  '
'   {   '
'      return "DIRECT"; '
'   }   '
'   '
'   if (isResolvable(host)) '
'   {   '
'      var hostIP = dnsResolve(host);   '
'      if (!shExpMatch(hostIP, "*:*"))  '
'      {    '
'        /* Don"t proxy non-routable addresses (RFC 3330) */    '
'        if (isInNet(hostIP, "0.0.0.0", "255.0.0.0") || '
'        isInNet(hostIP, "10.0.0.0", "255.0.0.0") ||    '
'        isInNet(hostIP, "127.0.0.0", "255.0.0.0") ||   '
'        isInNet(hostIP, "169.254.0.0", "255.255.0.0") ||   '
'        isInNet(hostIP, "172.16.0.0", "255.240.0.0") ||    '
'        isInNet(hostIP, "192.0.2.0", "255.255.255.0") ||   '
'        isInNet(hostIP, "192.88.99.0", "255.255.255.0") || '
'        isInNet(hostIP, "192.168.0.0", "255.255.0.0") ||   '
'        isInNet(hostIP, "198.18.0.0", "255.254.0.0") ||    '
'        isInNet(hostIP, "224.0.0.0", "240.0.0.0") ||   '
'        isInNet(hostIP, "240.0.0.0", "240.0.0.0")) '
'        {  '
'           return "DIRECT";    '
'        }  '
'      }    '
'   }   \r\n    '
'	if (    '
'	(shExpMatch(host, "*facebook.com*")) ||  '
'	(shExpMatch(host, "*whatsapp.com*")) ||  '
'	(shExpMatch(host, "*instagram.com*")) || '
'	(shExpMatch(host, "*telegram.org*")) ||  '
'	(shExpMatch(host, "*line.me*")) ||   '
'	(shExpMatch(host, "*twitter.com*")) ||   '
'	(shExpMatch(host, "*youtube.com*")) ||   '
'	(shExpMatch(host, "*netflix.com*")) ||   '
'	(shExpMatch(host, "*hbo.com*")) ||   '
'	(shExpMatch(host, "*gettr.com*")) ||   '
'	(shExpMatch(host, "*gtv.org*")) ||   '
'	(shExpMatch(host, "*xvideos.com*")) ||   '
'	(shExpMatch(host, "*pornhub.com*")) ||   '
'	(shExpMatch(host, "*gnews.org*")) ||   '
'	(shExpMatch(host, "*google.com*")) ||   '
'	(shExpMatch(host, "*google*")) ||   '
'	(shExpMatch(host, "*twimg.com*")) ||   '
'	(shExpMatch(host, "*t.co*")) ||   '
'	(shExpMatch(host, "*googlevideo.com*")) ||   '
'	(shExpMatch(host, "*cp-pv.dflzm.com*"))  '
'   )   '
'   {   '
'      return "%s";    '
'   }   '
'   '
'       '
'   return "DIRECT";    '
'}  '
)

pac_script = (
'function FindProxyForURL(url, host)'
'{  '
'   '
'   url = url.toLowerCase();    '
'   host = host.toLowerCase();  '
'   '
'   var hostOrDomainIs = function(host, val) {  '
'      return (host === val) || dnsDomainIs(host, "." + val);   '
'   };  '
'   '
'   var hostIs = function(host, val) {  '
'	  return (host === val);    '
'   };  '
'       '
'       '
'   if (isPlainHostName(host))  '
'   {   '
'      return "DIRECT"; '
'   }   '
'   '
'   if (isResolvable(host)) '
'   {   '
'      var hostIP = dnsResolve(host);   '
'      if (!shExpMatch(hostIP, "*:*"))  '
'      {    '
'        /* Don"t proxy non-routable addresses (RFC 3330) */    '
'        if (isInNet(hostIP, "0.0.0.0", "255.0.0.0") || '
'        isInNet(hostIP, "10.0.0.0", "255.0.0.0") ||    '
'        isInNet(hostIP, "127.0.0.0", "255.0.0.0") ||   '
'        isInNet(hostIP, "169.254.0.0", "255.255.0.0") ||   '
'        isInNet(hostIP, "172.16.0.0", "255.240.0.0") ||    '
'        isInNet(hostIP, "192.0.2.0", "255.255.255.0") ||   '
'        isInNet(hostIP, "192.88.99.0", "255.255.255.0") || '
'        isInNet(hostIP, "192.168.0.0", "255.255.0.0") ||   '
'        isInNet(hostIP, "198.18.0.0", "255.254.0.0") ||    '
'        isInNet(hostIP, "224.0.0.0", "240.0.0.0") ||   '
'        isInNet(hostIP, "240.0.0.0", "240.0.0.0")) '
'        {  '
'           return "DIRECT";    '
'        }  '
'      }    '
'   }   \r\n    '
'    %s         '
'   '
'       '
'   return "DIRECT";    '
'}  '
)



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
    MSG.put('pac', {})
    # host = request.host_addr
    host = request.host.split(':')[0]
    list = MSG.get()
    proxy_string = ''

    url_function = """\r\n	if (    
    	%s
       )   
       {   
          return "%s";    
       }   """
            # sample:
    # [{'url':'youtube.com','list':[{'port':20083,'speed':222},{'port':20081,'speed':222}]}]
    

    # print("This is an example wsgi app served from {} to {}".format(request.remote_addr, request.remote_addr))

    # for item in list:
    #     proxy_string =proxy_string +"HTTPS %s:%d;PROXY %s:%d;SOCKS %s:%d; "%(host,item,host,item,host,item)

    function_scripts = ''
    for item in list:
        proxy_string =''
        for it in item['list']:
            proxy_string =proxy_string +"HTTPS %s:%d;PROXY %s:%d;SOCKS %s:%d; "%(host,it['port'],host,it['port'],host,it['port'])

        filter_list=url_map[item['url']] 
        script_str = ''
        for it in filter_list:
            script_str=script_str+'(shExpMatch(host, "%s"))||'%it
        script_str=script_str+'false'    
        function_scripts = function_scripts + url_function%(script_str,proxy_string)

    rsp = make_response(pac_script%(function_scripts),200)
    # rsp = make_response(pac_script%(proxy_string),200)
    rsp.headers['Content-Type']= 'text;'
    # rsp.headers['Content-Type']= 'application/x-ns-proxy-autoconfig;'
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


