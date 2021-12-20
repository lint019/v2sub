#!/usr/bin/python3
# -*- coding: UTF-8 -*-

from node import Node
import base64
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


class V2ray(Node):
    uuid = ""
    alterId = 0
    network = ""
    camouflageType = ""
    camouflageHost = ""
    camouflagePath = ""
    camouflageTls = ""
    root_dir = "."
    proxy_port=0

    def __init__(
        self,        
        ip,
        port,
        remark,
        security,
        uuid,
        alterId,
        network,
        camouflageType,
        camouflageHost,
        camouflagePath,
        camouflageTls,
        root_dir=""
    ):
        super(V2ray, self).__init__(ip, port, remark, security)
        self.root_dir = root_dir
        self.uuid = uuid
        self.alterId = alterId
        self.network = network
        self.camouflageHost = camouflageHost
        self.camouflagePath = camouflagePath
        self.camouflageTls = camouflageTls
        self.camouflageType = camouflageType
        self._valid = False

    @property
    def valid(self):
        return self._valid

    @valid.setter
    def valid(self, value):
        self._valid = value

    def formatConfig0(self):
        v2rayConf = {
            "root_dir": self.root_dir,
            "remark": self.remark,
            "log": {
                "access": "./log/access.log",
                "error": "./log/error.log",
                "logLevel": "Verbose",
            },
            "inbounds": [
                {
                    "sniffing": {"enabled": True, "destOverride": ["tls", "http"]},
                    "port": 1080,
                    "listen": "127.0.0.1",
                    "protocol": "http",
                    "tag": "proxy",
                },
            ],
            "outbounds": [],
            "routing": {
                "strategy": "rules",
                "settings": {
                    "domainStrategy": "IPIfNonMatch",

                    "rules": [
                        {
                            "type": "field",
                            "ip": ["geoip:cn", "geoip:private"],
                            "outboundTag": "api",
                        },
                        {
                            "type": "field",
                            "outboundTag": "api",
                            "domain": ["localhost", "geosite:cn"],
                        },
                    ],
                },
            },
        }
        if self.network == "tcp" or self.network == "auto":
            # tcp下
            v2rayConf["outbounds"].append(
                {
                    "protocol": "vmess",
                    "settings": {
                        "vnext": [
                            {
                                "tag":self.uuid,
                                "address": self.ip,
                                "port": int(self.port),
                                "users": [
                                    {
                                        "id": self.uuid,
                                        "alterId": self.alterId,
                                        "security": self.security,
                                    }
                                ],
                            }
                        ]
                    },
                    "tag": "proxy",
                }
            )

        elif self.network == "kcp":
            # kcp 下
            v2rayConf["outbounds"].append(
                {
                    "protocol": "vmess",
                    "settings": {
                        "vnext": [
                            {
                                "tag":self.uuid,
                                "address": self.ip,
                                "port": int(self.port),
                                "users": [{"id": self.uuid, "alterId": self.alterId}],
                            }
                        ]
                    },
                    "streamSettings": {
                        "network": "kcp",
                        "kcpSettings": {
                            "mtu": 1350,
                            "tti": 50,
                            "uplinkCapacity": 12,
                            "downlinkCapacity": 100,
                            "congestion": False,
                            "readBufferSize": 2,
                            "writeBufferSize": 2,
                            "header": {
                                "type": self.camouflageType,
                            },
                        },
                    },
                    "tag": "out",
                }
            )
        elif self.network == "ws":
            # ws
            v2rayConf["outbounds"].append(
                {
                    "protocol": "vmess",
                    "settings": {
                        "vnext": [
                            {
                                "tag":self.uuid,
                                "address": self.ip,
                                "port": int(self.port),
                                "users": [{"id": self.uuid, "alterId": self.alterId}],
                            }
                        ]
                    },
                    "tag": "proxy",
                }
            )

        else:
            # h2
            v2rayConf["outbounds"].append(
                {
                    "protocol": "vmess",
                    "settings": {
                        "vnext": [
                            {
                                "address": self.ip,
                                "port": int(self.port),
                                "users": [{"id": self.uuid, "alterId": self.alterId}],
                            }
                        ]
                    },
                    "streamSettings": {
                        "network": "ws",
                        "security": self.camouflageTls,
                        "tlsSettings": {
                            "allowInsecure": True,
                        },
                        "httpSettings": {
                            "path": self.camouflagePath,
                            "host": [self.camouflageHost],
                        },
                    },
                    "tag": "proxy",
                }
            )

        return v2rayConf

    def formatConfig1(self):
        v2rayConf = {
            "root_dir": self.root_dir,
            "remark": self.remark,
            "log": {
                "access": "./log/access.log",
                "error": "./log/error.log",
                "logLevel": "Verbose",
            },
            "inbounds": [
                {
                    "sniffing": {"enabled": True, "destOverride": ["tls", "http"]},
                    "port": 1080,
                    "listen": "127.0.0.1",
                    "protocol": "http",
                    "tag": "proxy",
                },
            ],
            "outbounds": [],
            "routing": {
                "strategy": "rules",
                "settings": {
                    "domainStrategy": "IPIfNonMatch",
                    "balancers": [
                        {
                            "tag": "b1",
                            "selector": [
                                self.uuid,
                            ]
                        }
                        
                        ],
                    "rules": [
                        {
                            "type": "field",
                            "ip": ["geoip:cn", "geoip:private"],
                            "outboundTag": "api",
                        },
                        {
                            "type": "field",
                            "outboundTag": "api",
                            "domain": ["localhost", "geosite:cn"],
                        },                        
                        {
                            "type": "field",
                            "network": "tcp,udp",
                            "balancerTag": "b1"
                        }
                    ],
                },
            },
        }
        if self.network == "tcp" or self.network == "auto":
            # tcp下
            v2rayConf["outbounds"].append(
                {
                    "protocol": "vmess",
                    "settings": {
                        "vnext": [
                            {
                                "tag":self.uuid,
                                "address": self.ip,
                                "port": int(self.port),
                                "users": [
                                    {
                                        "id": self.uuid,
                                        "alterId": self.alterId,
                                        "security": self.security,
                                    }
                                ],
                            }
                        ]
                    },
                    "streamSettings": {"network": "tcp"},
                    "tag": "proxy",
                }
            )
            return v2rayConf
        elif self.network == "kcp":
            # kcp 下
            v2rayConf["outbounds"].append(
                {
                    "protocol": "vmess",
                    "settings": {
                        "vnext": [
                            {
                                "tag":self.uuid,
                                "address": self.ip,
                                "port": int(self.port),
                                "users": [{"id": self.uuid, "alterId": self.alterId}],
                            }
                        ]
                    },
                    "streamSettings": {
                        "network": "kcp",
                        "kcpSettings": {
                            "mtu": 1350,
                            "tti": 50,
                            "uplinkCapacity": 12,
                            "downlinkCapacity": 100,
                            "congestion": False,
                            "readBufferSize": 2,
                            "writeBufferSize": 2,
                            "header": {
                                "type": self.camouflageType,
                            },
                        },
                    },
                    "tag": "proxy",
                }
            )
            return v2rayConf
        elif self.network == "ws":
            # ws
            v2rayConf["outbounds"].append(
                {
                    "protocol": "vmess",
                    "settings": {
                        "vnext": [
                            {
                                "tag":self.uuid,
                                "address": self.ip,
                                "port": int(self.port),
                                "users": [{"id": self.uuid, "alterId": self.alterId}],
                            }
                        ]
                    },
                    "streamSettings": {
                        "network": "ws",
                        "security": self.camouflageTls,
                        "tlsSettings": {
                            "allowInsecure": True,
                        },
                        "wsSettings": {
                            "path": self.camouflagePath,
                            "headers": {"Host": self.camouflageHost},
                        },
                    },
                    "tag": "proxy",
                }
            )
            return v2rayConf
        else:
            # h2
            v2rayConf["outbounds"].append(
                {
                    "protocol": "vmess",
                    "settings": {
                        "vnext": [
                            {
                                "address": self.ip,
                                "port": int(self.port),
                                "users": [{"id": self.uuid, "alterId": self.alterId}],
                            }
                        ]
                    },
                    "streamSettings": {
                        "network": "ws",
                        "security": self.camouflageTls,
                        "tlsSettings": {
                            "allowInsecure": True,
                        },
                        "httpSettings": {
                            "path": self.camouflagePath,
                            "host": [self.camouflageHost],
                        },
                    },
                    "tag": "proxy",
                }
            )
            return v2rayConf
    def formatConfig(self):
        v2rayConf = {
            "root_dir": self.root_dir,
            "remark": self.remark,
            "log": {
                "access": "./log/access.log",
                "error": "./log/error.log",
                "logLevel": "Verbose",
            },
            "inbounds": [
                {
                    "sniffing": {"enabled": True, "destOverride": ["tls", "http"]},
                    "port": 1080,
                    "listen": "127.0.0.1",
                    "protocol": "http",
                    "tag":self.uuid,
                },
            ],
            "outbounds": [],
            "routing": {
                "domainStrategy": "IPIfNonMatch",                    
                "rules": [
                    {
                        "type": "field",
                        "ip": ["geoip:cn", "geoip:private"],
                        "outboundTag": "api",
                    },
                    {
                        "type": "field",
                        "outboundTag": "api",
                        "domain": ["localhost", "geosite:cn"],
                    },                        
                    
                ],
                
            },
        }
        self.add_outbound(v2rayConf["outbounds"],self)
        return v2rayConf


    def to_quantumult_url(self):
        tls = self.camouflageTls == "tls"
        ps = self.remark
        _type = self.camouflageType
        host = self.camouflageHost
        uuid = self.uuid
        port = self.port
        add = self.ip
        net = self.network
        path = self.camouflagePath
        str2 = ""
        if net == "http" or net == "ws":
            str2 = ',obfs={},obfs-path="{}"obfs-header="Host:{}"'.format(
                net, path, host
            )
        str1 = '{} = vmess,{},{},{},"{}",over-tls={},tls-host={},certificate=1'.format(
            ps, add, port, _type, uuid, tls, host
        )
        info = str1 + str2
        logger.debug("to_quantumult_url_origin -- %s" % info)
        vmess_info = "vmess://{}".format(
            base64.b64encode(info.encode("utf8")).decode("utf8")
        )
        logger.debug("to_quantumult_url -- %s" % vmess_info)
        return vmess_info

    def to_vmess_url(self, uuid, server, port, cipher, obfs, ws_path, tls, client_type):
        if client_type == "shadowrocket":
            vmess_info = "{}:{}@{}:{}".format(cipher, uuid, server, port)
            vmess_info_b64 = (
                base64.b64encode(vmess_info.encode("ascii"))
                .decode("ascii")
                .replace("=", "")
            )
            return "vmess://{}?path={}&obfs={}&tls={}".format(
                vmess_info_b64, ws_path, obfs, tls
            )
        elif client_type == "bifrost":
            ws_path = "%3D{}".format(ws_path.replace("/", "%252F"))
            vmess_info = "bfv://{}:{}/vmess/1?rtype=lanchinacnsite&dns=8.8.8.8&tnet=ws&tsec=tls&ttlssn={}&mux=0&uid={}&aid=64&sec=auto&ws=path{}%26headers%3D#{}".format(
                server, port, server, uuid, ws_path, server
            )

            print(vmess_info)
            print(ws_path)
            return vmess_info
        else:
            raise NameError("Unknown type")
    def proxy_info(self):
        return {
            "tag":self.uuid,
            "address": self.ip,
            "port": int(self.port),
            "users": [{"id": self.uuid, "alterId": self.alterId}]
        };
    

    def add_outbound(self,out,node):
        if node.network == "tcp" or node.network == "auto":
                # tcp下
            out.append(
                {
                    "protocol": "vmess",
                    "settings": {
                        "vnext": [
                            {
                                "address": node.ip,
                                "port": int(node.port),
                                "users": [
                                    {
                                        "id": node.uuid,
                                        "alterId": node.alterId,
                                        "security": node.security,
                                    }
                                ],
                            }
                        ]
                    },
                    "streamSettings": {"network": "tcp"},
                    "tag":node.uuid,
                }
            )
            
        elif node.network == "kcp":
            # kcp 下
            out.append(
                {
                    "protocol": "vmess",
                    "settings": {
                        "vnext": [
                            {
                                "address": node.ip,
                                "port": int(node.port),
                                "users": [{"id": node.uuid, "alterId": node.alterId}],
                            }
                        ]
                    },
                    "streamSettings": {
                        "network": "kcp",
                        "kcpSettings": {
                            "mtu": 1350,
                            "tti": 50,
                            "uplinkCapacity": 12,
                            "downlinkCapacity": 100,
                            "congestion": False,
                            "readBufferSize": 2,
                            "writeBufferSize": 2,
                            "header": {
                                "type": node.camouflageType,
                            },
                        },
                    },
                    "tag":node.uuid,
                }
            )
            
        elif node.network == "ws":
            # ws
            out.append(
                {
                    "protocol": "vmess",
                    "settings": {
                        "vnext": [
                            {
                                "address": node.ip,
                                "port": int(node.port),
                                "users": [{"id": node.uuid, "alterId": node.alterId}],
                            }
                        ]
                    },
                    "streamSettings": {
                        "network": "ws",
                        "security": node.camouflageTls,
                        "tlsSettings": {
                            "allowInsecure": True,
                        },
                        "wsSettings": {
                            "path": node.camouflagePath,
                            "headers": {"Host": node.camouflageHost},
                        },
                    },
                    "tag":node.uuid,
                }
            )
            
        else:
            # h2
            out.append(
                {
                    "protocol": "vmess",
                    "settings": {
                        "vnext": [
                            {
                                "address": node.ip,
                                "port": int(node.port),
                                "users": [{"id": node.uuid, "alterId": node.alterId}],
                            }
                        ]
                    },
                    "streamSettings": {
                        "network": "ws",
                        "security": node.camouflageTls,
                        "tlsSettings": {
                            "allowInsecure": True,
                        },
                        "httpSettings": {
                            "path": node.camouflagePath,
                            "host": [node.camouflageHost],
                        },
                    },
                    "tag":node.uuid,
                }
            )

    def add_balance0(self,services):
        config = self.formatConfig()
        for item in services:
            config["outbounds"][0]["settings"]["vnext"].append(item.proxy_info())
            config["routing"]["settings"]["balancers"][0]["selector"].append(item.uuid)
        return config
    def add_balance(self,services):
        config = self.formatConfig()
        balance =[{
                    "tag": "b1",
                    "selector": [
                        
                    ]
                }]
        config["routing"]["balancers"]=balance
        for item in services:
            self.add_outbound(config["outbounds"],item)
            config["routing"]["balancers"][0]["selector"].append(item.uuid)
                        
        rule = {
            "type": "field",
            "network": "tcp,udp",
            "balancerTag": "b1"
        }
        config["routing"]["rules"].append(rule)
        return config
