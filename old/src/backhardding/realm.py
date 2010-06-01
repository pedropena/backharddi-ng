from zope.interface import implements
from twisted.cred import portal, checkers
from twisted.web import resource
from twisted.web.static import File

class BackharddingRealm:
    implements(portal.IRealm)

    def requestAvatar(self, avatarId, mind, *interfaces):
        for iface in interfaces:
            if iface is resource.IResource:
                resc = File("/tmp")
                resc.realm = self
                return (resource.IResource, resc, lambda: None)
        raise NotImplementedError("Can't support that interface.")
