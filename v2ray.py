#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import os
import sys
import urllib
import time

import base64
import json
import subprocess

import requests
import logging
import argparse
import re

import queue
import threading
import time
import pyqrcode

logger = logging.getLogger(__name__)

from shadowsocks import Shadowsocks
from v2ray import V2ray

def validateTitle(title):
    rstr = r"[\/\\\:\*\?\"\<\>\|]"  # '/ \ : * ? " < > |'
    new_title = re.sub(rstr, "_", title)  # 替换为下划线
    return new_title

def decode(base64Str):
    base64Str = base64Str.replace('\n', '').replace('-', '+').replace('_', '/')
    padding = int(len(base64Str) % 4)
    if padding != 0:
        base64Str += '=' * (4 - padding)
    return str(base64.b64decode(base64Str),  'utf-8')
def askfollowRedirect(json):
    isfollowRedirect = ''
    try:
        isfollowRedirect = input('是否使用透明代理（重启失效）？[y/n/exit]')
    except KeyboardInterrupt:
        exit()
    except BaseException:
        return json
    if isfollowRedirect == 'y':
        # 判断是否开启了ip转发
        ipforward = subprocess.check_output("cat /proc/sys/net/ipv4/ip_forward",  shell=True)
        if ipforward == b'0\n':
            #添加ip转发
            subprocess.call("sysctl -w net.ipv4.ip_forward=1",  shell=True)
            subprocess.call("sysctl -p /etc/sysctl.conf", shell=True)
        ## 修改json的相关参数
        json['inbounds'].append({
           "port": 12345,
           "protocol": "dokodemo-door",
           "settings": {
             "network": "tcp,udp",
             "followRedirect": True
           },
            "tag":"followRedirect",
           "sniffing": {
             "enabled": True,
             "destOverride": ["http", "tls"]
           }
        })
        json['routing']['settings']['rules'].append({
            "type": "field",
            "inboundTag": ["followRedirect"],
            "outboundTag": "out"
        })
        for outbound in json['outbounds']:
            if outbound["protocol"] == 'vmess' or outbound["protocol"] == 'shadowsocks':
                outbound['streamSettings']['sockopt'] = {
                    "mark": 255
                }
        #关闭之前的iptables转发
        closeiptableRedirect()
        #开启iptable转发
        openiptableRedirect()
        return json
    elif isfollowRedirect == 'n':
        ipforward = subprocess.check_output("cat /proc/sys/net/ipv4/ip_forward",  shell=True)
        if ipforward == b'1\n':
            # 添加ip转发
            subprocess.call("sysctl -w net.ipv4.ip_forward=0", shell=True, stdout = subprocess.DEVNULL)
            subprocess.call("sysctl -p /etc/sysctl.conf", shell=True, stdout = subprocess.DEVNULL)
        closeiptableRedirect()
        return json
    else:
        return askfollowRedirect(json)

def openiptableRedirect():
    subprocess.call("iptables -t nat -N V2RAY", shell=True, stdout = subprocess.DEVNULL)
    subprocess.call("iptables -t nat -A V2RAY -d 192.168.0.0/16 -j RETURN", shell=True, stdout = subprocess.DEVNULL)
    subprocess.call("iptables -t nat -A V2RAY -d 172.16.0.0/16 -j RETURN", shell=True, stdout = subprocess.DEVNULL)
    subprocess.call("iptables -t nat -A V2RAY -d 10.0.0.0/16 -j RETURN", shell=True, stdout = subprocess.DEVNULL)
    subprocess.call("iptables -t nat -A V2RAY -p tcp -j RETURN -m mark --mark 0xff", shell=True, stdout = subprocess.DEVNULL)
    subprocess.call("iptables -t nat -A V2RAY -p udp -j RETURN -m mark --mark 0xff", shell=True, stdout = subprocess.DEVNULL)
    try:
        subprocess.call("iptables -t nat -A V2RAY -p tcp --match multiport ! --dports 12345,1080,22 -j REDIRECT --to-ports 12345",shell=True, stdout = subprocess.DEVNULL)
    except BaseException:
        logging.debug('以存在相应规则!跳过!')
    subprocess.call("iptables -t nat -A OUTPUT -p tcp -j V2RAY", shell=True, stdout = subprocess.DEVNULL)

