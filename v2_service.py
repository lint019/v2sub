import logging
import argparse
from multiprocessing import process
import os
import shutil
import pathlib

from node_manager import *

from web.web import WebServer
from msg import MsgMgr
from worker import Worker

from config import v2ray_conf, conf

# from .utils import state_name

state_index = {"all": 0, "downloading": 1, "paused": 2, "finished": 3, "invalid": 4}
state_name = ["all", "downloading", "paused", "finished", "invalid"]

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - {%(pathname)s:%(lineno)d} - %(levelname)s - %(message)s"
)


class WebMsgDispatcher(object):

    SuccessMsg = {"status": "success"}
    InternalErrorMsg = {"status": "error", "errmsg": "Internal Error"}
    TaskExistenceErrorMsg = {"status": "error", "errmsg": "URL is already added"}
    TaskInexistenceErrorMsg = {"status": "error", "errmsg": "Task does not exist"}
    UrlErrorMsg = {"status": "error", "errmsg": "URL is invalid"}
    InvalidStateMsg = {"status": "error", "errmsg": "Invalid query state"}
    RequestErrorMsg = {"status": "error", "errmsg": "Request error"}

    @classmethod
    def init(cls, task_mgr,conf):
        cls._task_mgr = task_mgr
        cls._conf = conf

    @classmethod
    def event_state(cls, svr, event, data, args):
        c = cls._task_mgr.state()
        svr.put({"status": "success", "detail": c})

    @classmethod
    def event_list(cls, svr, event, data, args):
        exerpt, state = data["exerpt"], data["state"]
        if state not in state_name:
            svr.put(cls.InvalidStateMsg)
        else:
            d, c = cls._task_mgr.list(state, exerpt)
            svr.put({"status": "success", "detail": d, "state_counter": c})

    @classmethod
    def event_start_all(cls, svr, event, data, args):

        d, c = cls._task_mgr.start_all()
        svr.put({"status": "success", "detail": d, "state_counter": c})
    
    @classmethod
    def event_subscribe(cls, svr, event, data, args):

        d, c = cls._task_mgr.subscribe()
        svr.put({"status": "success", "detail": d, "state_counter": c})

    @classmethod
    def event_query(cls, svr, event, data, args):
        logger.debug('query event')
        tid, exerpt = data['tid'], data['exerpt']

        try:
            detail = cls._task_mgr.query(tid, exerpt)
        except TaskInexistenceError:
            svr.put(cls.TaskInexistenceErrorMsg)
        else:
            svr.put({'status': 'success', 'detail': detail})

    @classmethod
    def event_offer(cls, svr, event, data, args):

        d, c = cls._task_mgr.offer()
        svr.put({"status": "success", "detail": d, "state_counter": c})

    @classmethod
    def event_qrcode(cls, svr, event, data, args):
        tid, exerpt = data['tid'], data['exerpt']
        d = cls._task_mgr.qrcode(tid)
        svr.put(d)

    @classmethod
    def event_pac(cls, svr, event, data, args):
        
        valid_ports = cls._task_mgr.pac_valid_ports()
        # svr.put(valid_ports)
        svr.put(cls._conf.v2ray_conf.make_pac_file(data['param'],valid_ports))

    @classmethod
    def event_reboot(cls, svr, event, data, args):
        
        msg = cls._task_mgr.reboot()
        svr.put(msg)

    @classmethod
    def event_config(cls, svr, event, data, arg):
        act = data['act']

        ret_val = cls.RequestErrorMsg
        if   act == 'get':
            ret_val = {'status': 'success'}
            ret_val['config'] = cls._conf.dict()
        elif act == 'update':
            conf_dict = data['param']
            cls._conf.load(conf_dict)
            suc, msg = cls._conf.save2file()
            if suc:
                ret_val = cls.SuccessMsg
            else:
                ret_val = {'status': 'error', 'errmsg': msg}

        svr.put(ret_val)
           

