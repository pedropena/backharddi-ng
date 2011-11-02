'''
Created on 17/05/2010

@author: Pedro Pena Perez
'''

from twisted.internet import reactor
from twisted.python import log

def map_host_name(ip)
    return ip

class Host():
    hosts = {}
    groups = {}
    livemonitor = None
    has_messages = False
    @classmethod
    def delFromGroup(cls, name, hosts):
        if name in cls.groups:
            for host in hosts:
                if host in cls.groups[name]['hosts']:
                    cls.groups[name]['hosts'].remove(host)
                    cls.hosts[host].group = None
        cls.sendStatus()
    @classmethod
    def delHost(cls, hosts):
        for host in hosts:
            if host in cls.hosts:
                del cls.hosts[host]
        cls.sendStatus()
    @classmethod
    def addToGroup(cls, name, hosts=None, config=None):
        if name in cls.groups:
            for host in hosts:
                if host not in cls.groups[name]['hosts']:
                    cls.groups[name]['hosts'].append(host)
            if config:
                cls.groups[name]['config'] = config
        else:
            cls.groups[name] = {'hosts': hosts, 'config': config}
        for host in hosts:
            cls.hosts[host].group = name
        cls.sendStatus()
    @classmethod
    def sendStatus(cls):
        cls.status = [{'id': host.ip, 'name': host.name, 'ip': host.ip, 'status': host.status, 'group': host.group, 'msg': host.msg} for host in cls.hosts.values()]
        cls.livemonitor.update(cls.status)
        Host.has_messages = False
    def __init__(self, request):
        self.ip = request.client.host
        self.name = map_host_name(self.ip)
        self.hosts[self.ip] = self
        self.request = request
        self.deferred_command(30)
        self.group = None
        self.setStatus("Conectado")
    def deferred_command(self,timeout,cmd='true'):
        self._deferred_command = reactor.callLater(timeout, self.command, cmd)
    def command(self, cmd):
        self.request.write(cmd)
        self.request.finish()
        if self._deferred_command.active():
            self._deferred_command.cancel()
        self.setStatus("Desconectado")
    def __str__(self):
        if self.msg:
            return "%s %s: %s" % (self.ip, self.status, self.msg)
        else:
            return "%s %s" % (self.ip, self.status)
    def __repr__(self):
        if self.msg:
            return "%s: %s" % (self.status, self.msg)
        else:
            return "%s" % (self.status)
    def setStatus(self, status, msg=None, interactive=False):
        self.status = status
        if msg or not hasattr(self, 'msg'):
            self.msg = msg
        Host.has_messages = True
        if interactive:
            self.sendStatus()
