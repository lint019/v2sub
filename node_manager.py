# import concurrent.futures
import urllib
import logging
import queue
import random
import threading
import requests
import pyqrcode
import click
# from prettytable import PrettyTable

from shadowsocks import Shadowsocks
from concurrent.futures import (
    ThreadPoolExecutor,
    wait,
    ALL_COMPLETED,
    FIRST_COMPLETED,
    as_completed,
)
import time

from v2ray import V2ray

from v2ray_node import *
from utils import *

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


TEST_PORT_BASE = 10080
PROXY_PORT_BASE = 20080


def producer(queue, event):
    """Pretend we're getting a number from the network."""
    while not event.is_set():
        message = random.randint(1, 101)
        logging.info("Producer got message: %s", message)
        queue.put(message)

    logging.info("Producer received event. Exiting")

class Message(object):
    def __init__(self, node,action):
        super(Message, self).__init__()
        self.node = node
        self.action =action 

class UI():
    def __init__(self,queue):        
        self.queue = queue
        self.services=[]

        self.mThread=threading.Thread(target=self.update_ui, args=())
        self.mThread.start()
    
    def indexOf(self,node):
        idx = -1
        if not isinstance(node,V2ray):
            return idx
        for index,item in enumerate(self.services): 
            if node.remark == item.remark:
                idx = index
                break;
        return idx

    def on_message(self,message):
        ret = True
        if message is not None:   
            # print("get message.%s"%message.action)
            index = self.indexOf(message.node)                         
            if message.action =='add':            
                if index < 0:                
                    self.services.append(message.node)  
                    # print("port %d speed %d"%(message.node.port,message.node.speed))                      
                else:
                    print("add exist name %s"%message.node.remark)
            elif message.action =='update':
                if index>=0:
                    self.services[index] = message.node
                else:
                    self.services.append(message.node)   
            elif message.action =='delete':
                if index>=0:
                    del self.services[index]
            elif message.action =='exit':
                print("exit message.")
                ret=False

        return ret

    def update_table(self):
        if len(self.services)==0:
            return
        click.clear()
        print("**************************************")
        self.services = sorted(self.services, key=lambda node: node.speed)
        for index,item in enumerate(self.services):
            if item.proxy_port > 0 and item.speed >=0:
                print("%d.[%s]- [%d] - %d.ms"%(index,item.remark,item.proxy_port,item.speed))
        print("**************************************")

    def update_ui(self):
        while True:                        
            try:
                self.update_table()  
                time.sleep(5)
                message = self.queue.get(False)                
                if not self.on_message(message):
                    return                    

                                     
                              
                
            except Exception as e:
                print(e)                
            except KeyboardInterrupt:
                break
        print("exit update_ui.")
             
    def stop(self):
        self.queue.put(Message(0,"exit"))
        self.mThread.join()


class NodeBase(object):
    def __init__(self,args):
        logger.debug("max_thread = %d" % int(args.threads))
        self.tasks = []
        self.max_size = int(args.threads)
        self.items = []
        self.pipeline = queue.Queue()
        self.event = threading.Event()
        self.executor = ThreadPoolExecutor(max_workers=self.max_size)
        self.index = 0


    def make_qrcode_png(self,node):
        quantumult_url = node.to_quantumult_url()
        vmess_qr = pyqrcode.create(quantumult_url, error='H')
        try:
            if not os.path.exists(self.args.qrcode_path):
                os.makedirs(self.args.qrcode_path)
            name = validateTitle(node.remark)    
            str_path = "{}-{}.png".format( name, node.uuid)            
            vmess_qr.png( os.path.join(self.args.qrcode_path, str_path), scale=5)
        except Exception as e:
            logger.error('Unable to save file![%s]'% e)


    def do_action(self, queue, event):
        

        # while not queue.empty():
        while not event.is_set() or not queue.empty():
            node = queue.get()
            # index = queue.qsize() % self.max_size
            logger.debug("current index = %d"%self.index)
            self.index = self.index+1
            return self.run(node, self.index)
        return None

    def run(self, node, index):
        logger.debug("dssddsdsds… 如等待时间过久，请检查网络。\n")
        pass

    def on_done(self, node):
        pass

    def start(self):
        # self.pipeline = queue.Queue(maxsize=self.max_size)
        # self.event = threading.Event()

        # executor = ThreadPoolExecutor(max_workers=self.max_size)

        logger.debug(" pipeline size = %d" % self.pipeline.qsize())
        self.tasks = [
            self.executor.submit(self.do_action, self.pipeline, self.event)
            for item in self.items
        ]

        # self.tasks = executor.map(self.do_action, self.pipeline, self.event, self.items)
        self.event.set()