class WorkMsgDispatcher(object):

    _task_mgr = None

    @classmethod
    def init(cls, task_mgr):

        cls._task_mgr = task_mgr

    @classmethod
    def event_worker_done(cls, svr, event, data, arg):
        tid, data = data["tid"], data["data"]
        try:
            cls._task_mgr.finish_task(tid)
        except TaskInexistenceError:
            cls.logger.error("Cannot finish, task does not exist")

    @classmethod
    def event_progress(cls, svr, event, data, arg):
        tid, data = data["tid"], data["data"]
        try:
            cls._task_mgr.progress_update(tid, data)
        except TaskInexistenceError:
            cls.logger.error("Cannot update progress, task does not exist")

    @classmethod
    def event_worker_done(cls, svr, event, data, arg):
        tid, data = data['tid'], data['data']
        try:
            cls._task_mgr.finish_task(tid)
        except TaskInexistenceError:
            cls.logger.error('Cannot finish, task does not exist')

    @classmethod
    def event_config(cls, svr, event, data, arg):
        act = data['act']

        ret_val = cls.RequestErrorMsg
        if   act == 'get':
            ret_val = {'status': 'success'}
            ret_val['config'] = cls._conf.dict()
        elif act == 'update':
            conf_dict = data['param']
            cls._conf.load(conf_dict)
            suc, msg = cls._conf.save2file()
            if suc:
                ret_val = cls.SuccessMsg
            else:
                ret_val = {'status': 'error', 'errmsg': msg}

        svr.put(ret_val)
    @classmethod
    def event_speed_result(cls, svr, event, data, arg):
        tid, data = data['tid'], data['data']
        try:
            cls._task_mgr.speed_result(tid,data)
        except TaskInexistenceError:
            cls.logger.error('Cannot finish, task does not exist')




class Task(object):
    def __init__(self, args, tid, msg_cli, node, index):
        self.args = args
        self.tid = tid
        self.node = node
        self.msg_cli = msg_cli
        self.index = index

    def start(self):
        self.state = state_index["downloading"]
        self.worker = Worker(self.args, self.tid, self.msg_cli, self.node, self.index)
        self.worker.start()


