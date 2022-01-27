import time
import datetime
import requests
import os
import json
import subprocess
import logging
import queue
import urllib

haproxy_conf='''
global
    log {}/ha local0
    log {}/ha local0 notice
    user root
    group root
    daemon

defaults
    log global
    mode tcp
    timeout connect 5s
    timeout client 5s
    timeout server 5s
    option      dontlognull
    option      redispatch
    option      httplog
    retries     3

listen status
  bind *:{}
  mode  http
  stats refresh 10s
  stats uri /status
  stats realm Haproxy  
  stats auth admin:admin
  stats hide-version
  stats admin if TRUE

frontend http-web
    mode tcp
    bind *:{}
    default_backend v2-out

backend v2-out
    mode tcp
    balance roundrobin    
    {}
'''


logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)



class HaProxy(object):
    def __init__(self, args):  
        self.args = args
        self.p = None
        

    def run_haproxy(self,base,service_count):
        self.shutdown()
        root_dir = self.args.root_dir

        log_path = os.path.join(root_dir,  "log")
        if not os.path.exists(log_path):
            os.makedirs(log_path)

        tmp = os.path.join(
            root_dir, "config_haproxy.conf" 
        )
        serv = "server  {}    127.0.0.1:{}  check\r\n"
        servs=''
        for index in range(service_count):
            servs=servs+serv.format("server_"+str(base+index),base+index)

        content = haproxy_conf.format(log_path,log_path,30002,30001,servs)

        

        logger.debug(json.dumps(content))
        json.dump(content, open(tmp, "w"), indent=2)
        logger.debug("run haproxy: %s -f %s" % (self.args.haproxy_exec_path, tmp))        
        try:
            f = open(tmp, "w")
            f.write(content)
            f.close()
            self.p = subprocess.Popen([self.args.haproxy_exec_path, "-f", tmp],stdout=subprocess.PIPE,stderr=subprocess.PIPE)        
            output, err  = self.p.communicate(timeout=5)
            logger.debug("read err %s" % (err))
        except Exception as e:        
            logger.debug("execute err %s" % (e))
            pass
        
        logger.debug("haproxy RUN OK" )

    
    def shutdown(self):
        if self.p is not None:
            self.p.terminate()
            self.p.wait()
            logger.debug("haproxy has terminated.")