class Subscribe(NodeBase):
    def __init__(self, args):
        super(Subscribe, self).__init__(args)
        self.args = args
        # logger.debug("args = %s " % (args))

    def run(self, node, index):
        logger.debug("\n开始从订阅地址中读取服务器节点… 如等待时间过久，请检查网络。\n")
        logger.debug("start get subscribe url = %s %d" % (node, index))
        logger.debug("args = %s " % (self.args))
        servers = []
        try:            
            urldata = node["md5"]
            servers = decode(urldata).splitlines(False)
            logger.info("[%s] HAS [%d ] URLS" % (node["url"],len(servers)))

        except Exception as e:
            logger.error("parse subscribe url fail:[%s]" % e)

        return servers

    def on_done(self, list):
        logger.debug("server2 list = %s" % list)

    def parse_file(self, config_file):

        try:
            with open(config_file, encoding="utf-8") as f:
                strs = f.read()
                obj = json.loads(strs)
                logger.debug("jstring - %s " % strs)
                updated = False
                for item in obj["subscribes"]:
                    if self.args.update or "md5" not in item:
                        logger.info("UPDATE NEW SUBCRIBE ...")
                        try:
                            item["md5"] = requests.get(item["url"].replace("\n", ""), proxies=self.args.proxies,timeout=self.args.connect_timeout).text
                            updated = True
                            logger.info("UPDATE NEW SUBCRIBE [%s] OK."%item["url"])
                        except Exception as e:
                            logger.info("UPDATE NEW SUBCRIBE [%s] FAIL."%item["url"])
                            logger.debug("UPDATE NEW SUBCRIBE[%s]"%e)
                            pass

                    if item["enabled"]:
                        self.items.append(item)
                        self.pipeline.put(item)
                f.close()
                if updated:
                    logger.info("SAVE NEW SUBCRIBE[%s]"%self.args.subFilePath)
                    json.dump(obj, open(self.args.subFilePath, mode="w", encoding="utf-8"), indent=2)

        except Exception as e:
            logging.debug(e)
        self.tasks = []
        self.start()
        servers = []
        for future in as_completed(self.tasks):
            data = future.result()
            servers = servers + data
        wait(self.tasks, return_when=ALL_COMPLETED)

        logger.info("TOTAL SERVICES[%d]" % (len(servers)))    
        result = []
        for i in range(len(servers)):
            try:
                if servers[i].startswith("ss://"):
                    pass
                    # ss node
                    # base64Str = servers[i].replace("ss://", "")
                    # base64Str = urllib.parse.unquote(base64Str)
                    # origin = decode(base64Str[0 : base64Str.index("#")])
                    # remark = base64Str[base64Str.index("#") + 1 :] | "no name"
                    # security = origin[0 : origin.index(":")]
                    # password = origin[origin.index(":") + 1 : origin.index("@")]
                    # ipandport = origin[origin.index("@") + 1 :]
                    # ip = ipandport[0 : ipandport.index(":")]
                    # port = int(ipandport[ipandport.index(":") + 1 :])
                    # logging.debug("【" + str(i) + "】" + remark)
                    # ssNode = Shadowsocks(ip, port, remark, security, password)
                    # result.append(ssNode)
                elif servers[i].startswith("vmess://"):
                    # vmess
                    logger.debug("vmess link:[%s]" % servers[i])
                    base64Str = servers[i].replace("vmess://", "")
                    jsonstr = decode(base64Str)
                    logger.debug("vmess*%s" % jsonstr)
                    serverNode = json.loads(jsonstr)
                    logger.debug("【" + str(i) + "】" + serverNode["ps"])

                    v2Node = V2ray(                        
                        serverNode["add"],
                        int(serverNode["port"]),
                        serverNode["ps"] + "_" + str(i),
                        "auto",
                        serverNode["id"],
                        int(serverNode["aid"]),
                        serverNode["net"],
                        serverNode["type"],
                        serverNode["host"],
                        serverNode["path"],
                        serverNode["tls"],
                        self.args.root_dir,
                    )
                    result.append(v2Node)
                else:
                    pass

            except BaseException as e:
                logger.debug("%d node error.[%s]" % (i, e))
                pass
        logger.info("RESUTL HAS [%d]VALID VESS URLS" % (len(result)))            
        return result


