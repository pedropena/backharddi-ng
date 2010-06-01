'''
Created on 17/05/2010

@author: Pedro Pena Perez
'''

from twisted.internet import reactor
from twisted.python import log

class Host():
    hosts = {}
    groups = {}
    livemonitor = None
    lockupdates = False
    @classmethod
    def delFromGroup(cls, name, hosts):
        if name in cls.groups:
            for host in hosts:
                if host in cls.groups[name]['hosts']:
                    cls.groups[name]['hosts'].remove(host)
                    cls.hosts[host].group = None
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
    def unlockupdates(cls):
        log.msg('Desbloqueando updates')
        cls.lockupdates = False
    @classmethod
    def sendStatus(cls):
        cls.status = {
         'groups': [{'id': host.ip, 'name': host.ip, 'ip': host.ip, 'status': host.status, 'group': host.group, 'msg': host.msg} for host in cls.hosts.values() if host.group], 
         'clients': [{'id': host.ip, 'name': host.ip, 'ip': host.ip, 'status': host.status, 'group': None, 'msg': host.msg} for host in cls.hosts.values() if not host.group]
         }
        cls.livemonitor.update(cls.status)
#        if not Host.lockupdates:
#            log.msg('Bloqueando updates')
#            Host.lockupdates = True
#            self.livemonitor.update({'groups': [], 'clients': [{'id': host.ip, 'name': host.ip, 'ip': host.ip, 'status': host.status, 'group': None } for host in self.hosts.values()]})
#            reactor.callLater(2, self.unlockupdates)
    def __init__(self, request):
        self.ip = request.client.host
        self.hosts[self.ip] = self
        self.request = request
        self.setTimeout(30)
        self.group = None
        self.setStatus("Conectado")
    def setTimeout(self,timeout,cmd='true'):
        self.timeout = reactor.callLater(timeout, self.command, cmd)
    def command(self, cmd):
        self.request.write(cmd)
        self.request.finish()
        if self.timeout.active():
            self.timeout.cancel()
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
    def setStatus(self, status, msg=None):
        self.status = status
        if msg or not hasattr(self, 'msg'):
            self.msg = msg
        self.sendStatus()
