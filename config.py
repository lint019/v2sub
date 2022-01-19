import logging
import json

from copy import deepcopy
from os.path import expanduser


logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - {%(pathname)s:%(lineno)d} - %(levelname)s - %(message)s"
)



pac_script = (
'function FindProxyForURL(url, host)'
'{  '
'   '
'   url = url.toLowerCase();    '
'   host = host.toLowerCase();  '
'   '
'   var hostOrDomainIs = function(host, val) {  '
'      return (host === val) || dnsDomainIs(host, "." + val);   '
'   };  '
'   '
'   var hostIs = function(host, val) {  '
'	  return (host === val);    '
'   };  '
'       '
'       '
'   if (isPlainHostName(host))  '
'   {   '
'      return "DIRECT"; '
'   }   '
'   '
'   if (isResolvable(host)) '
'   {   '
'      var hostIP = dnsResolve(host);   '
'      if (!shExpMatch(hostIP, "*:*"))  '
'      {    '
'        /* Don"t proxy non-routable addresses (RFC 3330) */    '
'        if (isInNet(hostIP, "0.0.0.0", "255.0.0.0") || '
'        isInNet(hostIP, "10.0.0.0", "255.0.0.0") ||    '
'        isInNet(hostIP, "127.0.0.0", "255.0.0.0") ||   '
'        isInNet(hostIP, "169.254.0.0", "255.255.0.0") ||   '
'        isInNet(hostIP, "172.16.0.0", "255.240.0.0") ||    '
'        isInNet(hostIP, "192.0.2.0", "255.255.255.0") ||   '
'        isInNet(hostIP, "192.88.99.0", "255.255.255.0") || '
'        isInNet(hostIP, "192.168.0.0", "255.255.0.0") ||   '
'        isInNet(hostIP, "198.18.0.0", "255.254.0.0") ||    '
'        isInNet(hostIP, "224.0.0.0", "240.0.0.0") ||   '
'        isInNet(hostIP, "240.0.0.0", "240.0.0.0")) '
'        {  '
'           return "DIRECT";    '
'        }  '
'      }    '
'   }   \r\n    '
'    %s         '
'   '
'       '
'   return "DIRECT";    '
'}  '
)


class conf_base(object):
    def __init__(self, valid_fields, conf_dict):
        # each item in the _valid_fields is a tuple represents
        # (key, default_val, type, validate_regex, call_function)
        self._valid_fields = valid_fields
        self._conf = {}
        self.load(conf_dict)

    def load(self, conf_dict):
        for field in self._valid_fields:
            key      = field[0]
            dft_val  = field[1]
            val_type = field[2]
            vld_regx = field[3]
            func     = field[4]

            # More check can be made here
            if key in conf_dict:
                self._conf[key] = conf_dict[key] if func is None else func(conf_dict.get(key, dft_val))
                self._conf[key] = int(self._conf[key]) if val_type == 'int' else self._conf[key]
            elif dft_val is not None:
                self._conf[key] = dft_val if func is None else func(conf_dict.get(key, dft_val))


    def get_val(self, key):
        return self._conf[key]

    def __getitem__(self, key):
        return self.get_val(key)

    def set_val(self, key, val):
        self._conf[key] = val

    def __setitem__(self, key, val):
        self.set_val(key, val)

    def dict(self):
        return self._conf

class gen_conf(conf_base):
    _valid_fields = [
            #(key,              default_val,                type,       validate_regex,     call_function)
            ('download_dir',    '~/Downloads/youtube-dl',   'string',   '',                 expanduser),
            ('db_path',         '~/.conf/ydl_webui.db',     'string',   '',                 expanduser),
            ('root_dir',         '/data/v2           ',     'string',   '',                 expanduser),
            ('log_size',        10,                         'int',      '',                 None),
        ]

    def __init__(self, conf_dict={}):
        super(gen_conf, self).__init__(self._valid_fields, conf_dict)

class svr_conf(conf_base):
    _valid_fields = [
            #(key,              default_val,                type,       validate_regex,     call_function)
            ('host',            '127.0.0.1',                'string',   None,               None),
            ('port',            '30000',                    'string',   None,               None),
        ]

    def __init__(self, conf_dict={}):
        super(svr_conf, self).__init__(self._valid_fields, conf_dict)

