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

    def __init__(self, data=None, mountdir = None, mounted = False):
        self.data = data
        self.mounted = False
        self.mountdir = mountdir
        self.previouslymounted = mounted
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
            if 'block.device' in data:
                self.name = '+En_particion_%s' % data['block.device'].replace('/','_')
            if 'LV Name' in self.data:
                self.name = '+En_particion_%s' % data['LV Name'].replace('/','_')

    def __str__(self):
        if self.data:
            if 'block.device' in self.data:
                return "%s %s" % (self.data['block.device'], self.mountdir)
            elif 'LV Name' in self.data:
                return "%s %s" % (self.data['LV Name'], self.mountdir)

    def mount(self, dirname):
        self.mounted = True
        if self.data and 'block.device' in self.data:
            dev = self.data['block.device']
        if self.data and 'LV Name' in self.data:
            dev = self.data['LV Name']
        params = [ dev, dirname ]
        if self.previouslymounted:
            dev = self.mountdir
            params.append('-o bind')
        log.msg("Montando %s en %s" % (dev, dirname) )
        try:
            os.mkdir(dirname)
        except:
            pass
        value = utils.getProcessValue(self.MOUNT, params)
        value.addCallback( self._cb_mount, dirname )            

    def _cb_mount(self, v, dirname):
        if v == 0:
            self.mountdir = dirname.decode('utf-8')
        else:
            raise Exception("Unable to mount.")

    def umount(self):
        if self.mounted:
            log.msg('Desmontando %s' % self.mountdir)
            os.system("%s %s" % (self.UMOUNT, str(self.mountdir) ))
            if self.mountdir:
                os.rmdir(self.mountdir)