class TaskManager(object):
    def __init__(self, args, msg_cli,conf):
        self.args = args
        self._msg_cli = msg_cli
        self._conf = conf
        self._tasks_dict = {}
        self.services = parse_sub_file(self.args,args.root_dir, args.subFilePath)
        # self.queue = queue.Queue(20)
        # thread = threading.Thread(target=self.on_start_task)
        # thread.start()
        self.sub_manager = Subscribe(args)
        self.connect_tester= ConnectTest(args)
        self.offer_manager = HaproxyManager(args)
        # self.offer_manager = OnlyOneService(args)
        self.alvailableds=[]
        self._tasks_dict["state"]="invalid"
        

    def on_start_task(self):
        while True:
            logger.debug("get task")
            task = self.queue.get()
            task.start()

    
    

    def on_subscribe(self):

        self._tasks_dict["state"]="downloading"

        logger.info("SUBSCRIBLE")
        self.args.update= True
        self.services = self.sub_manager.parse_file(self.args.subFilePath)        
        counter = len(self.services)
        logger.info("GET URL SERVICES[%d]"%counter)

        self._tasks_dict["state"]= "all"

    def on_start_all(self):        
        while True:
            self._tasks_dict["state"]="downloading"
            self.args.update= True
            self.services = self.sub_manager.parse_file(self.args.subFilePath)     
            logger.info("START URL SERVICES[%d]"%len(self.services))
            self.alvailableds =self.connect_tester.start_test(self.services)
            logger.info("GET AVAILABLED SERVICES[%d]"%len(self.alvailableds))
            self._tasks_dict["state"]= "all"
            if(len(self.alvailableds)==0):
                time.sleep(30)
            else:
                break
       
        

        # for index, item in enumerate(self.services):
        #     logger.debug("start index = %d"%index)
        #     self.start_task(item, index)


    def new_task(self, url):
        tid = url2tid(url)
        return tid

    def start_task(self, node, index):
        task = None
        tid = new_uuid()
        if tid in self._tasks_dict:
            task = self._tasks_dict[tid]
            if task.state == state_index["downloading"]:
                raise TaskError("Task is downloading")
        else:
            task = Task(self.args, tid, self._msg_cli, node, index)
            self._tasks_dict[tid] = task

        self.queue.put(task);
        # task.start()

    def delete_task(self, tid, del_file=False):
        logger.debug("task deleted (%s)" % (tid))

    def reboot(self):
        try:
            p = subprocess.Popen(["reboot"])        
            time.sleep(1)
            p.terminate()
        except Exception as e:        
            logger.debug("execute err %s" % (e))
        return {}
        

    def list(self, state, exerpt=False):
        detail = []
        a =0
        process = 0
        if self._tasks_dict["state"]=="downloading":
            a = len(self.services)
            if "progress" in self._tasks_dict:
                process =int(self._tasks_dict['progress']['index']/self._tasks_dict['progress']['total']*100)

        counter = {'progress':process,'downloading': a, 'paused': len(self.services)-a, 'finished': len(self.alvailableds), 'invalid': len(self.offer_manager.items)}
        list=[]
        if state=='finished':
            list= self.alvailableds
        elif state=='invalid':
            list =self.offer_manager.items     
            list = sorted(list, key=lambda node: node.speed)       
        else:
            list= self.services

       
        for item in list:
            t = {}
            t["title"]=item.remark
            t["state"]=state
            t["description"]="ddddsss"
            t["url"]=item.camouflageHost
            t["valid"]="1"
            t["tid"]=url2tid(item.remark+item.uuid)            
            # if t["tid"] in self._tasks_dict:
            #     t["speed"]=self._tasks_dict[t["tid"]]['speed']
            #     t['total_bytes']=self._tasks_dict[t["tid"]]['speed']
            # else:
            #     t["speed"]='10'
            #     t['total_bytes']=0
            t['total_bytes']=item.speed
            t['percent']=str(process) +"%"          
            t['filename']=665          
            t['tmpfilename']=665       
            t['downloaded_bytes']=665                    
            t['total_bytes_estmt']=665  
            t['eta']=str(item.proxy_port)
            t['elapsed']=665       

            if len(self.args.urls) >0 and self.args.urls[0]  in item.speed_detail:
                t['filename']=self.args.urls[0]  
                t['total_bytes_estmt']=item.speed_detail[self.args.urls[0]]
                    
            # t['thumbnail']="/task/tid/%s/qrcode"%t["tid"]
            detail.append(t)
        
        return detail, counter

    def qrcode(self, tid, exerpt=True):
        found = None
        for item in self.services:
            t =url2tid(item.remark+item.uuid)
            if tid == t:
                found=item
                break
        
        detail = ""
        if found is not None:            
            detail =  make_qrcode_png(found,self.args)
        return detail

    def speed_result(self, tid, data):         
        self._tasks_dict[tid]=data
    
    def pac_valid_ports(self):   

        # detail: {
        #            "youtube.com":200
        #            "github.com":22}
        # sample:
        # [{'url':'youtube.com','list':[{'port':20083,'speed':222},{'port':20081,'speed':222}]}] 
        list = self.alvailableds
        # list = self.connect_tester.items

        detail_list=[]
        if len(list)>0:
            for key_url in self.args.urls:                
                url_list = list
                # sorted(list, key=lambda node: node.speed_detail[key_url])
                # logger.debug("after sort:",json.dumps(url_list))
                detail={}
                detail['url']=key_url
                detail['list']=[]
                for index,i in enumerate(list):
                    logger.debug("dd [%d] dd:%s"%(id(i),json.dumps(i.speed_info)))
                    if key_url in i.speed_info and i.speed_info[key_url] >0:
                        s={}
                        s['port']=i.proxy_port
                        s['speed']=i.speed_detail[key_url]
                        detail['list'].append(s)
                        if len(detail['list'])>3:
                            break
                detail['list'] = sorted(detail['list'], key=lambda node: node['speed'])    
                detail_list.append(detail)
                
        logger.debug("after sort:%s"%json.dumps(detail_list))
        return detail_list

        # list = sorted(list, key=lambda node: node.speed)  
        # list_port = []
        # for item in list:
        #     # if item.speed>=0:
        #     item.speed_detail['port']=item.proxy_port
        #     list_port.append(item.speed_detail)
        # return list_port
        

    def query(self, tid, exerpt=True):
        detail = {}
        found = None
        for item in self.services:
            t =url2tid(item.remark+item.uuid)
            if tid == t:
                found=item
                break
        
        t = {}
        if found is not None: 
            t["title"]=item.remark
            t["state"]="Finished"
            t["description"]="ddddsss"
            t["url"]=item.camouflageHost
            t["valid"]="1"
            t["tid"]=url2tid(item.remark+item.uuid)  
            t['percent']=item.proxy_port 
            t["eta"]=665            
            t['percent']=665    
            if self.args.urls[0]  in item.speed_detail:
                t['filename']=self.args.urls[0]  
                t['total_bytes_estmt']=item.speed_detail[self.args.urls[0]]
            t['tmpfilename']=665       
            t['downloaded_bytes']=665  
            t['total_bytes']=665       
                                
            t['eta']=str(item.proxy_port)              
            t['elapsed']=665 
            t['thumbnail']="/task/tid/%s/qrcode"%t["tid"]
        return t

    def state(self):
        return []

    def subscribe(self):
        detail = []
        counter = 0
        if self._tasks_dict["state"]== "downloading":
            logger.error("Task is subscribing")
        else:
            thread = threading.Thread(target=self.on_subscribe)
            thread.start()
            # logger.info("START URL SERVICES[%d]"%len(self.services))
            # self.alvailableds =self.connect_tester.start_test(self.services)
        return detail, counter

    def start_all(self):
        detail = []
        counter = 0
        if self._tasks_dict["state"]== "downloading":
            logger.error("Task is testing all")
        else:
            thread = threading.Thread(target=self.on_start_all)
            thread.start()
        return detail, counter

        # for index, item in enumerate(self.services):
        #     self.start_task(item, index)

    def offer(self):
        detail = []
        counter = len(self.alvailableds)
        # counter = len(self.services)
        if counter>0:
            try:
                # self.offer_manager.offer_no_wait(self.alvailableds)
                self.offer_manager.offer(self.alvailableds)
                # self.offer_manager.offer(self.services)
                # self.alvailableds =self.connect_tester.start_test(self.alvailableds)
                logger.info('OFFER COUNT(%d)' %(counter))
            except Exception as e:
                logger.debug(e)
            

        return detail, counter


    def update_info(self, tid, info_dict):
        if tid not in self._tasks_dict:
            raise TaskInexistenceError("task does not exist")

    def progress_update(self, tid, data):        
        self._tasks_dict['progress']=data
        
    def finish_task(self, tid):
        logger.debug('task finished (%s)' %(tid))

        if tid not in self._tasks_dict:
            raise TaskInexistenceError('task does not exist')

