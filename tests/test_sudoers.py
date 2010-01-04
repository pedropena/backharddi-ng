from backhardding.utils.sudoers import SudoersParser

def test():
    sp = SudoersParser()
    sp.parseFile("tests/sudoers")
    assert sp.getCommands('root') == ["(ALL) ALL"]
    print sp.getCommands('kkk')
    assert sp.getCommands('kkk') == ["(WEBMASTERS) NOPASSWD: KILL\t/usr/bin/kill"]

if __name__ == "__main__":
	test()
