# -*- coding: UTF-8 -*-

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# Authors: Igor An. Berezhnov (Vinnie) (igorberezhnov@yandex.ru)
# Copyright (C) 2017 Vinnie

from gi.repository import GdkPixbuf, GLib
import ctypes
from ctypes import *

libXcursor = CDLL('libXcursor.so.1')

import struct, array
def argbdata_to_pixdata(data,  len):
    if data == None or len < 1: return None
    b = array.array('B', '\0'* len*4)	
    offset = 0
    i = 0
    offset = 0
    while i < len:
	argb = data[i] & 0xffffffff
	rgba = (argb << 8) | (argb >> 24)
	b1 = (rgba >> 24)  & 0xff
	b2 = (rgba >> 16) & 0xff
	b3 = (rgba >> 8) & 0xff
	b4 = rgba & 0xff

	struct.pack_into("=BBBB", b, offset, b1, b2, b3, b4)
	offset = offset + 4
	i = i + 1

    return b 

PIXEL_DATA_PTR = POINTER(c_uint)

class XCursorImage (ctypes.Structure):
    _fields_ = [('version', ctypes.c_uint),
                ('size', ctypes.c_uint),
                ('width', ctypes.c_uint),
                ('height', ctypes.c_uint),
                ('xhot', ctypes.c_uint),
                ('yhot', ctypes.c_uint),
                ('delay', ctypes.c_uint),
                ('pixels', PIXEL_DATA_PTR)]


XCursorLibraryLoadImage = libXcursor.XcursorLibraryLoadImage
XCursorLibraryLoadImage.restype = ctypes.POINTER(XCursorImage)
XCursorLibraryLoadImage.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
XcursorImageDestroy     = libXcursor.XcursorImageDestroy
XcursorImageDestroy.argtypes = [ctypes.POINTER(XCursorImage)]

def GetCursorPixmap(theme):
    cr = XCursorLibraryLoadImage("left_ptr", theme, 16)
    crdata = cr[0]
    bytes = argbdata_to_pixdata(crdata.pixels, crdata.width * crdata.height)
    bytearr = GLib.Bytes.new(bytes)
    cursor_image = GdkPixbuf.Pixbuf.new_from_bytes(bytearr, GdkPixbuf.Colorspace.RGB, True, 8, crdata.width, crdata.height, crdata.width * 4)
    del bytes
    XcursorImageDestroy (cr)

    return cursor_image

