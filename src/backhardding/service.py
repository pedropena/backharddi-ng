'''
Created on 03/05/2010

@author: Pedro Pena Perez
'''
from twisted.application import service
from twisted.python import components, log
from zope.interface import Interface, implements
from twisted.web import resource
import dbus
from dbus.mainloop.glib import DBusGMainLoop

from backhardding.partition import Partition
import os
import re
import cStringIO
import tarfile
from twisted.internet import reactor, error
from backhardding.udpsender import UDPSender
from twisted.internet.protocol import Protocol, Factory
from twisted.internet import utils
import shutil
from twisted.web.server import NOT_DONE_YET
from backhardding.host import Host

DBusGMainLoop(set_as_default=True)
TFTP_TEMPLATE = '''DEFAULT menu.c32
TIMEOUT 30
MENU TITLE BACKHARDDI-NG

LABEL Backharddi NG Net
MENU DEFAULT
KERNEL linux-backharddi-ng
APPEND vga=788 video=vesa:ywrap,mtrr quiet backharddi/medio=net %s initrd=minirt-backharddi-ng.gz --

LABEL Backharddi NG HD
KERNEL linux-backharddi-ng
APPEND vga=788 video=vesa:ywrap,mtrr quiet backharddi/medio=hd-media initrd=minirt-backharddi-ng.gz --

LABEL Disco Duro Local
LOCALBOOT 0
'''

def toUnicode(s, encoding='utf-8'):
    return s if isinstance(s, unicode) else s.decode(encoding)

class IService(Interface):
    def listBackupPartitions():
        """Devuelve una lista con todas las particiones de backup (ext3 o ext4 con etiqueta "backharddi")
        encontradas en el sistema"""
        
class WebService(resource.Resource):
    def __init__(self, service):
        resource.Resource.__init__(self)
        self.service = service
        self.putChild("", self)
    
    def getChild(self, name, request):
        if hasattr(Service, name) or hasattr(Service, 'request_' + name):
            return self
        return resource.Resource.getChild(self, name, request)

    def render_GET(self, request):
        if hasattr(self.service, request.prepath[0]):
            return getattr(self.service, request.prepath[0])(**request.args)
        elif hasattr(self.service, 'request_' + request.prepath[0]):
            return getattr(self.service, 'request_' + request.prepath[0])(request,**request.args)

components.registerAdapter(WebService, IService, resource.IResource)

class UploadPackedMetadataProtocol(Protocol):
    MAXSIZE = 2 ** 24
    def connectionMade(self):
        self.size = 0
        self.data = ""
    
    def dataReceived(self, data):
        self.size += len(data)
        if self.size > self.MAXSIZE:
            log.msg( "PackedMetadata > MAXSIZE" )
            self.transport.loseConnection()
        else:
            self.data += data
    
    def connectionLost(self, reason):
	log.msg( "Subidos %d bytes" % self.size )
        self.factory.unpack(self.data)
        
class UploadPackedMetadataFactory(Factory):
    SEP = '***BACKHARDDINGPACK***'
    protocol = UploadPackedMetadataProtocol
    def unpack(self, data):
        chunks = data.split(self.SEP)
        while True:
            try:
                chunkdata = chunks.pop()
                chunkname = chunks.pop()
            except:
                break
            absname = os.path.join(self.base,*chunkname.decode('utf-8').split(os.sep)[2:])
            try:
                os.makedirs(os.path.dirname(absname), 0755)
            except:
                pass
            open(absname,'w').write(chunkdata)
	self.port.stopListening()
            
class UploadImgProtocol(Protocol):

    SPLITSIZE = 680 * 2 ** 20
    
    def openFds(self):
        self.size = 0
        if self.fd1:
            os.close(self.fd1)
            self.fd1 = self.fd2
        else:
            self.fd1 = os.open(self.factory.filename + ".%02d" % self.splitcount, os.O_CREAT | os.O_WRONLY | os.O_NONBLOCK, 0755)
        self.splitcount += 1
        self.fd2 = os.open(self.factory.filename + ".%02d" % self.splitcount, os.O_CREAT | os.O_WRONLY | os.O_NONBLOCK, 0755)

    def connectionMade(self):
        self.splitcount = 0
        self.fd1 = None
        self.fd2 = None
        self.openFds()
        
    def connectionLost(self, reason):
        os.close(self.fd1)
        os.close(self.fd2)
        os.unlink(self.factory.filename + ".%02d" % (self.splitcount))

    def dataReceived(self, data):
        bytes = os.write(self.fd1, data[:min( len(data), self.SPLITSIZE - self.size )] )
        self.size += bytes
        if self.size == self.SPLITSIZE:
            self.openFds()
        if not bytes == len(data):
            bytes = os.write(self.fd1, data[bytes:])
            self.size += bytes

