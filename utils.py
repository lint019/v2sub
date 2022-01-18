import requests
import base64
import json
import logging
import pyqrcode
import os
import re
import uuid

from hashlib import sha1
from v2ray import V2ray
from v2ray_node import *

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)



class TaskError:
    """Error related to download tasks."""

    def __init__(self, msg, tid=None):
        if tid:
            msg += " tid={}".format(tid)

        super(TaskError, self).__init__(msg)
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


class TaskInexistenceError(TaskError):
    def __init__(self, msg, tid=None, url=None, state=None):
        msg = "Task does not exist"
        if tid:
            msg += " tid={}".format(tid)
        if url:
            msg += " url={}".format(url)
        if state:
            msg += " state={}".format(state)

        super(TaskInexistenceError, self).__init__(msg)
        self.msg = msg


def new_uuid():
    return str(uuid.uuid4().hex)


def url2tid(url):
    return sha1(url.encode()).hexdigest()


def validateTitle(title):
    rstr = r"[\/\\\:\*\?\"\<\>\|]"  # '/ \ : * ? " < > |'
    new_title = re.sub(rstr, "_", title)  # 替换为下划线
    return new_title


def decode(base64Str):
    base64Str = base64Str.replace("\n", "").replace("-", "+").replace("_", "/")
    padding = int(len(base64Str) % 4)
    if padding != 0:
        base64Str += "=" * (4 - padding)
    return str(base64.urlsafe_b64decode(base64Str), "utf-8")


def decode_url(base64Str, altchars=b"+/"):
    """Decode base64, padding being optional.

    :param data: Base64 data as an ASCII byte string
    :returns: The decoded byte string.

    """
    base64Str = re.sub(rb"[^a-zA-Z0-9%s]+" % altchars, b"", base64Str)  # normalize
    missing_padding = len(base64Str) % 4
    if missing_padding:
        base64Str += b"=" * (4 - missing_padding)
    return str(base64.b64decode(base64Str, altchars), "utf-8")


def make_qrcode_png(v2Node, args):
    quantumult_url = v2Node.to_quantumult_url()
    logger.debug("quantumult_url *%s" % quantumult_url)
    str_path=""
    vmess_qr = pyqrcode.create(quantumult_url, error="H")
    try:
        dir = os.path.join(args.root_dir, "qrcode")
        if not os.path.exists(dir):
            os.makedirs(dir)
        name = validateTitle(v2Node.remark)
        str_path = "{}/{}-{}.png".format(dir, name, v2Node.uuid)
        # str_path = validateTitle(str_path)
        logger.debug("make png path *%s" % str_path)
        vmess_qr.png(str_path, scale=1)
    except Exception as e:
        logger.error("Unable to save file![%s]" % e)
    return str_path
    
def make_url_qrcode_png(url):
    vmess_qr = pyqrcode.create(url, error="H")
    try:
        vmess_qr.png(str_path, scale=5)
    except Exception as e:
        logger.error("Unable to save file![%s]" % e)


def parse_sub_file(args,root_dir,config_file,update=False):
    servers = []
    try:
        with open(config_file, encoding="utf-8") as f:
            strs = f.read()
            obj = json.loads(strs)
            logger.debug("jstring - %s " % strs)
            updated = False
            for item in obj["subscribes"]:

                if update :
                    logger.info("UPDATE NEW SUBCRIBE ...")
                    try:
                        item["md5"] = requests.get(item["url"].replace("\n", ""), proxies=args.proxies,timeout=args.connect_timeout).text
                        logger.info("UPDATE NEW SUBCRIBE [%s] OK."%item["url"])
                        updated = True
                    except Exception as e:
                        logger.info("UPDATE NEW SUBCRIBE [%s] FAIL."%item["url"])
                        logger.debug("UPDATE NEW SUBCRIBE[%s]"%e)
                        pass

                urldata = item["md5"]
                list = decode(urldata).splitlines(False)
                servers = servers+list

            f.close()
            if updated:
                logger.info("SAVE NEW SUBCRIBE[%s]"%config_file)
                json.dump(obj, open(config_file, mode="w", encoding="utf-8"), indent=2)

    except Exception as e:
        logging.debug(e)
    
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
                    root_dir,
                )
                result.append(v2Node)
            else:
                pass

        except BaseException as e:
            logger.debug("%d node error.[%s]" % (i, e))
            pass
    logger.info("RESUTL HAS [%d]VALID VESS URLS" % (len(result)))
    return result
