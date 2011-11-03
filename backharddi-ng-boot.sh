#!/bin/bash

LOG=/var/log/backharddi-ng-boot
rm $LOG
exec 2> >(while read a; do echo "$(date):" "$a"; done >>$LOG) 
exec > >(while read a; do echo "$(date):" "$a"; done >>$LOG) 
set -xv

TITLE="Backharddi NG - Dispositivo de Arranque" 
KERNEL=/boot/linux-backharddi-ng
INITRD=/boot/minirt-backharddi-ng.gz
MEMTEST=/boot/memtest86+.bin
TMP_DIR=/tmp/backharddi-ng_boot
TMP_RESPONSE=/tmp/backharddi-ng_response
TMP_FILENAME=/tmp/backharddi-ng_filename
MARCA="backharddi"
NBSP=' '
TAB='	'
NL='
'
DOS_VOLUME_ID=bacadd10
SYSLINUX_DIR=/usr/share/backharddi-ng/syslinux
COMMON_DIR=/usr/share/backharddi-ng/common
FIFO=/tmp/progress_fifo
ERROR=/tmp/backharddi-ng_error
FILELIST=/usr/share/backharddi-ng/backharddi-ng-boot.filelist

abort(){
	exec 3>&-
	rm $ERROR $TMP_FILENAME $TMP_RESPONSE $FIFO
	exit $1
}

error(){
	echo 100 >&3
	zenity --error --title $TITLE --text "$1"
	umount $TMP_DIR && rmdir $TMP_DIR
	abort 1
}

umount_device(){
	for m in $(mount | grep $1 | cut -d" " -f 1); do
		umount $m
	done
}

