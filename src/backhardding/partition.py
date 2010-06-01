'''
Created on 04/05/2010

@author: Pedro Pena Perez
'''

from twisted.internet import utils
from twisted.python import log
import os

class Partition():
    MOUNT = '/bin/mount'
    UMOUNT = '/bin/umount'

    def __init__(self, data=None):
        self.data = data
        self.mountdir = None
        self.previouslymounted = False
        if data:
            if 'volume.mount_point' in data and data['volume.mount_point']:
                log.msg('Particion de Backup previamente montada')
                self.mountdir = data['volume.mount_point']
                self.previouslymounted = True
            elif 'Block device' in data:
                for dev, mountdir in [ line.split()[:2] for line in open('/proc/mounts').read().splitlines() ]:
                    try:
                        if os.path.samefile(data['LV Name'], dev):
                            log.msg('Particion de Backup previamente montada')
                            self.mountdir = mountdir
                            self.previouslymounted = True
                    except:
                        continue

    def __str__(self):
        if self.data:
            if 'block.device' in self.data:
                return "%s %s" % (self.data['block.device'], self.mountdir)
            elif 'LV Name' in self.data:
                return "%s %s" % (self.data['LV Name'], self.mountdir)

    def mount(self, dir):
        if not self.mountdir:
            if self.data and 'block.device' in self.data:
                log.msg("Montando %s en %s" % (self.data['block.device'], dir) )
                value = utils.getProcessValue(self.MOUNT, [self.data['block.device'], dir])
                value.addCallback( self._cb_mount, dir )
            if self.data and 'LV Name' in self.data:
                log.msg("Montando %s en %s" % (self.data['LV Name'], dir) )
                value = utils.getProcessValue(self.MOUNT, [self.data['LV Name'], dir])
                value.addCallback( self._cb_mount, dir )                
        else:
            raise Exception("Unable to mount.")

    def _cb_mount(self, v, dir):
        if v == 0:
            self.mountdir = dir.decode('utf-8')
        else:
            raise Exception("Unable to mount.")

    def umount(self):
        if self.mountdir:
            log.msg('Desmontando %s' % self.mountdir)
            os.system("%s %s" % (self.UMOUNT, str(self.mountdir) ))