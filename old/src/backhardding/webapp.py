from zope.interface import implements
from twisted.internet import reactor

from nevow import athena, loaders, tags as T, inevow

class MyElement(athena.LiveElement):
    jsClass = u'MyModule.MyWidget'

    docFactory = loaders.stan(T.div(render=T.directive('liveElement'))[
        T.input(type="submit", value="Push me", onclick='Nevow.Athena.Widget.get(this).clicked()')])

    def __init__(self, *a, **kw):
        super(MyElement, self).__init__(*a, **kw)
        reactor.callLater(5, self.myEvent)

    def myEvent(self):
        print 'My Event Firing'
        self.callRemote('echo', 12345)

    def echo(self, argument):
        print 'Echoing', argument
        return argument
    athena.expose(echo)

from nevow import appserver, rend

class MyPage(athena.LivePage):
    addSlash = True
    docFactory = loaders.stan(T.html[
        T.head(render=T.directive('liveglue')),
        T.body(render=T.directive('myElement'))])

    def render_myElement(self, ctx, data):
        f = MyElement()
        f.setFragmentParent(self)
        return ctx.tag[f]

class FakeRoot(object):
    implements(inevow.IResource)
    
    def locateChild(self, ctx, segments):
        return MyPage(), segments