def closeiptableRedirect():
    subprocess.call("iptables -t nat -F V2RAY", shell=True, stdout = subprocess.DEVNULL)


v2rayConfigLocal=os.path.join(os.getcwd(),"v2ray-core",os.name, "config.json")
v2rayExecLocal=os.path.join(os.getcwd(),"v2ray-core", os.name,"v2ray")
SHARE_QUANTUMULT_QRCODE_PATH=os.path.join(os.getcwd(),"qrcode")
TEST_PORT_BASE = 10080
testFileUrl="http://cachefly.cachefly.net/10mb.test"
google_url = "https://www.github.com"
# google_url = "https://www.google.com"
# google_url = "https://www.twitter.com"
exitFlag = 0

class Manager(object):
    def __init__(self,cmd,args):
        self.cmd = cmd
        self.args = args
        self.p = 0

    def restart(self):
        self.stop()

        logger.debug("create cmd %s"%self.cmd)
        self.p = subprocess.Popen([self.cmd,self.args])
        # self.p = subprocess.Popen(self.cmd,shell=True,stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(3)
        if self.p.poll() is not None:
            return True
        
        return False

    def stop(self):
        os.system("killall v2ray")
        # if self.p !=0:
        #     self.p.terminate()
        
class SpeedTest(object):
    def __init__(self,config,id):
        self.config = config
        self.listen_port = TEST_PORT_BASE+id
        self.p =0
        
    def run_v2ray(self):

        # logger.debug(json.dumps(self.config))
        tmp = os.path.join(os.getcwd(),"v2ray-core",os.name, "config_%d.json"%self.listen_port)
        self.config['inbounds'][0]['port']= self.listen_port
        self.config['inbounds'][0]['protocol']= "http"
        self.config['log']['access']= os.path.join(os.getcwd(),"v2ray-core",os.name, "log/access.log")
        self.config['log']['error']= os.path.join(os.getcwd(),"v2ray-core",os.name, "log/err.log")
        log_path =os.path.join(os.getcwd(),"v2ray-core",os.name,"log")
        if not os.path.exists(log_path):
            os.makedirs(log_path)

        logger.debug(json.dumps(self.config))
        json.dump(self.config, open(tmp, 'w'), indent=2)
        logger.debug("run test: %s %s"%(v2rayExecLocal,tmp))
        self.p = subprocess.Popen([v2rayExecLocal,'-config',tmp])
        # output, unused_err = self.p.communicate()
        output = ""
        count = 5
        while output.find('started') < 0 and count >0:
            logger.debug(output)
            count = count -1
            time.sleep(1)

    
    def start_download(self):
        ret = False
        try:
            while self.p.poll()==0:
                logger.debug("wait a sec.")
                time.sleep(1)
            # proxies = { "http": "http://linyaoji:fuckyou-321@10.255.251.141:8080", "https": "http://linyaoji:fuckyou-321@10.255.251.141:8080"}    
            proxies = {"http": "http://127.0.0.1:%d"%self.listen_port,"https": "http://127.0.0.1:%d"%self.listen_port,"socks5": "http://127.0.0.1:%d"%self.listen_port}
            print("used : http://127.0.0.1:%d"%self.listen_port)
            # resp = requests.get(google_url,stream=True)
            resp = requests.get(google_url,proxies=proxies,timeout=30)
            if resp.status_code == 200:
                print ('[%s] OK!'%self.config['remark'])
                ret = True
            else:
                print ('[%s] Boo!'%self.config['remark'])
            # cmd = "curl -o /dev/null -s -w %{speed_download} -x socks5://127.0.0.1:%d %s"%(self.listen_port, testFileUrl)
            # output = subprocess.check_output(cmd, shell=True)
        except KeyboardInterrupt:
            pass
        except Exception as e:
            output = b'0.000'
            print ('[%s] error [%s]!'%(self.config['remark'],e))
        output =0

        return ret
        # print('%d : %d kb/s' %(self.listen_port, float(output) / 1000))

    def shutdown(self):
        if self.p !=0:
            self.p.terminate()
            self.p.wait()
            logger.debug("has terminated.")
        
    

