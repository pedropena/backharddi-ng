from zope.interface import implements

from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker
from twisted.cred.portal import Portal
from twisted.web.guard import HTTPAuthSessionWrapper, BasicCredentialFactory
from twisted.application import internet
from twisted.web import server
from backhardding.realm import BackharddingRealm
from backhardding.utils.fixedUNIXChecker import FixUNIXChecker

class BackharddingOptions(usage.Options):
    optParameters = [["port", "p", 4500, "The port number to listen on."]]

class BackharddingServiceMaker(object):
    implements(IServiceMaker, IPlugin)
    description = "Backharddi NG server"
    tapname = "backhardding"
    options = BackharddingOptions

    def makeService(self, options):
        """
        Construct a TCPServer from a factory defined in backhardding.
        """
        realm = BackharddingRealm()
        porta = Portal(realm, [FixUNIXChecker()])
        credentialFactory = BasicCredentialFactory("Backharddi NG")
        resource = HTTPAuthSessionWrapper(porta, [credentialFactory])
        return internet.TCPServer(int(options["port"]), server.Site(resource))

serviceMaker = BackharddingServiceMaker()

