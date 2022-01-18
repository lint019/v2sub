import time
import datetime
import requests
import os
import json
import subprocess
import logging
import queue
import urllib

from concurrent.futures import (
    ThreadPoolExecutor,
    wait,
    ALL_COMPLETED,
    FIRST_COMPLETED,
    as_completed,
)

from requests.api import request

urls = [
        'https://www.youtube.com/'        
        ]

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


class Testing(object):
    def __init__(self ,args):        
        self.args = args

    def is_connect(self,url):
        ret = -1
        try:
            proxies = {
                "http": "http://127.0.0.1:%d" % self.args.port,
                "https": "http://127.0.0.1:%d" % self.args.port,
                "socks5": "http://127.0.0.1:%d" % self.args.port,
            }
            output = ("start connect [%s] used :[%s] node,proxy:[http://127.0.0.1:%d]-timeout[%d] "%(url,self.args.name,self.args.port,self.args.connect_timeout))
            # print(output)
            logger.debug(output)
            resp = requests.get(url,proxies=proxies,timeout=self.args.connect_timeout)      
            if resp.status_code == 200:
                ret = resp.elapsed.microseconds/1000
                print ('[%d][%s] [%s] OK!'%(ret,self.args.name,url))                
            else:
                print('[%s] [%s]Boo!'%(url,self.args.name))
            # req = urllib.request.Request(url)
            # proxy_host = "http://127.0.0.1:%d" % self.args.port
            # req.set_proxy(proxy_host, 'http')            
            # response = urllib.request.urlopen(req,timeout=self.args.connect_timeout)
            # data = response.read().decode('utf-8')
            # ret = True
        except KeyboardInterrupt:
            pass
        except Exception as e:
            logger.debug('[%s] error [%s]!'%(self.args.name,e))            
            # print ('[%s] - [%s] Fail!'%(self.args.name,url))
            pass
        
        return ret

    def do_action(self, queue):
        while  not queue.empty():
            url = queue.get()
            # print ('test connect[%s] !'%(url))
            return self.is_connect(url),url
        
    def test(self,urls=[]):
        pipeline = queue.Queue()
        for item in urls:
            pipeline.put(item)
    
        executor = ThreadPoolExecutor(max_workers=5)

        logger.debug(" pipeline size = %d" % pipeline.qsize())
        tasks = [
            executor.submit(self.do_action, pipeline)
            for item in urls
        ]
        result=[]
        for future in as_completed(tasks):
            speed,url = future.result()
            t={}
            t['url']=url
            t['speed']=speed
            result.append(t)

        wait(tasks, return_when=ALL_COMPLETED)
        return result
        # while tasks:
        #     done, not_done = wait(tasks,
        #             return_when=FIRST_COMPLETED)
        #     for future in done:
        #         ok,url = future.result()
        #         if ok >= 0:
        #             for task in not_done:
        #                 task.cancel()
        #             return ok,url
        #     tasks = not_done


        return -1,''


class V2RayCore(object):
    def __init__(self, node, index,args,base_port=10080):

        self.config = node.formatConfig()
        self.listen_port = base_port + index
        self.p = 0
        self.v2rayExecLocal = args.exe_path
        self.args = args
        self.node = node


    def balance_service(self,services):
        self.config = self.node.add_balance(services)
 

    def run_v2ray(self):
        logger.debug(json.dumps(self.config))
        root_dir = self.args.root_dir
        tmp = os.path.join(
            root_dir, "config_%d.json" % self.listen_port
        )
        self.config["inbounds"][0]["port"] = self.listen_port
        self.config["inbounds"][0]["listen"] = "0.0.0.0"
        self.config["inbounds"][0]["protocol"] = "http"
        self.config["log"]["access"] = os.path.join(
            root_dir, "log/access.log"
            # root_dir, "log/access_%d.log"%self.listen_port
        )
        self.config["log"]["error"] = os.path.join(
            root_dir,  "log/err.log"
            # root_dir,  "log/err_%d.log"%self.listen_port
        )
        log_path = os.path.join(root_dir,  "log")
        if not os.path.exists(log_path):
            os.makedirs(log_path)

        logger.debug(json.dumps(self.config))
        json.dump(self.config, open(tmp, "w"), indent=2)
        logger.debug("run test: %s -config %s" % (self.v2rayExecLocal, tmp))        
        try:
            self.p = subprocess.Popen([self.v2rayExecLocal, "-config", tmp],stdout=subprocess.PIPE,stderr=subprocess.PIPE)        
            output, err  = self.p.communicate(timeout=5)
            logger.debug("read err %s" % (err))
        except Exception as e:        
            logger.debug("execute err %s" % (e))
            pass
        
        count = 15
        # while err.find("started") < 0 and count > 0:
        #     output, err  = self.p.communicate(1)
        #     logger.debug(err)
        #     count = count - 1
        #     time.sleep(1)

        logger.debug("V2RAY RUN OK" )

    def test_connect(self,urls=[]):
        ret = []
        url=''
        # while self.p.poll() == 0:
        #     logger.debug("wait a sec.")
        #     time.sleep(1)
        try:
            self.args.name = self.config["remark"]
            self.args.port =self.listen_port
            tester = Testing(self.args)
            ret = tester.test(urls)
        except Exception as e:
            logger.debug('[%s] test_connect error!'%(e))
            pass
        # ret = self.is_connect(self.config["remark"], self.listen_port)

        return ret
        # print('%d : %d kb/s' %(self.listen_port, float(output) / 1000))

    def test_speed(self):
        pass

  
    def shutdown(self):
        if self.p != 0:
            self.p.terminate()
            self.p.wait()
            logger.debug("has terminated.")