def ping_node(ip):
    if os.name == 'linux':
        subprocess.call('ping ' + ip + ' -c 3 -w 10', shell=True)
    elif os.name =="nt":
        pass
    elif os.name =="posix":
        subprocess.call('ping ' + ip + ' -c 3 ', shell=True)
        logging.info("ping %s"%ip)


def backup_config():
    if os.name == 'linux':
        subprocess.call('cp ' + v2rayConfigLocal + ' ' + v2rayConfigLocal + '.bak', shell=True)        
    elif os.name =="nt":
        pass
    elif os.name =="posix":
        subprocess.call('cp ' + v2rayConfigLocal + ' ' + v2rayConfigLocal + '.bak', shell=True)        
    
def restore_config():
    if os.name == 'linux':
        subprocess.call('mv ' + v2rayConfigLocal + '.bak ' + v2rayConfigLocal , shell=True)
    elif os.name =="nt":
        pass
    elif os.name =="posix":
        subprocess.call('mv ' + v2rayConfigLocal + '.bak ' + v2rayConfigLocal , shell=True)
    
def change_node(jsonObj,mgr):
    if os.name == 'linux':
        logging.debug("\n重启 v2ray 服务……\n")
        subprocess.call('systemctl restart v2ray.service', shell=True)
        logging.debug('地址切换完成')
        logging.debug('代理端口协议：socks5')
        logging.debug('代理地址: 127.0.0.1')
        logging.debug('代理端口号：1080')
        pass
    elif os.name =="nt":
        pass
    elif os.name =="posix":
        restart_v2ray(mgr)
    print(os.name)    

def restart_v2ray(mgr):    
    return mgr.restart()        
    
# work_queue
# queue_lock

# work_queue = queue.Queue(10)        
queue_lock = threading.Lock()
class myThread (threading.Thread):
    def __init__(self, threadID,wq):
        threading.Thread.__init__(self)
        self.id = threadID
        self.work_queue = wq
        self.exit = False
        # self.queue_lock = queueLock
        
    def finish(self):
        self.exit = True

    def run(self):
        logger.debug("Starting %d"%self.id)
        process_data(self.id,self.work_queue)   
        # while not self.exit:
        #     queue_lock.acquire()
        #     # logger.debug("read %d"%id)
        #     if not self.work_queue.empty():
        #         # logger.debug("get queue %d"%id)
        #         config = self.work_queue.get()            
        #         queue_lock.release()
        #         do_test(id,config)            
        #     else:
        #         # logger.debug("empty queue %d"%id)
        #         queue_lock.release()             
        logger.debug("Exiting %d" % self.id)

def do_test(id,config):
    ret = False
    try:
        test = SpeedTest(config,id)
        test.run_v2ray()
        ret = test.start_download()
        test.shutdown()
    except Exception as e:
        logger.error(e)
    return ret
def process_data(id,work_queue):            
    while not exitFlag:
        queue_lock.acquire()
        # logger.debug("read %d"%id)
        if not work_queue.empty():
            # logger.debug("get queue %d"%id)
            node = work_queue.get()            
            queue_lock.release()
            ret = do_test(id,node.formatConfig())
            node.valid = ret
            # node.valid = ret or True
        else:
            # logger.debug("empty queue %d"%id)
            queue_lock.release()
            break
            
        # time.sleep(3)

    