def load_conf_from_file(args):
    conf_file = args.config
    logger.info('load config file (%s)' %(conf_file))

    if  conf_file is None:
        return (None, {}, {})

    abs_file = args.configFilePath
    try:
        with open(abs_file) as f:
            return (abs_file, json.load(f))
    except FileNotFoundError as e:
        logger.critical("Config file (%s) doesn't exist", abs_file)
        exit(1)

def start_service(args):


    conf_file, conf_dict = load_conf_from_file(args)
    _conf = conf(conf_file, conf_dict=conf_dict)
    logger.debug("configuration: \n%s", json.dumps(_conf.dict(), indent=4))

    args.urls=_conf.v2ray_conf.get_filter_urls()
    msg_mgr = MsgMgr()
    web_cli = msg_mgr.new_cli("server")
    task_cli = msg_mgr.new_cli()

    args.task_cli = task_cli

    task_mgr = TaskManager(args, task_cli,_conf)

    WebMsgDispatcher.init(task_mgr,_conf)
    WorkMsgDispatcher.init(task_mgr)

    msg_mgr.reg_event("list", WebMsgDispatcher.event_list)
    msg_mgr.reg_event("state", WebMsgDispatcher.event_state)
    msg_mgr.reg_event("config", WebMsgDispatcher.event_config)
    msg_mgr.reg_event("start_all", WebMsgDispatcher.event_start_all)
    msg_mgr.reg_event("subscribe", WebMsgDispatcher.event_subscribe)
    msg_mgr.reg_event('query',      WebMsgDispatcher.event_query)
    msg_mgr.reg_event('offer',      WebMsgDispatcher.event_offer)
    msg_mgr.reg_event('qrcode',      WebMsgDispatcher.event_qrcode)
    msg_mgr.reg_event('pac',      WebMsgDispatcher.event_pac)
    msg_mgr.reg_event('reboot',      WebMsgDispatcher.event_reboot)

    msg_mgr.reg_event("progress", WorkMsgDispatcher.event_progress)
    msg_mgr.reg_event("worker_done", WorkMsgDispatcher.event_worker_done)
    msg_mgr.reg_event("speed_result", WorkMsgDispatcher.event_speed_result)

    web_server = WebServer(web_cli,  _conf['server']['host'], _conf['server']['port'])
    web_server.start()

    task_mgr.start_all()

    # msg_mgr.start()
    msg_mgr.run()