class ConnectTest(NodeBase):
    def __init__(self, args):
        super(ConnectTest, self).__init__(args)
        self.args = args

    def run(self, node, index):
        ret = None
        try:
            test = V2RayCore(node, index, self.args, TEST_PORT_BASE)
            test.run_v2ray()
            r = test.test_connect()            
            test.shutdown()            
            if r>0:
                logger.info("[%d] %s -- OK " % (index, node.remark))
                self.make_qrcode_png(node)
                ret = node
            else:
                logger.info("[%d] %s -- FAIL " % (index, node.remark))
        except Exception as e:            
            # logger.error(e)
            logger.info("[%d] %s -- FAIL " % ( index,node.remark))
        finally:
            test.shutdown() 
        return ret

    def start_test(self, server_list):
        logger.debug("start_test")
        if len(server_list) == 0:
            logger.error("ConnectTest servers is empty.")
            return []


        servers = []
        for item in server_list:
            self.items.append(item)
            self.pipeline.put(item)
        self.start()

        
        wait(self.tasks, return_when=ALL_COMPLETED)
        for future in as_completed(self.tasks):
            data = future.result()
            if data is not None:
                servers.append(data)

        return servers


class ProxyManager(NodeBase):
    def __init__(self, args):
        super(ProxyManager, self).__init__(args)
        self.message_queue = queue.Queue()        
        
        self.args = args
        # self.args.message_queue = self.message_queue
        self.nodes = []
        self.runings = []        

    def run(self, node, index):
        ret = None
        port =PROXY_PORT_BASE + index
        try:
            test = V2RayCore(node, index, self.args, PROXY_PORT_BASE)
            test.run_v2ray()
            count = 5
            flag = True
            while count > 0:
                # print("[%s]OFFER PORT:%d" % (node.remark,PROXY_PORT_BASE + index))                
                speed = test.test_connect()
                node.proxy_port= PROXY_PORT_BASE + index
                node.speed = speed
                if  speed  <0:
                    if not flag:
                        count = count -1
                    flag = False
                else:
                    flag = True
                self.message_queue.put(Message(node,"update"))
                time.sleep(30)
            self.message_queue.put(Message(node,"delete"))
            # logger.info("[%s][%d] LOST " % (node.remark,PROXY_PORT_BASE + index))
        except Exception as e:
            logger.error(e)
        finally:
            print("[%s][%d]finaylly done to shutdown"%(node.remark,port))
            test.shutdown()     
        return ret

    def offer(self, server_list):
        if len(server_list) == 0:
            logger.error("servers is empty.")
            return []

        servers = []

        
        ui = UI(self.message_queue)  

        for item in server_list:
            self.items.append(item)
            self.pipeline.put(item)
            self.message_queue.put(Message(item,"add"))
            # logger.info("Message add")
            self.make_qrcode_png(item)

        self.start()

        for future in as_completed(self.tasks):
            data = future.result()
            if data is not None:
                servers.append(data)
        wait(self.tasks, return_when=ALL_COMPLETED)
        ui.stop()

        logger.info("ALL SERVICE NOT AVAILABLED ")






class OnlyOneService(NodeBase):
    def __init__(self, args):
        args.threads = 1
        super(OnlyOneService, self).__init__(args)
        self.args = args

    def run(self, node, index):
        ret = None
        port =PROXY_PORT_BASE + index
        try:
            test = V2RayCore(node, index, self.args, PROXY_PORT_BASE)
            test.balance_service(self.args.services)
            test.run_v2ray()
            count = 5
            flag = True
            while count > 0:
                print("[%s]OFFER PORT:%d" % (node.remark,PROXY_PORT_BASE + index))                
                speed = test.test_connect()
                if  speed  <0:
                    if not flag:
                        count = count -1
                    flag = False
                else:
                    flag = True
                time.sleep(30)
            # logger.info("[%s][%d] LOST " % (node.remark,PROXY_PORT_BASE + index))
        except Exception as e:
            logger.error(e)
        finally:
            print("finaylly done to shutdown")
            test.shutdown()     
        return ret

    def offer(self,services):
        # for item in services:            
        #     self.make_qrcode_png(item)
        self.items.append(services[0])
        self.pipeline.put(services[0])
        self.args.services = services
        self.start()
        wait(self.tasks, return_when=ALL_COMPLETED)
