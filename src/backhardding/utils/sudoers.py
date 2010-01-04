#!/usr/bin/python
#
# This program parses a sudoers file and can be used to test who has 
# what access
#
# Author: Joel Heenan 30/09/2008
#
# This software may be freely redistributed under the terms of the GNU
# general public license.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.



import re, grp, socket, sys, os

class SudoCmnd:
    def __init__(self, runas, passwd, command, sp):
        self.runas = runas
        self.passwd = passwd
        self.command = command
        self.sp = sp

    def __repr__(self):
        commands = []
        for cmndAlias in self.sp.cmndAliases:
            if(cmndAlias == self.command):
                commands = self.sp.cmndAliases[cmndAlias]
                
        if(self.passwd):
            str = "(%s) %s\n" % (self.runas, self.command)
        else:
            str = "(%s) NOPASSWD: %s" % (self.runas, self.command)
        for command in commands:
            str += "\t%s\n" % command
        return str

class SudoRule:
    def __init__(self, user, server, command, sp):
        self.user = user
        self.server = server
        self.command = command
        self.sp = sp

    def __repr__(self):
        return "%s %s %s" % (self.user, self.server, self.command)

    def matchUser(self, user):
        if(user == self.user):
            return True
        for userAlias in self.sp.userAliases:
            if(userAlias == self.user): #I'm a user alias
                return self.sp.matchUserAlias(self.sp.userAliases[userAlias], user)
        return self.sp.matchUserAlias([self.user], user)

    def matchHost(self, host):
        if(host == self.server):
            return True
        for hostAlias in self.sp.hostAliases:
            if(hostAlias == self.server): #I'm a host alias
                return self.sp.matchHostAlias(self.sp.hostAliases[hostAlias], host)
        return self.sp.matchHostAlias([self.server], host)

class SudoersParser:
    def parseFile(self, file="/etc/sudoers"):
        self.hostAliases = {}
        self.userAliases = {}
        self.cmndAliases = {}
        self.rules = []
    
        fh = open(file, "r")
        lines = fh.readlines()
        lines = self._collapseLines(lines)

        defaultsRE = re.compile("^\s*Defaults")
        hostAliasRE = re.compile("^\s*Host_Alias")
        userAliasRE = re.compile("^\s*User_Alias")
        cmndAliasRE = re.compile("^\s*Cmnd_Alias")

        for line in lines:
            if(defaultsRE.search(line)):
                # don't currently do anything with these
                continue
            if(hostAliasRE.search(line)):
                self.hostAliases.update(self._parseAlias(line, "Host_Alias"))
                continue
            if(userAliasRE.search(line)):
                self.userAliases.update(self._parseAlias(line, "User_Alias"))
                continue
            if(cmndAliasRE.search(line)):
                self.cmndAliases.update(self._parseAlias(line, "Cmnd_Alias"))
                continue

            rule = self._parseRule(line)
            if(rule):
                self.rules.append(rule)

    # what commands can a user run on a particular host?
    # note: we assume that the current user/group environment is the
    # same as the host 
    def getCommands(self, user, host="localhost"):
        if(host == "localhost" or host == None):
            host = socket.gethostname()

        match = False
        cmds = []
        for rule in self.rules:
            if(rule.matchUser(user) and rule.matchHost(host)):
                match = True
                for cmnd in rule.command:
                    cmds.append(str(cmnd).strip('\n'))
        if(not match):
            return None
        else:
            return cmds
 
    # given the contents of a user alias, see if it matches a particular user
    def matchUserAlias(self, userAlias, user):
        for entry in userAlias:
            if(entry == user):
                return True
            elif(entry[0] == "%"):
                return self._userInGroup(entry[1:], user)
        return False

    def matchHostAlias(self, hostAlias, host):
        for entry in hostAlias:
            if(entry == "ALL"):
                return True
            elif(entry.find(host) == 0):
                return True
        return False

    def matchCmndAlias(self, cmndAlias, command):
        match = False
        for entry in cmndAlias:
            negate = False
            if(entry[0] == "!"):
                negate = True
                entry = entry[1:]
            if(entry.find(command) == 0):
                if(negate):
                    return False
                match = True
            if(os.path.normpath(entry) == os.path.dirname(command)):
                if(negate):
                    return False
                match = True
            if(entry == "ALL"):
                match = True
        return match
                
    def _userInGroup(self, group, user):
        try:
            (gr_name, gr_passwd, gr_gid, gr_mem) = grp.getgrnam(group)
        except KeyError:
#            print "warning: group %s was not found" % group
            return False
        if(user in gr_mem):
            return True

    def _parseAlias(self, line, marker):
        res = {}
    
        aliasRE = re.compile("\s*%s\s*(\S+)\s*=\s*((\S+,?\s*)+)" % marker)
        m = aliasRE.search(line)
        if(m):
            alias = str(m.group(1))
            nodes = str(m.group(2)).split(",")
            nodes = [ node.strip() for node in nodes ]
            res[alias] = nodes

        return res

    def _parseRule(self, line):
        ruleRE = re.compile("\s*(\S+)\s*(\S+)\s*=\s*(.*)")
        
        runasRE = re.compile("^\s*\((\S+)\)(.*)")
        m = ruleRE.search(line)
        if(m):
            user = str(m.group(1))
            host = str(m.group(2))
            parsedCommands = []
            
            cmnds = str(m.group(3)).split(",")
            cmnds = [ cmnd.strip() for cmnd in cmnds ]
            for cmnd in cmnds:
                unparsed = cmnd
                m = runasRE.search(unparsed)
                if(m):
                    runas = str(m.group(1))
                    unparsed = str(m.group(2))
                else:
                    runas = "ANY"
                pos = unparsed.find("NOPASSWD:")
                if(pos > -1):
                    passwd = False
                    unparsed = unparsed[pos + len("NOPASSWD:"):]
                else:
                    passwd = True
                unparsed = unparsed.strip()

                parsedCommands.append(SudoCmnd(runas, passwd, unparsed, self))
            
            return SudoRule(user, host, parsedCommands, self)

    def _collapseLines(self, lines):
        res = []
        currentline = ""
        
        for line in lines:
            if(line.rstrip()[-1:] == "\\"):
                currentline += line.rstrip()[:-1]
            else:
                currentline += line
                res.append(currentline)
                currentline = ""

        return res

