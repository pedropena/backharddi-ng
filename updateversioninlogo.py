#!/usr/bin/python

import Image, ImageFont, ImageDraw

version = open('debian/changelog').readline().partition('(')[2].partition(')')[0]
font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSans.ttf", 12)
fontcolor = '#000000'
im = Image.open("src/backhardding/html/media/banner_left.tpl.png")
draw = ImageDraw.Draw(im)
draw.text((11, 53), "Version: " + version, font=font, fill=fontcolor)
del draw
im.save('src/backhardding/html/media/banner_left.png')
