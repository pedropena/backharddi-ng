from twisted.plugins.cred_unix import UNIXChecker
from twisted.internet import defer
from twisted.cred.error import UnauthorizedLogin
from backhardding.utils.sudoers import SudoersParser

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
                if username is 'root':
                    return defer.succeed(username)
                else:
                    sp = SudoersParser()
                    sp.parseFile()
                    commands = sp.getCommands(username)
                    if commands is not None and '(ALL) ALL' in commands:
                        return defer.succeed(username)
                    else:
                        return defer.fail(UnauthorizedLogin())


