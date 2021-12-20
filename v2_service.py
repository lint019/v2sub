import logging
import argparse
import os
import shutil
import pathlib

from node_manager import *

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def startTest(args):

    subscribe = Subscribe(args)    
    tester = ConnectTest(args)

    services = subscribe.parse_file(args.subFilePath)
    logger.info("SERVICE [%d] FOUND.",len(services))

    services = tester.start_test(services)
    logger.info("SERVICE AVAILABLE [%d].",len(services))
    
    #一个服务，负载平衡
    if len(services)>0:
        proxies = OnlyOneService(args) 
        proxies.offer(services)
    
    #多服务端口
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
    parser.add_argument("-s", "--connect_timeout", help="connect timeout second", default=15)
    parser.add_argument(
        "-d", "--root_dir", help="read and write directory", default="/data/v2"
    )
    parser.add_argument("-v", "--verbose", help="Verbose logging", action="store_true")
    args = parser.parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)


    dir_path = os.path.dirname(os.path.realpath(__file__))
    subFilePath = os.path.join(args.root_dir, "v2sub.conf")
    args.exe_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "v2ray-core", os.name, "v2ray")
    args.proxies ={}
    if os.name == "linux":
        pass
    elif os.name == "nt":
        args.root_dir = dir_path
        subFilePath = os.path.join(args.root_dir, "v2sub.conf")
        args.proxies = { "http": "http://linyaoji:fuckyou==123@10.255.251.141:8080", "https": "http://linyaoji:fuckyou==123@10.255.251.141:8080"}
        
    elif os.name == "posix":
        pathlib.Path(os.path.join(args.root_dir, "qrcode")).mkdir(parents=True, exist_ok=True)
        if not os.path.exists(subFilePath):
            shutil.copy(os.path.join(dir_path, "v2sub.conf"),subFilePath)
    args.qrcode_path = os.path.join(args.root_dir,"qrcode")
    try:
        shutil.rmtree(args.qrcode_path)
    except Exception as e:
        logger.error("rmdir error.[%s]" % ( e))
    
    args.subFilePath = subFilePath
       
    startTest(args)
    logger.debug("process exit. availables")

