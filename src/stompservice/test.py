from client import StompClientFactory
from twisted.internet import reactor
from pprint import pprint

class XStomp(StompClientFactory):    
      
    def recv_connected(self, msg):
        print 'recv_connected'
        pprint(msg)
        self.subscribe('/topic/home')
        self.send('/topic/home', 'welcome')

    def recv_message(self,msg):        
        print 'recv_send'
        pprint(msg)
        if msg['body'] != 'hiho':
            print 'do send'
            self.send('/topic/home', 'hiho')

reactor.connectTCP('localhost', 61613, XStomp())
reactor.run()
