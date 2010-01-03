from twisted.plugins.cred_unix import UNIXChecker
from twisted.internet import defer
from twisted.cred.error import UnauthorizedLogin

def fixVerifyCryptedPassword(crypted, pw):
    if crypted[0] == '$':
        salt = crypted[0:3] + crypted.split('$')[2]
    else:
        salt = crypted[:2]
    try:
        import crypt
    except ImportError:
        crypt = None

    if crypt is None:
        raise NotImplementedError("cred_unix not supported on this platform")
    return crypt.crypt(pw, salt) == crypted

class FixUNIXChecker(UNIXChecker):
    def checkSpwd(self, spwd, username, password):
        try:
            cryptedPass = spwd.getspnam(username)[1]
        except KeyError:
            return defer.fail(UnauthorizedLogin())
        else:
            if fixVerifyCryptedPassword(cryptedPass, password):
                return defer.succeed(username)


