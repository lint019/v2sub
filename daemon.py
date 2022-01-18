import threading
import logging
import os
import subprocess
from time import sleep
import platform
system = platform.system().lower()

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def start(name):
    logger.info(" *****  START...  ")
    exec = "python"
    
    try:
        if os.name == "linux":
            pass
        elif os.name == "posix":
            exec = "python3"
            is_android = 'ANDROID_STORAGE' in os.environ
            if is_android:
                exec = "/vendor/bin/python3/bin/python3"
                
        # p = subprocess.Popen([exec, name,"-u"])
        p = subprocess.Popen([exec, name,"-u","-v"])
        status = p.wait()   
    except Exception as e:
        logger.error("run error.")
        pass
    finally:
        logger.info("terminate")
        p.terminate();


    # print("\nRUN AGAIN.")
    # t1 = threading.Timer(120, start,(name,))    
    # t1.start()
name = os.path.join(os.path.dirname(os.path.realpath(__file__)), "v2_service.py")

while True:
    start(name)
    sleep(120)
    logger.info("RUN AGAIN.")
