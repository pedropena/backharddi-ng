PORT = 4600
HTTPPORT = 9091
ROOT = '/var/lib/backharddi-ng'
TFTPROOT = '/var/lib/tftpboot/backharddi-ng'

import sys
sys.path.insert(0,'/usr/share/backharddi-ng/python/src')

from twisted.application import service
from twisted.application import internet
from twisted.web import server, resource
from twisted.runner.procmon import ProcessMonitor
from backhardding.service import Service
from backhardding.monitor import setupSite, LiveMonitor
from twisted.conch import manhole_tap
from morbid.morbid import StompFactory

application = service.Application("Backharddi NG")

livemonitor = LiveMonitor()
monitor = internet.TCPClient('localhost', 61613, livemonitor)
monitor.setServiceParent(application)

procmon = ProcessMonitor()
procmon.setServiceParent(application)

service = Service(procmon, livemonitor, ROOT, TFTPROOT)
service.setServiceParent(application)

ws = server.Site(resource.IResource(service))
internet.TCPServer( PORT, ws ).setServiceParent(application)

manhole = manhole_tap.makeService({
    'namespace': {'service': service},
    'telnetPort': None,
    'sshPort': 'tcp:%d:interface=127.0.0.1' % (PORT+1),
    'passwd': '/etc/backharddi-ng/passwd'
                                   })
manhole.setServiceParent(application)

stomp = StompFactory()
stompsrv = internet.TCPServer( 61613 , stomp)
stompsrv.setServiceParent(application)

webfrontend = setupSite(service)
httpsrv = internet.TCPServer( HTTPPORT, webfrontend)
httpsrv.setServiceParent(application)