class Service(service.Service):
    implements(IService)
    FILES = ['cmdline', 'device', 'mbr', 'model', 'pt', 'size', 'visuals', 'bootable',  'compresion', 'detected_filesystem', 'img', 'path', 'view', 'visual_filesystem', 'visual_mountpoint', 'cmosdump', 'postmaster', 'premaster', 'sti', 'ntfsclone', 'partclone' ]

    def __init__(self, procmon=None, livemonitor=None, root='/var/lib/backharddi-ng', tftproot='/var/lib/tftpboot', tftprootsuffix=None):
        self.procmon = procmon
        self.livemonitor = livemonitor
        self.tftproot = tftproot
        self.tftpcfgdir = tftproot + os.sep + tftprootsuffix if tftprootsuffix else tftproot
        self.root = root
        self.tftpcfgfiles = []

    def startService(self):
        log.msg('Iniciando servicio...')
        self.bngparts = [ Partition( None, self.root, True ) ]
        self.hosts = Host.hosts
        self.groups = Host.groups
        Host.livemonitor = self.livemonitor
        reactor.callWhenRunning(self.initHal)
        reactor.callWhenRunning(self.scanLVM)
        reactor.callWhenRunning(self.startTftp)
        reactor.callWhenRunning(self.startProxyDhcp)
        reactor.callWhenRunning(self.sendStatus)
        service.Service.startService(self)

    def sendStatus(self, timeout=2):
        if Host.has_messages:
            log.msg('Enviando estado al monitor')
            Host.sendStatus()
        self.send_status = reactor.callLater(timeout, self.sendStatus)

    def processLabel(self, result, lv):
        label, err, code = result
        if code == 0 and label.strip() == 'backharddi':
            lv['e2label'] = label.strip()
            part = Partition(lv)
            self.bngparts.append(part)
            part.mount(self.root + os.sep + part.name)

    def processLVM(self, result):
        for slv in result.split('--- Logical volume ---'):
            lv = {}
            for line in slv.split('\n'):
                key = line[:25].strip()
                value = line[25:].strip()
                if key:
                    lv[key] = value
            if 'LV Name' in lv:
                output = utils.getProcessOutputAndValue('/sbin/e2label', [lv['LV Name']])
                output.addCallback(self.processLabel, lv)
    
    def scanLVM(self):
        result = utils.getProcessOutput('/sbin/lvdisplay')
        result.addCallback(self.processLVM)

    def initHal(self):
        log.msg('Conectando a HAL...')
        bus = dbus.SystemBus()
        halmanager = bus.get_object ("org.freedesktop.Hal", "/org/freedesktop/Hal/Manager")
        self.hal = dbus.Interface(halmanager, "org.freedesktop.Hal.Manager")
        volumes = self.hal.FindDeviceByCapability("volume")
        for vol_uri in volumes:
            vol = bus.get_object ("org.freedesktop.Hal", vol_uri)
            vol = dbus.Interface(vol, "org.freedesktop.Hal.Device")
            vol = vol.GetAllProperties()
            if vol['volume.fstype'] in ['ext3', 'ext4'] and vol['volume.label'] in ["backharddi"]:
                part = Partition(vol)
                self.bngparts.append(part)
                part.mount(self.root + os.sep + part.name)

    def stopService(self):
        service.Service.stopService(self)
        if self.send_status.active():
            self.send_status.cancel()
        self.stopProxyDhcp()
        self.stopTftp()
        log.msg('Parando servicio...')
        for part in self.bngparts:
            part.umount()
                
    def listBackupPartitions(self):
        return "\n".join([str(part) for part in self.bngparts])
    
    def listPartition(self, dir=['/target']):
        backups = []
        backupdirs = []
        dir = [toUnicode(dir[0])]
        part = self.bngparts[0]
        if part.mountdir:
            absdir = os.path.join(part.mountdir,*dir[0].split(os.sep)[2:])
            try:
                paths = os.listdir(absdir)
            except os.error:
                paths = []
            for path in paths:
                abspath = os.path.join(absdir,path)
                if os.path.isdir(abspath):
                    try:
                        paths2 = os.listdir(abspath)
                    except os.error:
                        paths2 = []
                    for path2 in paths2:
                        if re.match('^=dev=',path2):
                            backups.append(path)
                            break
                    if path[0] == '+':
                        backupdirs.append(path)
        return "\n".join(backupdirs + backups).encode('utf-8')

    def getBackupMetadata(self, backup=['']):
        io = cStringIO.StringIO()
        backup = [toUnicode(backup[0])]
        part = self.bngparts[0]
        if part.mountdir:
            absbackup = os.path.join(part.mountdir,*backup[0].split(os.sep)[2:])

            tar = tarfile.open(mode="w:gz",fileobj=io)
            
            for root, dirs, files in os.walk(absbackup):
                for dir in dirs:
                    if not re.match('^=dev=',dir) and not re.match('[0-9]*-[0-9]*',dir):
                        dirs.remove(dir)
                for file in files:
                    if file in self.FILES:
                        absf = os.path.join(root, file)
                        filename = os.sep.join(absf.split(os.sep)[part.mountdir.count(os.sep)+1:])
                        tar.add(absf,filename)
                    elif file == 'img.00' and 'detected_filesystem' in files:
                        if 'linux-swap' in open( root + '/detected_filesystem' ).read():
                            absf = os.path.join(root, file)
                            filename = os.sep.join(absf.split(os.sep)[3:])
                            tar.add(absf,filename)
            tar.close()
        return io.getvalue()

    def putBackupMetadata(self):
        putfactory = UploadPackedMetadataFactory()
        putfactory.base = self.bngparts[0].mountdir
        for portn in xrange(8000,8999):
            try:
                putfactory.port = reactor.listenTCP(portn, putfactory)
            except error.CannotListenError:
                continue
            else:
                return str(portn)        
    
    def put(self, file=['']):
        file = [toUnicode(file[0])]
        if os.path.basename(file[0]) != 'img':
            return ""
        absfile = os.path.join(self.bngparts[0].mountdir,*file[0].split(os.sep)[2:])
        absdir = os.path.dirname(absfile)
        try:
            os.makedirs(absdir)
        except:
            pass
        putfactory = Factory()
        putfactory.protocol = UploadImgProtocol
        putfactory.filename = absfile.encode('utf-8')
        for portn in xrange(8000,8999):
            try:
                reactor.listenTCP(portn, putfactory)
            except error.CannotListenError:
                continue
            else:
                return str(portn)

    def list_imgs( self, backup ):
        imgs = []
        for root, dirs, files in os.walk( backup ):
            if 'img.00' in files and 'detected_filesystem' in files:
                if not 'linux-swap' in open( root + '/detected_filesystem' ).read():
                    imgs.append( root + '/img' )
        imgs.sort()
        return imgs

    def waiting( self, backup, address ):
        if backup in UDPSender.active:
            for udpsender in UDPSender.active[backup]:
                if udpsender.address == address and not udpsender.serving:
                    return udpsender

    def request_get(self, request, backup=[''], minclients=[1]):
        backup = [toUnicode(backup[0])]
        address = request.getHost().host
        if not minclients[0]:
            minclients=[1]
        part = self.bngparts[0]
        if part.mountdir:
            absbackup = os.path.join(part.mountdir,*backup[0].split(os.sep)[2:])
            udpsender = self.waiting( absbackup, address )
            if not udpsender:
                imgs = self.list_imgs( absbackup ) 
                udpsender = UDPSender( absbackup, address, imgs, minclients[0] )
                reactor.callInThread( udpsender.start_next )
            udpsender.requests += 1
        return str(udpsender.port)
    
    def request_command(self, request):
        if request.client.host in self.hosts:
            self.hosts[request.client.host].request = request
            self.hosts[request.client.host].deferred_command(30)
            if self.hosts[request.client.host].status == 'Desconectado':
                self.hosts[request.client.host].setStatus('Conectado', interactive=True)
        else:
            Host(request)
        return NOT_DONE_YET
    
    def do_command(self, host, cmd):
        if host in self.hosts:
            self.hosts[host].command(cmd)
            return "Ok"
        else:
            return "Host %s no encontrado" % host
    
    def do_add_to_group(self, name, hosts=None, config=None):
        Host.addToGroup(name, hosts, config)
        
    def do_del_from_group(self, name, hosts):
        Host.delFromGroup(name, hosts)
        
    def do_launch_group(self, name):
        for host in self.groups[name]['hosts']:
            self.do_command(host, 'backharddi_do %s backharddi/net/minclients=%d' % (self.groups[name]['config'], len(self.groups[name]['hosts'])))
            
    def request_status(self, request, status, msg=[None]):
        if request.client.host in self.hosts:
            if not self.hosts[request.client.host].group:
                log.msg('Status sin grupo')
                self.do_add_to_group('Grupo %d' % (len(self.groups) + 1), [request.client.host])
            self.hosts[request.client.host].setStatus(status[0], msg[0])
            if msg[0] == 'Completado':
                def reboot():
                    group = self.hosts[request.client.host].group
                    if self.groups[group]['config'] and 'reboot' in self.groups[group]['config']:
                        log.msg('Reiniciando %s' % request.client.host)
                        self.do_command(request.client.host,'reboot')
                reboot()
        else:
            raise Exception("Se ha enviado estado desde un Host inexistente")
        return ""

    def do_status(self, host):
        return "%s" % self.hosts[host]

    def do_ssh(self, host):
        reactor.callInThread( lambda: os.system('gnome-terminal -e "sshpass -p root ssh -o stricthostkeychecking=no -o UserKnownHostsFile=/dev/null installer@%s"' % host))

    def do_set_boot(self, boot):
        for file in self.tftpcfgfiles:
            cfg = open(self.tftpcfgdir + os.sep + file).read()
            f = open(self.tftpcfgdir + os.sep + file,'w')
            f.write(cfg.replace('\nMENU DEFAULT','').replace('LABEL %s' % boot, 'LABEL %s\nMENU DEFAULT' % boot ))
            f.close()
            
    def startTftp(self):
        import netifaces
        import ipaddr
        ifaces = []
        for iface in netifaces.interfaces():
            if iface == 'lo':
                continue
            addresses = netifaces.ifaddresses(iface)
            if 2 in addresses:
                for address in addresses[2]:
                    if 'addr' in address:
                        ifaces.append({ 'iface': iface, 'addr': ipaddr.IPNetwork( "%s/%s" % (address['addr'],address['netmask']))})
                        break
         
        os.makedirs(self.tftpcfgdir + os.sep + 'pxelinux.cfg')
        os.chmod(self.tftpcfgdir,0755)
        os.chmod(self.tftpcfgdir + os.sep + 'pxelinux.cfg',0755)
        self.tftpcfgfiles.append('pxelinux.cfg' + os.sep + 'default')
        open(self.tftpcfgdir + os.sep + 'pxelinux.cfg' + os.sep + 'default', 'w').write( TFTP_TEMPLATE % '')
        os.chmod(self.tftpcfgdir + os.sep + 'pxelinux.cfg' + os.sep + 'default',0666)
        
        for address in ifaces:
            filename = ('%X' % address['addr'])[:address['addr'].prefixlen/4]
            self.tftpcfgfiles.append('pxelinux.cfg' + os.sep + filename)
            open(self.tftpcfgdir + os.sep + 'pxelinux.cfg' + os.sep + filename, 'w').write( TFTP_TEMPLATE % 'backharddi/net/server=%s' % address['addr'].ip )
            os.chmod(self.tftpcfgdir + os.sep + 'pxelinux.cfg' + os.sep + filename,0666)
        
        filelist = ['/usr/lib/syslinux/pxelinux.0', '/usr/lib/syslinux/menu.c32', '/boot/linux-backharddi-ng', '/boot/minirt-backharddi-ng.gz']
        if not portInUse(69):
            for file in filelist:
                os.symlink(file, self.tftpcfgdir + os.sep + os.path.basename(file))
