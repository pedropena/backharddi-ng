'''
Created on 23/06/2010

@author: Pedro Pena Perez
'''

import sys
from twisted.internet import reactor
from twisted.internet.utils import getProcessOutput
from bitarray import bitarray
from twisted.python import log
import os

def clone(metadata, orig, dest):
    forig = open(orig,'rb')
    fdest = open(dest,'wb')
    for i in xrange(metadata['sBitmap']):
        if metadata['bitmap'][i] == True:
#            print 'Leyendo bloque %d' % i
            bytes = forig.read(metadata['sBlock'])
            fdest.write(bytes)
        else:
#            print 'Saltando bloque %d' % i
            forig.seek(metadata['sBlock'], 1)
            fdest.seek(metadata['sBlock'], 1)
    forig.close()
    fdest.truncate()
    fdest.flush()
    os.fsync(fdest.fileno())
    fdest.close()
    reactor.stop()

def processBitmap(data):
    metadata = {}
    for line in data.splitlines():
        key, value = line.split(': ')
        if key in ['sBitmap', 'sBlock' ]:
            value = long(value)
        elif key == 'bitmap':
            b = bitarray()
            b.fromstring(value)
            value = b
        metadata[key] = value
    reactor.callWhenRunning(clone, metadata, sys.argv[1], sys.argv[2])
    
def getBitmap():
    cmd = './Debug/ext2_bitmap'
    d = getProcessOutput(cmd, [ sys.argv[1] ])
    d.addCallback(processBitmap)

if __name__ == '__main__':
    reactor.callWhenRunning(getBitmap)
    reactor.run()