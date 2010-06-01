#!/bin/sh

PATH=/sbin:/bin:/usr/sbin:/usr/bin

pidfile=/var/run/backharddi-ng.pid
rundir=/var/lib/backharddi-ng/
file=/etc/backharddi-ng/backharddi-ng.tac
logfile=/var/log/backharddi-ng.log

[ -r /etc/default/backharddi-ng ] && . /etc/default/backharddi-ng

test -x /usr/bin/twistd && TWISTD=/usr/bin/twistd
test -z $TWISTD && exit 0
test -r $file || exit 0

case "$1" in
    start)
        echo -n "Starting backharddi-ng: twistd"
        start-stop-daemon --start --quiet --exec $TWISTD -- --pidfile=$pidfile --rundir=$rundir --python=$file --logfile=$logfile >/dev/null --reactor epoll 2>&1
        echo "."	
    ;;

    stop)
        echo -n "Stopping backharddi-ng: twistd"
        start-stop-daemon --stop --quiet --pidfile $pidfile
        echo "."	
    ;;

    restart)
        $0 stop
        $0 start
    ;;

    force-reload)
        $0 restart
    ;;

    *)
        echo "Usage: /etc/init.d/backharddi-ng {start|stop|restart|force-reload}" >&2
        exit 1
    ;;
esac

exit 0