def startTest(args):

    subscribe = Subscribe(args)
    tester = ConnectTest(args)

    services = subscribe.parse_file(args.subFilePath)
    logger.info("SERVICE [%d] FOUND.", len(services))

    services = tester.start_test(services)
    logger.info("SERVICE AVAILABLE [%d].", len(services))

    # 一个服务，负载平衡
    if len(services) > 0:
        proxies = OnlyOneService(args)
        proxies.offer(services)

    # 多服务端口
    # proxies = ProxyManager(args)
    # proxies.offer(services)

    logger.info("PROCESS EXIT")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="v2服务", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "-m", "--mode", help="change_node | speed_test", default="speed_test"
    )
    parser.add_argument("-u", "--update", help="update subscribe", action="store_true")
    parser.add_argument("-t", "--threads", help="speed test threads", default=20)
    parser.add_argument(
        "-s", "--connect_timeout", help="connect timeout second", default=15
    )
    parser.add_argument(
        "-d", "--root_dir", help="read and write directory", default="/data/v2"
    )
    parser.add_argument(
        "-c", "--config", help="config file ", default="config.json"
    )
    parser.add_argument("-v", "--verbose", help="Verbose logging", action="store_true")
    args = parser.parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not os.path.exists(args.root_dir):
        os.makedirs(args.root_dir)
    dir_path = os.path.dirname(os.path.realpath(__file__))
    subFilePath = os.path.join(args.root_dir, "v2sub.conf")
    configFilePath = os.path.join(args.root_dir, args.config)
    args.exe_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "v2ray-core", os.name, "v2ray"
    )
    args.proxies = {}
    if os.name == "linux":
        pass
    elif os.name == "nt":
        args.root_dir = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "v2ray-core", os.name ) 
        subFilePath = os.path.join(dir_path, "v2sub.conf")
        configFilePath = os.path.join(dir_path, args.config)
        args.proxies = {
            "http": "http://linyaoji:fuckyou==123@10.255.251.141:8080",
            "https": "http://linyaoji:fuckyou==123@10.255.251.141:8080",
        }
        args.haproxy_exec_path = "cmd.exe"
    elif os.name == "posix":
        pathlib.Path(os.path.join(args.root_dir, "qrcode")).mkdir(
            parents=True, exist_ok=True
        )
        args.haproxy_exec_path = os.path.join(dir_path,"haproxy","android","haproxy")
        
    if not os.path.exists(subFilePath):
        shutil.copy(os.path.join(dir_path, "v2sub.conf"), subFilePath)
    
    if not os.path.exists(configFilePath):
        shutil.copy(os.path.join(dir_path, "config.json"), configFilePath)

    # args.urls = [
    #     'https://www.youtube.com',
    #     'https://www.github.com',
    #     'https://www.twitter.com',
    #     'https://www.gettr.com',
    #     'https://www.gtv.org',
    #     'https://www.xvideos.com',
    #     'https://www.pornhub.com',
    #     ]
    args.urls = [
        'https://www.youtube.com',
        ]

    args.qrcode_path = os.path.join(args.root_dir, "qrcode")
    try:
        shutil.rmtree(args.qrcode_path)
    except Exception as e:
        logger.error("rmdir error.[%s]" % (e))

    args.subFilePath = subFilePath
    args.configFilePath = configFilePath

    # startTest(args)
    start_service(args)
    logger.debug("process exit. availables")
