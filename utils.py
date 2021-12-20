import requests
import base64
import json
import logging
import pyqrcode
import os
import re


logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

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

def decode_url(base64Str, altchars=b'+/'):
    """Decode base64, padding being optional.

    :param data: Base64 data as an ASCII byte string
    :returns: The decoded byte string.

    """
    base64Str = re.sub(rb'[^a-zA-Z0-9%s]+' % altchars, b'', base64Str)  # normalize
    missing_padding = len(base64Str) % 4
    if missing_padding:
        base64Str += b'='* (4 - missing_padding)
    return str(base64.b64decode(base64Str, altchars), "utf-8")

def make_qrcode_png(v2Node,args):
    quantumult_url = v2Node.to_quantumult_url()
    logger.debug("quantumult_url *%s"%quantumult_url)

    vmess_qr = pyqrcode.create(quantumult_url, error='H')
    try:
        dir = os.path.join(args.root_dir, "qrcode")
        if not os.path.exists(dir):
            os.makedirs(dir)
        name = validateTitle(v2Node.remark)    
        str_path = "{}/{}-{}.png".format(dir, name, v2Node.uuid)
        # str_path = validateTitle(str_path)
        logger.debug("make png path *%s"%str_path)
        vmess_qr.png( str_path, scale=5)
    except Exception as e:
        logger.error('Unable to save file![%s]'%e)
