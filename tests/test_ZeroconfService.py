from backhardding.utils.ZeroconfService import ZeroconfService
from twisted.internet import glib2reactor
glib2reactor.install()
    
from twisted.internet import reactor
    
def test():
    class MyService(ZeroconfService):
        def __init__(self, name, port, stype="_http._tcp", domain="", host="", text=""):
            ZeroconfService.__init__(self, name, port, stype, domain, host, text, self.new_service, self.remove_service)

        def new_service(self, interface, protocol, name, stype, domain, flags):
            print "Found service '%s' of type '%s' in domain '%s' on %i.%i. Flags: %s" % (name, stype, domain, interface, protocol, flags)
            self.unpublish()
    
        def remove_service(self, interface, protocol, name, stype, domain, flags):
            print "Service '%s' of type '%s' in domain '%s' on %i.%i disappeared. Flags: %s" % (name, stype, domain, interface, protocol, flags)
            reactor.callLater(0.5, reactor.stop)
   
    MyService(name="TestService", port=3000)        
    reactor.run()

if __name__ == "__main__":
	test()