#            self.procmon.addProcess('tftp',['/usr/sbin/dnsmasq','--port=0','-d','-R','-h','-C','/dev/null','-K','--log-dhcp','-F','192.168.56.1,192.168.56.255,255.255.255.0','-M','pxelinux.0, backharddi-ng, 192.168.56.1','--enable-tftp','--tftp-root=%s' % self.tftproot])
            self.procmon.addProcess('tftp',['/usr/sbin/dnsmasq','--port=0','-d','-R','-h','-C','/dev/null','--enable-tftp','--tftp-root=%s' % self.tftproot])
        else:
            for file in filelist:
                shutil.copy(file, self.tftpcfgdir + os.sep + os.path.basename(file))

    def stopTftp(self):
        if self.tftpcfgdir:
            shutil.rmtree(self.tftpcfgdir)
        try:
            self.procmon.removeProcess('tftp')
        except:
            pass

    def startProxyDhcp(self):
        if not portInUse(67):
            import netifaces
            cmdline = ['/usr/sbin/dnsmasq','--port=0','-d','-R','-h','-C','/dev/null','--pxe-service=x86PC,Backharddi-NG,backharddi-ng/pxelinux', '--log-dhcp']
            for iface in netifaces.interfaces():
                if iface == 'lo':
                    continue
                addresses = netifaces.ifaddresses(iface)
                if 2 in addresses:
                    for address in addresses[2]:
                        if 'addr' in address:
                            cmdline.append('--dhcp-range=%s,proxy' % address['addr'])
                            break
            self.procmon.addProcess('proxydhcp',cmdline)

    def stopProxyDhcp(self):
        try:
            self.procmon.removeProcess('proxydhcp')
        except:
            pass
            
def portInUse(port,proto='udp'):
    f = open('/proc/net/' + proto)
    for con in f.readlines()[1:]:
        if int(con[6:19].split(':')[1],16) == port:
            return True
    return False