mksyslinux_boot(){
	monitor
	umount_device $2
	part=$2
	if [ x"$2" = xformat ]; then
		echo 10 >&3
		parted $1 mklabel msdos
		sfdisk $1 <<EOT
unit: sectors
: start=63, size= , Id=c, bootable
EOT
		part=${1}1
		mkfs.msdos -I -i $DOS_VOLUME_ID -n "$MARCA" $part
		echo 20 >&3
	fi
	syslinux -f $part || error "No se ha podido instalar SYSLINUX en $1.\nEl sistema de archivos en $1 debe ser FAT16 o FAT32"
	dd if=/usr/lib/syslinux/mbr.bin of=$1
	parted $1 set ${part#$1} boot on
	echo 30 >&3
	mkdir -p $TMP_DIR
	mount $part $TMP_DIR
	echo 40 >&3
	mkdir $TMP_DIR/boot || true
	cp $KERNEL $TMP_DIR/boot/linux
	cp $INITRD $TMP_DIR/boot/minirt.gz
	cp $MEMTEST $TMP_DIR/boot/mt86plus
	echo 60 >&3
	mkdir $TMP_DIR/syslinux || true
	cp $SYSLINUX_DIR/* $TMP_DIR/syslinux
	echo 70 >&3
	cp $COMMON_DIR/* $TMP_DIR/syslinux
	echo 80 >&3
	umount $TMP_DIR && rm -r $TMP_DIR
	echo 100 >&3
}

monitor(){
	mkfifo $FIFO
	zenity --progress --width 400 --title $TITLE --text "Preparando dispositivo de almacenamiento USB..." --auto-close <$FIFO || abort $? &
	exec 3>&1 3>$FIFO
}
	 
humandev(){
	vendor="$(udevadm info -q env -n $1 | grep ID_VENDOR= | cut -d = -f 2)"
	model="$(udevadm info -q env -n $1 | grep ID_MODEL= | cut -d = -f 2)"
	[ -z $vendor ] && vendor="$(cat /sys/block/$(basename $1)/device/vendor)"
	[ -z $model ] && model="$(cat /sys/block/$(basename $1)/device/model)"
	echo "$vendor $model"
}

humanpart(){
	udi="$(hal-find-by-property --key block.device --string $1 | head -n 1)"
	[ -z "$udi" ] && return 0
	label="$(hal-get-property --udi "$udi" --key volume.label)"
	if [ -n "$label" ]; then
		echo "Etiquetada como: $label"
	fi
}

alert(){
	zenity --question --width 400 --title $TITLE --text "Recuerde que si continúa perderá cualquier dato que hubiera en el dispositivo de almacenamiento USB seleccionado. ¿Desea continuar?" || abort $?
}		

cd /tmp
IFS="$NBSP"
zenity --list --width 400 --height 200 --title $TITLE --text "Seleccione el tipo de medio para arrancar el sistema Backharddi NG:" --column "Medios soportados" "Dispositivo de almacenamiento USB" "CD-ROM" > $TMP_RESPONSE || abort $?
medio=$(cat $TMP_RESPONSE)

case "$medio" in
	*USB*)
		IFS="$NL"
		for i in $(find /dev -maxdepth 1 -name sd?); do
			bus="$(udevadm info -q env -n $i | grep ID_BUS= | cut -d = -f 2)"
			case "$bus" in
				*[Uu][Ss][Bb]*) device_list="$(echo $i) $(humandev $i)
$device_list";;
				*[Ss][Cc][Ss][Ii]* | *[Ii][Dd][Ee]* | *[Aa][Tt][Aa]*) true ;;
				*) device_list="$(echo $i) $(humandev $i)
$device_list";;
			esac
		done
		
		if [ -z "$device_list" ]; then
			zenity --info --title $TITLE --text "No se ha encontrado ningún dispositivo de almacenamineto USB en su sistema. Por favor, inserte uno."
			exit 1
		fi
		
		IFS="$NL"
		zenity --list --width 400 --height 200 --title $TITLE --text "Seleccione un dispositivo de almacenamiento USB:" --column "Dispositivos USB Detectados" $device_list > $TMP_RESPONSE || abort $?
		device=$(cat $TMP_RESPONSE | cut -d" " -f 1)
		
		zenity --list --height 200 --title $TITLE --text "Desea formatear todo el dispositivo seleccionado?" --column "" "Sí" "No" > $TMP_RESPONSE || abort $?
		format=$(cat $TMP_RESPONSE)

		if [ "$format" = "Sí" ]; then
			alert
			mksyslinux_boot $device format
		else
			for i in $device*; do
				[ "$device" = "$i" ] && continue
				part_list="$(echo $i) $(humanpart $i)
$part_list"
			done

			if [ -z "$part_list" ]; then
				zenity --info --title $TITLE --text "No se ha encontrado ninguna partición en el dispositivo seleccionado. Por favor, formatéelo antes."
				exit 1
			fi
			IFS="$NL"
			zenity --list --width 400 --height 200 --title $TITLE --text "Seleccione la partición donde desea instalar el sistema de arranque.\nRecuerde que los datos de esta partición no se perderán y que debe tener al menos 16MB libres en esta partición." --column "Particiones detectadas" $part_list > $TMP_RESPONSE || abort $?
			part=$(cat $TMP_RESPONSE | cut -d" " -f 1)
			mksyslinux_boot $device $part
		fi
	;;	
	*CD-ROM*)
		IFS="$TAB"
		if [ -f /proc/sys/dev/cdrom/info ]; then
			for i in $(grep 'drive name' /proc/sys/dev/cdrom/info | cut -f 2-); do 
				device_list="$(echo /dev/$i) $(humandev $i)
$device_list"
			done
		fi
		device_list="$device_list""Archivo de la imagen"
		
		IFS="$NL"
		zenity --list --width 400 --height 200 --title $TITLE --text "Seleccione un Grabador:" --column "Grabadores Detectados" $device_list > $TMP_RESPONSE || abort $?
		grabador=$(cat $TMP_RESPONSE | cut -d" " -f 1)

		IFS="$NBSP"
		while true; do
			rm $ERROR
			if [ $grabador = "Archivo" ]; then
				home=$(getent passwd $SUDO_USER | cut -d ":" -f 6)
				zenity --file-selection --title "Seleccione el nombre de la imagen:" --save --confirm-overwrite --filename "$home/backharddi-ng.iso" > $TMP_FILENAME || abort $?
				{ mkisofs -r -f -iso-level 2 -V "Backharddi NG" -b boot/isolinux/isolinux.bin -c boot/isolinux/boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table -hide-rr-moved -graft-points -path-list $FILELIST -o $(cat $TMP_FILENAME) 2>&1 || touch $ERROR; } | sed -u 's/^[\ \t]*//' | tee /dev/stderr | zenity --progress --width 400 --title $TITLE --text "Generando CD de arranque Backharddi NG..." --auto-close
				[ -f $ERROR ] && { error; continue; }

				if [ "$SUDO_UID" != "" ]; then
					chown ${SUDO_UID}:${SUDO_GID} $(cat $TMP_FILENAME) || true
				fi
			else
				device=$(echo $grabador | cut -d" " -f 1) 
				zenity --question --title $TITLE --text "Introduzca un CD virgen." || abort $?
				{ mkisofs -r -f -iso-level 2 -V "Backharddi NG" -b boot/isolinux/isolinux.bin -c boot/isolinux/boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table -hide-rr-moved -graft-points -path-list $FILELIST | cdrecord driveropts=burnfree gracetime=2 dev=$device - 2>&1 || touch $ERROR; } | sed -u 's/^[\ \t]*//' | tee /dev/stderr | zenity --progress --width 400 --title $TITLE --text "Generando CD de arranque Backharddi NG..." --auto-close
				[ -f $ERROR ] && { error; continue; }
				eject $device
			fi
			break
		done
	;;
esac

zenity --info --title $TITLE --text "La preparación del medio de arranque ha terminado correctamente."

abort 0