class v2ray_conf(conf_base):
    _valid_fields = [
            #(key,              default_val,                type,       validate_regex,     call_function)
            ('proxy',           '',                       'string',   None,               None),
            ('format',          '',                       'string',   None,               None),
            ('ratelimit',       1048576,                    'int',      None,               None),
            ('outtmpl',         '',                       'string',   None,               None),
            ('global',          False,                      'bool',     None,               None),
        ]

    _task_settable_fields = set(['format'])

    def __init__(self, conf_dict={}):
        super(v2ray_conf, self).__init__(self._valid_fields, conf_dict)

    def merge_conf(self, task_conf_dict={}):
        ret = deepcopy(self.dict())
        for key, val in task_conf_dict.items():
            if key not in self._task_settable_fields or val == '':
                continue
            ret[key] = val

        return ret


    def get_filter_urls(self):
        keys=[]
        try:
            url_map = json.loads(self.get_val('outtmpl'))
            keys=list(url_map.keys())
        except Exception as e:
            logger.debug('url_map json load fail. %s'%e)

        return keys

    def make_pac_file(self,host,port_list):
        proxy_string = ''     
        url_function = """\r\n	if (    
    	    %s
        )   
        {   
            return "%s";    
        }   """
        try:
            url_map = json.loads(self.get_val('outtmpl'))
        except Exception as e:
            logger.debug('url_map json load fail. %s'%e)
        
        function_scripts = ''
        for item in port_list:
            proxy_string =''
            for it in item['list']:
                proxy_string =proxy_string +"HTTPS %s:%d;PROXY %s:%d;SOCKS %s:%d; "%(host,it['port'],host,it['port'],host,it['port'])

            filter_list=url_map[item['url']] 
            script_str = ''
            for it in filter_list:
                script_str=script_str+'(shExpMatch(host, "*%s*"))||'%it
            script_str=script_str+'false'    
            function_scripts = function_scripts + url_function%(script_str,proxy_string)

        return pac_script%(function_scripts)

class conf(object):

    _valid_fields = set(('v2ray', 'server', 'general'))

    v2ray_conf = None
    svr_conf = None
    gen_conf = None

    def __init__(self, conf_file, conf_dict={}, cmd_args={}):        
        self.conf_file = conf_file
        self.cmd_args = cmd_args
        self.load(conf_dict)

    def cmd_args_override(self):
        _cat_dict = {'host': 'server',
                    'port': 'server'}

        for key, val in self.cmd_args.items():
            if key not in _cat_dict or val is None:
                continue
            sub_conf = self.get_val(_cat_dict[key])
            sub_conf.set_val(key, val)

    def load(self, conf_dict):
        if not isinstance(conf_dict, dict):
            self.logger.error("input parameter(conf_dict) is not an instance of dict")
            return

        for f in self._valid_fields:
            if f == 'v2ray':
                self.v2ray_conf = v2ray_conf(conf_dict.get(f, {}))
            elif f == 'server':
                self.svr_conf = svr_conf(conf_dict.get(f, {}))
            elif f == 'general':
                self.gen_conf = gen_conf(conf_dict.get(f, {}))
        # override configurations by cmdline arguments
        self.cmd_args_override()

    def dict(self):
        d = {}
        for f in self._valid_fields:
            if f == 'v2ray':
                d[f] = self.v2ray_conf.dict()
            elif f == 'server':
                d[f] = self.svr_conf.dict()
            elif f == 'general':
                d[f] = self.gen_conf.dict()

        return d

    def save2file(self):
        if self.conf_file is not None:
            try:
                with open(self.conf_file, 'w') as f:
                    json.dump(self.dict(), f, indent=4)
            except PermissionError:
                return (False, 'permission error')
            except FileNotFoundError:
                return (False, 'can not find file')
            else:
                return (True, None)

    def get_val(self, key):
        if key not in self._valid_fields:
            raise KeyError(key)

        if key == 'v2ray':
            return self.v2ray_conf
        elif key == 'server':
            return self.svr_conf
        elif key == 'general':
            return self.gen_conf
        else:
            raise KeyError(key)

    def __getitem__(self, key):
        return self.get_val(key)
 