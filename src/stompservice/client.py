"""
Stomp client
Based on stomper example code by
(c) Oisin Mulvihill, 2007-07-26.
License: http://www.apache.org/licenses/LICENSE-2.0
"""
import logging
from twisted.internet import reactor
from twisted.internet.protocol import Protocol, ReconnectingClientFactory
import stomper

stomper.utils.log_init(logging.DEBUG)

class StompProtocol(Protocol, stomper.Engine):

    def __init__(self, client, username='', password=''):
        stomper.Engine.__init__(self)
        self.client = client
        self.username  = username
        self.password = password
        self.log = logging.getLogger("sender")
        self.stompBuffer = stomper.stompbuffer.StompBuffer()

    def connected(self, msg):
        """Once I've connected I want to subscribe to my the message queue.
        """
        return stomper.Engine.connected(self, msg)
        
    def ack(self, msg):
        """Processes the received message. I don't need to 
        generate an ack message.
        
        """
#        self.log.info("SENDER - received: %s " % msg['body'])
        return stomper.NO_REPONSE_NEEDED


    def send(self, dest, msg, **headers):
        """Send out a hello message periodically.
        """

        f = stomper.Frame()
        f.unpack(stomper.send(dest, msg))
        f.headers.update(headers)
        self.transport.write(f.pack())


    def subscribe(self, dest, **headers):
        f = stomper.Frame()
        f.unpack(stomper.subscribe(dest))
        # ActiveMQ specific headers:
        #
        # prevent the messages we send comming back to us.
        #f.headers['activemq.noLocal'] = 'true'
        f.headers.update(headers)
        self.transport.write(f.pack())
        

    def connectionMade(self):
        """Register with stomp server.
        """
        cmd = stomper.connect(self.username, self.password)
        self.transport.write(cmd)


    def dataReceived(self, data):
        """Use stompbuffer to determine when a complete message has been received. 
        """
        self.stompBuffer.appendData(data)
        while True:
            msg = self.stompBuffer.getOneMessage()
            if msg is None:
                break
            returned = self.react(msg)
            if returned:
               self.transport.write(returned)
            self.client.messageReceived(msg)

class StompClientFactory(ReconnectingClientFactory):
    
    # Will be set up before the factory is created.
    username, password = '', ''
    
    def buildProtocol(self, addr):
        self.proto = StompProtocol(self, self.username, self.password)
        self.send = self.proto.send
        self.subscribe = self.proto.subscribe
        return self.proto
    
    def clientConnectionLost(self, connector, reason):
        """Lost connection
        """
        print 'Lost connection.  Reason:', reason
    
    def clientConnectionFailed(self, connector, reason):
        """Connection failed
        """
        print 'Connection failed. Reason:', reason        
        ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)
        
    def messageReceived(self, msg):
        fname = 'recv_' + msg.get('cmd', '').lower()
        if hasattr(self, fname):
            getattr(self, fname)(msg)
            
