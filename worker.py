#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import logging
import json
from v2ray import V2ray
from v2ray_node import *

from threading import Thread as Process
from time import time

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - {%(pathname)s:%(lineno)d} - %(levelname)s - %(message)s"
)

TEST_PORT_BASE = 10080
PROXY_PORT_BASE = 20080


class Worker(Process):
    def __init__(self,args, tid, msg_cli, node,index):
        super(Worker, self).__init__()
        self.tid = tid
        self.node = node
        self.msg_cli = msg_cli
        self.index = index
        self.args = args

    def run(self):
        try:
            test = V2RayCore(self.node, self.index, self.args, TEST_PORT_BASE)
            test.run_v2ray()
            r = test.test_connect()            
            test.shutdown()            
            if r>0:
                logger.info("[%d] %s -- OK " % (self.index, self.node.remark))                                
            else:
                logger.info("[%d] %s -- FAIL " % (self.index, self.node.remark))
        except Exception as e:            
            logger.debug(e)
            logger.info("[%d] %s -- FAIL " % ( self.index,self.node.remark))
        finally:
            test.shutdown()         
       
        self.msg_cli.put('worker_done', {'tid': self.tid, 'data': {}})

    def stop(self):
        self.logger.info('Terminating Process ...')
        self.terminate()
        self.join()

