# -*- coding: utf-8
'''
Created on 19/05/2010

@author: Pedro Pena Perez
'''
from twisted.web import static, server, resource
import os
import backhardding
from stompservice import StompClientFactory
from orbited import json
from twisted.python import log
from backhardding.host import Host
import re

CHANNEL_NAME = '/livemonitor'

class LiveMonitor(StompClientFactory):    
    def update(self, data):
        if hasattr(self, 'send'):
            log.msg("Enviando estado al monitor\n")
            self.send(CHANNEL_NAME, json.encode(data))

class BackharddiNGControl(resource.Resource):
    def __init__(self, backend):
        resource.Resource.__init__(self)
        self.backend = backend
    
    def getChild(self, name, request):
        if hasattr(self, name):
            return self
        return resource.Resource.getChild(self, name, request)

    def render_GET(self, request):
        if hasattr(self, request.prepath[1]):
            return getattr(self, request.prepath[1])(**request.args)
    
    render_POST = render_GET
    
    def json_status(self, _dc=None):
        if hasattr(Host, 'status'):
            return json.encode(Host.status)
        else:
            return json.encode([])

    def to_secure_string(self, dir):
        paths = dir.split('/')
        pattern = re.compile('[^a-zA-Z0-9ñÑçÇáéíóúàèìòù\+\.,:;-]')
        result = []
        for path in paths:
            p = re.sub(pattern, '_', path)
            if len(result) < len(paths) - 1:
                p = '+%s' % p
            result.append(p)
        return '/'.join(result)

    def group_config(self, hosts=[''], name=[''], modo=['rest'], reboot=None, shutdown=None, backup=[''], launch=None):
        cmd = "backharddi/modo=%s backharddi/imagenes=/target/%s" % (modo[0], self.to_secure_string(backup[0]))
        if reboot:
            cmd = '%s backharddi/reboot=' % cmd
        if shutdown:
            cmd = '%s shutdown' % cmd
        self.backend.do_add_to_group(name[0],hosts[0].split(','),cmd)
        if launch:
            self.backend.do_launch_group(name[0])
        return ''
    
    def group_launch(self, name):
        self.backend.do_launch_group(name[0])
        return ''

    def del_from_group(self, name, hosts):
        self.backend.do_del_from_group(name[0], hosts)
        return ''
        
    def del_from_gui(self, hosts):
        self.backend.do_del_host(hosts)
        return ''

    def sync_clients(self, _dc=None):
	self.backend.do_sync_hosts()
	return ''

    def reboot(self, hosts):
        for host in hosts:
            self.backend.do_reboot(host)
        return ''

    def shutdown(self, hosts):
        for host in hosts:
            self.backend.do_shutdown(host)
        return ''
    
    def set_boot(self, boot):
        self.backend.do_set_boot(boot[0])
        return ''
    
    def tree(self, node):
        if node[0] == 'root':
            n = '/target'
        else:
            n = node[0]
        list = self.backend.list_partition([n])
        r = []
        for l in list.splitlines():
            if l[0] == '+':
                r.append({'id': "%s/%s" % (n,l), 'text': l[1:].replace('_',' ')})
            else:
                r.append({'id': "%s/%s" % (n,l), 'text': l.replace('_',' '), 'leaf': True})
        return json.encode(r)
    
def setupSite(backend):
    from orbited import logging, config
    config.map['[access]'][('localhost',61613)] = ['*']
    logging.setup(config.map)
    import orbited.start

    orbited.start.logger = logging.get_logger('orbited.start')

    root = static.File(os.path.dirname(backhardding.__file__) + "/html")
    root.putChild('control', BackharddiNGControl(backend))
    static_files = static.File(os.path.dirname(orbited.__file__) + "/static")
    root.putChild('static', static_files)
    orbited.start._setup_protocols(root)
    site = server.Site(root,'/dev/null')
    return site
