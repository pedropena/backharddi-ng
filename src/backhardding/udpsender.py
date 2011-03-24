'''
Created on 05/05/2010

@author: Pedro Pena Perez
'''
from twisted.internet import reactor
from twisted.python import log
from twisted.protocols.basic import FileSender
from zope.interface import implements
from twisted.internet import interfaces
from twisted.internet.protocol import ProcessProtocol
import backhardding.service
import glob

UDPSENDER = '/usr/bin/udp-sender'
PORTBASE = 9000

class UDPSender():
    active = {} #Mapa de listas de hilos udpsender. La llave del mapa es el directorio del backup.
    def __init__( self, backup, address, imgs, minclients ):
        self.backup = backup
        self.address = address
        self.imgs = imgs.__iter__()
        self.serving = 0 
        self.requests = 0
        self.participants = 0
        self.minclients = int(minclients)
        self.maxwait = 0
        self.port = PORTBASE
        active_ports = [ udpsender.port for backup in UDPSender.active.itervalues() for udpsender in backup ]
        while self.port in active_ports or backhardding.service.portInUse(self.port + 1):
            self.port += 2
        self.set_active()
    
    def start_next(self):
        try:
            self.finish = False
            pp = UDPSenderProtocol( self, self.imgs.next() )
            self.log( 'UDP-Sender levantado' )
            reactor.spawnProcess( pp, UDPSENDER,  [ UDPSENDER, "--nokbd", "--half-duplex", "--retries-until-drop", "50", "--interface", str( self.address ), "--portbase", str( self.port ), "--min-receivers", str( self.minclients ), "--max-wait", str( self.maxwait ), "--stat-period", "2000" ] )
            self.maxwait = 240
        except StopIteration:
            self.unset_active()

    def set_active( self ):
        if self.backup in UDPSender.active:
            UDPSender.active[self.backup].append( self )
        else:
            UDPSender.active[self.backup] = [ self ]

    def unset_active( self ):
        try:
            log.msg('Quitando %s de activos en %s' % (str(self), self.backup.encode('utf-8')))
            UDPSender.active[self.backup].remove( self )
        except:
            log.msg('%s no esta activo' % str(self))

    def log( self, msg ):
        log.msg( '%-25s: file[%s] puerto[%d] interfaz[%s] peticiones[%d] clientesmin[%d] participantes[%d]\n' % ( msg, self.backup.encode('utf-8'), self.port, str( self.address ), self.requests, int( self.minclients ), self.participants ))

class BackharddiFileSender( FileSender ):
    implements(interfaces.IProducer)
    CHUNK_SIZE = 2 ** 16
    lastSent = ''
    deferred = None
    def resumeProducing(self):
        chunk = ''
        if self.file:
            chunk = self.file.read(self.CHUNK_SIZE)
        if not chunk:
            self.file = None
            self.consumer.unregisterProducer()
            if self.deferred:
                self.deferred.callback(self.lastSent)
                self.deferred = None
            return

        self.consumer.write(chunk)

class UDPSenderProtocol( ProcessProtocol ):
    def __init__(self, udpsender, img):
        self.udpsender = udpsender
        self.img = img

    def connectionMade(self):
        self.input = glob.glob( self.img + ".??" )
        self.input.sort()
        self.transferNextFile(None, self.input.__iter__())

    def transferNextFile(self, last, i):
        producer = BackharddiFileSender()
        try:
            d = producer.beginFileTransfer(open(i.next()), self.transport.pipes[0])
            d.addCallback(self.transferNextFile, i).addErrback(self.transferAbort)
        except StopIteration:
            self.transport.closeStdin()
    
    def transferAbort(self, exception):
        self.udpsender.finish = False
        self.udpsender.unset_active()
        self.udpsender.log("Transferencia abortada")

    def errReceived(self, data):
        lines = data.split("\n")
        for line in lines:
            if not line:
                continue
            elif line[:5] == "bytes":
                self.udpsender.log(line.strip())
                continue
            elif line[:7] == "Timeout":
                self.udpsender.log(line.strip())
                continue
            elif line.find( "Starting transfer" ) >= 0:
                self.udpsender.serving = 1
                self.udpsender.log( 'Iniciando transferencia' )
            elif line.find( "Transfer complete." ) >= 0:
#                self.udpsender.minclients = self.udpsender.participants
                self.udpsender.finish = True
                self.udpsender.log( 'Transferencia finalizada' )
                self.udpsender.log(line.strip())
            elif line.find( "New connection" ) >= 0:
                self.udpsender.participants += 1
                self.udpsender.log( 'Nueva conexion' )
                self.udpsender.log(line.strip())
            elif line.find( "Dropping client" ) >= 0:
                self.udpsender.log( 'Tiempo de espera agotado' )
                self.udpsender.minclients -= 1
                self.udpsender.log(line.strip())
            elif line.find( "Disconnecting" ) >= 0:
                self.udpsender.participants -= 1
                self.udpsender.log( 'Desconexion' )
                self.udpsender.log(line.strip())
            else:
                self.udpsender.log( line.strip() )

    def processEnded(self, reason):
        if reason.value.exitCode == 0 and self.udpsender.finish:
            reactor.callInThread( self.udpsender.start_next )