def start(args):
    # mode = 'changeNode'
    # v2rayConfigLocal='/etc/v2ray/config.json'
    
    
    subFilePath = os.path.join(os.getcwd(), "v2sub.conf")

    proxies={}
    # cmd = "%s %s "%(v2rayExecLocal,v2rayConfigLocal)
    # exec = Manager(cmd,"")
    exec = Manager(v2rayExecLocal,v2rayConfigLocal)
    if len(sys.argv) == 2:
        mode = sys.argv[1]
    if os.name == 'linux':
        # 鉴权
        if os.geteuid() != 0:
            logging.debug("您需要切换到 Root 身份才可以使用本脚本。尝试在命令前加上 sudo?\n")
            exit()

        #判断v2ray服务是否安装
        if subprocess.call("systemctl is-enabled v2ray.service", shell=True, stdout = subprocess.DEVNULL, stderr = subprocess.DEVNULL) == 1:
            logging.debug('检测到v2ray未安装,将执行官方脚本安装v2ray,如果下载速度缓慢,请考虑手动本地安装v2ray,参考地址：https://www.v2ray.com/chapter_00/install.html')
            logging.debug('正在下载官方脚本')
            subprocess.run("wget https://install.direct/go.sh", shell=True, stdout = subprocess.DEVNULL)
            logging.debug('正在安装v2ray')
            subprocess.check_call('bash go.sh', shell=True)
            logging.debug('执行清理工作')
            subprocess.run('rm -rf go.sh', shell=True)
    elif os.name =="nt":
        logging.debug("使用系统代理")
        proxies = { "http": "http://linyaoji:fuckyou-321@10.255.251.141:8080", "https": "http://linyaoji:fuckyou-321@10.255.251.141:8080"}    
    elif os.name =="posix":
        pass    
    # 本脚本的配置文件，目前的作用是仅存储用户输入的订阅地址，这样用户再次启动脚本时，就无需再输入订阅地址。
    # 预设的存储的路径为存储到用户的 HOME 内。

    # 获取订阅地址
    if not os.path.exists(subFilePath):
        open(subFilePath, 'w+')

    links =[]
    # subFile = open(subFilePath, 'r')

    # try:
    #     links = subFile.readlines()
    #     print(type(links), links)
    #     for line in links:
    #         print(type(line), line)
    # finally:
    #     subFile.close()

    # try:
    with open(subFilePath, encoding='utf-8') as f:
        strs = f.read()
        obj = json.loads(strs)
        logger.debug("jstring - %s "%strs)
        for item in obj["subscribes"]:
            if item["enabled"]:
                links.append(item)
        f.close()
    # except Exception as e:            
    #     logger.error("read json %s:"%e)

 
    logger.debug("\n开始从订阅地址中读取服务器节点… 如等待时间过久，请检查网络。\n")

    serverListLink =[]
    for j in obj["subscribes"]:
        if not j["enabled"]:
            continue
        # 获取订阅信息
        logger.debug("start get subscribe url = %s"%j['url'])        
        # logging.debug(urldata)
        try:
            if args.update or 'md5' not in j :
                urldata = requests.get(j['url'].replace("\n",""),proxies=proxies).text
                j['md5']=urldata
                # json.dumps(subFilePath,links)
                json.dump(obj, open(subFilePath, mode='w',encoding='utf-8'),indent=2)
                logger.debug("update subscribe url = %s"%j['url'])
            else:
                urldata=j["md5"]
            servers = decode(urldata).splitlines(False)        
            for i in range(len(servers)):
                try:                
                    if servers[i].startswith('ss://'):
                    # ss node
                        base64Str = servers[i].replace('ss://', '')
                        base64Str = urllib.parse.unquote(base64Str)
                        origin = decode(base64Str[0 : base64Str.index('#')])
                        remark = base64Str[base64Str.index('#') + 1 :]
                        security = origin[0 : origin.index(':')]
                        password = origin[origin.index(':') + 1 : origin.index('@')]
                        ipandport = origin[origin.index('@') + 1 : ]
                        ip = ipandport[0: ipandport.index(':')]
                        port = int(ipandport[ipandport.index(':') + 1:])
                        logging.debug('【' + str(i) + '】' + remark)
                        ssNode = Shadowsocks(ip, port, remark, security, password)
                        serverListLink.append(ssNode)
                    else:
                        # vmess
                        logger.debug("vmess link:[%s]"%servers[i])
                        base64Str = servers[i].replace('vmess://', '')                
                        jsonstr = decode(base64Str)
                        logger.debug("vmess*%s"%jsonstr)
                        serverNode = json.loads(jsonstr)
                        logger.debug('【' + str(i) + '】' + serverNode['ps'])
                                               
                        v2Node = V2ray(serverNode['add'], int(serverNode['port']), serverNode['ps'], 'auto', serverNode['id'], int(serverNode['aid']), serverNode['net'], serverNode['type'], serverNode['host'], serverNode['path'], serverNode['tls'])                
                        
                        serverListLink.append(v2Node)
                        quantumult_url = v2Node.to_quantumult_url()
                        logger.debug("quantumult_url *%s"%quantumult_url)

                        vmess_qr = pyqrcode.create(quantumult_url, error='H')
                        try:
                            if not os.path.exists(SHARE_QUANTUMULT_QRCODE_PATH):
                                os.makedirs(SHARE_QUANTUMULT_QRCODE_PATH)
                            name = validateTitle(v2Node.remark)    
                            str_path = "{}\{}-{}.png".format(SHARE_QUANTUMULT_QRCODE_PATH, name, v2Node.uuid)
                            # str_path = validateTitle(str_path)
                            vmess_qr.png( str_path, scale=5)
                        except Exception as e:
                            logger.error('Unable to save file![%s]'%e)
                except BaseException  as e:
                    logger.error("%d node error.[%s]"%(i,e))
                    pass
        except Exception as e:
            logger.error("get subscribe url fail:[%s]"%e)
            continue  


    if args.mode == 'change_node':
        while True:
            try:
                for i in range(len(serverListLink)):
                    if isinstance(serverListLink[i],V2ray):
                        print('[' + str(i) + ']' + serverListLink[i].remark)
                setServerNodeId = int(input("\n请输入要切换的节点编号："))
            except KeyboardInterrupt:
                break
            except BaseException:
                continue
            ping_node(serverListLink[i].ip)
            inputStr = input('确定要使用该节点吗？[y/n/exit]  ')
            if inputStr == 'y':
                jsonObj = serverListLink[setServerNodeId].formatConfig()
                # jsonObj = askfollowRedirect(jsonObj)
                json.dump(jsonObj, open(v2rayConfigLocal, 'w'), indent=2)
                change_node(jsonObj,exec)
                exit()
            elif inputStr == 'n':
                continue
            else:
                break
    elif args.mode == "speed_test":        
        
        workQueue = queue.Queue(len(serverListLink))
        threads = []    

        # logger.debug("start fill queue" )
        # 填充队列
        queue_lock.acquire()
        for i in range(len(serverListLink)):
             if isinstance(serverListLink[i],V2ray):
                # logger.debug("put queue" )
                workQueue.put(serverListLink[i])
                # workQueue.put(serverListLink[i].formatConfig())
        queue_lock.release()
        # logger.debug("finish fill queue" )
        
        # 创建新线程
        for i in  range(int(args.threads)):
            thread = myThread(i,workQueue)
            thread.start()
            threads.append(thread)

        # 等待队列清空
        while not workQueue.empty():
            pass

        
        exitFlag = 0
        # 等待所有线程完成
        for t in threads:
            t.finish()
            t.join()

        for i in range(len(serverListLink)):
            print("speed test result-[{}] - [{}].".format(serverListLink[i].remark,serverListLink[i].valid))
        
        print("speed test done.")

        # copy config.json
        
        # print("\n正在备份现有配置文件 %s\n" % v2rayConfigLocal)
        # backup_config()
        # print("\n当前模式为测速模式\n")
        # for i in range(len(serverListLink)):            
        #     if isinstance(serverListLink[i],V2ray) or not restart_v2ray(exec):                
        #         print("%i start fail."%i)
        #         continue
        #     json.dump(serverListLink[i].formatConfig(), open(v2rayConfigLocal, 'w'), indent=2)
        #     try:
        #         time.sleep(5)
        #         output = subprocess.check_output('curl -o /dev/null -s -w %{speed_download} -x socks5://127.0.0.1:1080 ' + testFileUrl, shell=True)
        #     except KeyboardInterrupt:
        #         break
        #     except BaseException:
        #         output = b'0.000'
        #     print('【%d】%s : %d kb/s' %(i, serverListLink[i].remark, float(output) / 1000))
        # print("\n正在恢复现有配置文件 %s\n" % v2rayConfigLocal)
        # restore_config()
        # restart_v2ray(exec)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="多媒体http服务",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-m','--mode', help="change_node | speed_test", default='change_node')
    parser.add_argument("-u", "--update", help="update subscribe", action='store_true')
    parser.add_argument("-t", "--threads", help="speed test threads", default=1)
    parser.add_argument("-v", "--verbose", help="Verbose logging", action='store_true')
    args = parser.parse_args()
    if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)

    start(args)
