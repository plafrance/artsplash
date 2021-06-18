#   Copyright (C) 2019 Lunatixz
#   Copyright (C) 2021 plafrance
#
#
# This file is part of Artsplash ScreenSaver.
#
# Artsplash ScreenSaver is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Artsplash ScreenSaver is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ArtsplashScreenSaver.  If not, see <http://www.gnu.org/licenses/>.

import math
import urllib.parse, urllib.request, random, itertools
import xbmc, xbmcaddon, xbmcvfs, xbmcgui
import requests, json
from PIL import Image, ImageDraw
import os
import time
import random
import traceback

class MyMonitor (xbmc.Monitor):
    def __init__(self, callback):
        self._callback = callback
        self._active=True

    def ss_active(self):
        return self._active
    
    def onScreensaverDeactivated(self):
        self._active=False
        self._callback()
        self._callback=None

# Plugin Info
ADDON_ID       = 'screensaver.artsplash'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
ADDON_VERSION  = REAL_SETTINGS.getAddonInfo('version')
ADDON_PATH     = REAL_SETTINGS.getAddonInfo('path')
SETTINGS_LOC   = REAL_SETTINGS.getAddonInfo('profile')

IMG_CONTROLS   = [30000,30001]
try: CYC_CONTROL    = itertools.cycle(IMG_CONTROLS).__next__
except: CYC_CONTROL    = itertools.cycle(IMG_CONTROLS).next

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11"

class GUI(xbmcgui.WindowXMLDialog):
    def __init__( self, *args, **kwargs ):
        self.settings={}
        self.settings["ANIMATION"]      = str(REAL_SETTINGS.getSetting("Animate") == 'true')
        self.settings["TIME"]           = str(REAL_SETTINGS.getSetting("Time") == 'true')
        self.settings["OVERLAY"]        = str(REAL_SETTINGS.getSetting("Overlay") == 'true')
        self.settings["ENABLE_KEYS"]    = str(REAL_SETTINGS.getSetting("Enable_Keys") == 'true')
        self.settings["KEYWORDS"]       = urllib.parse.quote(REAL_SETTINGS.getSetting("Keywords").encode("utf-8"))
        self.settings["DATE_BEG"]       = REAL_SETTINGS.getSetting('DateBegin')
        self.settings["DATE_END"]       = REAL_SETTINGS.getSetting('DateEnd')
        self.settings["DEPARTMENTID"]   = REAL_SETTINGS.getSetting('DepartmentId')
        self.settings["TIMER"]          = [120,300,600,1800,3600,7200,18000,43200,86400][int(REAL_SETTINGS.getSetting("RotateTime"))]
        self.settings["RES"]            = [(1280, 720),(1920, 1080),(3840, 2160)][int(REAL_SETTINGS.getSetting("Resolution"))]
        self.settings["MATTE"]          = int(REAL_SETTINGS.getSetting("MatteSize"))
        self.settings["CROP_PCT"]       = int(REAL_SETTINGS.getSetting("CropSize"))/100.0
        self.settings["REAL_SIZE"]      = int(REAL_SETTINGS.getSetting("RealSize")) == 0
        self.settings["SCREEN_SIZE"]    = int(REAL_SETTINGS.getSetting("ScreenSize"))

        self.phototype = ['Met Museum', 'Rijksmuseum'][int(REAL_SETTINGS.getSetting("PhotoType"))]
        self.url_params     = '/%s'%self.phototype

        if self.phototype == "Met Museum":
            self.IMAGE_URL = 'https://collectionapi.metmuseum.org/public/collection/v1/'
        elif self.phototype == "Rijksmuseum":
            self.IMAGE_URL = 'https://www.rijksmuseum.nl/api/en/collection'
            
        self.object_list=[]
        self.info={}
        self.nextImage=False        
        self.currentID = CYC_CONTROL()

        self.KODI_MONITOR   = MyMonitor( self.terminer )

    def terminer(self):
        self.close()
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + str(msg), level)
            
            
    def onInit( self ):
        if  self.object_list==[] :
            try:
                self.object_list=self.getObjectList()
                self.log("Found "+str(len(self.object_list))+" objects", xbmc.LOGDEBUG)
            except Exception as e:
                self.log(e, xbmc.LOGERROR)
            
        self.winid = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
        self.winid.setProperty('artsplash_animation', self.settings["ANIMATION"])
        self.winid.setProperty('artsplash_time', self.settings["TIME"])
        self.winid.setProperty('artsplash_overlay', self.settings["OVERLAY"])
        self.startRotation()

    def setImage(self, id):
        self.log("SetImage:"+str(id), xbmc.LOGDEBUG)
        url=None

        url,data=self.getRandomImage()

        if url:
            if self.phototype == "Met Museum":
                    self.info["Artist"] = data["artistDisplayName"] + "(%s-%s)" % (data["artistBeginDate"], data["artistEndDate"]) if data["artistBeginDate"]!="" else ""
                    self.info["Title"] = "%s" % (data["title"]) + "(%s)" % (data["objectEndDate"]) if data["objectEndDate"] != "" else ""

                    if self.settings["REAL_SIZE"] :
                        mesures = [ m for m in data['measurements'] if m['elementName']=="Overall" ]
                        
                        if len(mesures)>0:
                            self.mesures = float(mesures[0]['elementMeasurements']['Height'])
                        else:
                            self.mesures = None
                            

            elif self.phototype == "Rijksmuseum":
                    self.info["Artist"] = data["principalOrFirstMaker"]
                    self.info["Title"] = "%s" % (data["title"])
        else:
                self.log("Image not found", xbmc.LOGERROR)
                return

        self.log("Trying " + str(url), xbmc.LOGDEBUG)
        url_image = self.openURL(url)
        url_image = url_image if len(url_image) > 0 else self.openURL(url)

        filename = self.traiter_image( url_image )

        self.getControl(id).setImage(filename)
        self.getControl(30004).setLabel( (self.info["Artist"] if "Artist" in self.info else "") + "\n" + (self.info["Title"] if "Title" in self.info else "") )

    def traiter_image( self, url_image ):
        crop_pct = self.settings["CROP_PCT"]
        self.log("URL" + url_image, xbmc.LOGDEBUG)
        image = Image.open(urllib.request.urlopen(url_image))
        self.log("IMAGE" + str(image), xbmc.LOGDEBUG)
        filename = "/tmp/artsplash_temp" + str(time.time()) + ".png"

        w_final = self.settings["RES"][0]
        h_final = self.settings["RES"][1]

        w_biseau = 8
        w_matte_int = 40
        w_matte_ext = self.settings["MATTE"]-2*(w_biseau+w_matte_int)

        sample = image.resize( (16,16) )
        colors = sample.getcolors()
        c=hsv_to_rgb(max([ rgb_to_hsv(c[1]) for c in colors], key=lambda x : x[1]))

        #c=(sum([s[1][0] for s in colors])/len(colors), sum([s[1][1] for s in colors])/len(colors), sum([s[1][2] for s in colors])/len(colors) )
        
        ratio = float(image.height)/image.width
        if ratio < 0.5625 : #16/9 et plus large
            image_out = Image.new( "RGB", (w_final, int((w_final-2*w_matte_ext)*ratio)+2*w_matte_ext ) )
        else:
            image_out = Image.new( "RGB", (int((h_final-2*w_matte_ext)/ratio)+2*w_matte_ext, h_final) )

        draw = ImageDraw.Draw( image_out )

        c_haut = darken(c, 0.8)
        c_gauche = darken(c, 0.9)
        c_droite = darken(c, 1.2)
        c_bas = darken(c, 1.3)

        couleurs=[darken(c, 1-x/100.0) for x in range( -3, 4 )]

        for x in range(image_out.width):
            for y in range(w_matte_ext):
                image_out.putpixel((x, y), random.choice(couleurs))
                image_out.putpixel((x, image_out.height-1-y), random.choice(couleurs))
        for x in range(w_matte_ext):
            for y in range(image_out.height):
                image_out.putpixel((x, y), random.choice(couleurs))
                image_out.putpixel((image_out.width-1-x, y), random.choice(couleurs))
        
        #Haut
        draw.polygon(((w_matte_ext-w_biseau, w_matte_ext-w_biseau),
                      (image_out.height/2, image_out.height/2),
                      (image_out.width-image_out.height/2,  image_out.height/2),
                      (image_out.width-(w_matte_ext-w_biseau), w_matte_ext-w_biseau)), fill=c_haut)

        draw.polygon(((0, 0),
                      (image_out.height/2, image_out.height/2),
                      (image_out.width-image_out.height/2,  image_out.height/2),
                      (image_out.width, 0)), fill=None, outline="black")
        
        #Bas
        draw.polygon(((w_matte_ext-w_biseau, image_out.height-(w_matte_ext-w_biseau)),
                      (image_out.height/2, image_out.height/2),
                      (image_out.width-image_out.height/2,  image_out.height/2),
                      (image_out.width-(w_matte_ext-w_biseau), image_out.height-(w_matte_ext-w_biseau))), fill=c_bas)

        draw.polygon(((0, image_out.height),
                      (image_out.height/2, image_out.height/2),
                      (image_out.width-image_out.height/2,  image_out.height/2),
                      ((image_out.width, image_out.height))), fill=None, outline="black")
        
        #Gauche
        draw.polygon(((w_matte_ext-w_biseau, w_matte_ext-w_biseau),
                      (image_out.height/2, image_out.height/2),
                      (image_out.height/2,  image_out.height/2),
                      (w_matte_ext-w_biseau, image_out.height-(w_matte_ext-w_biseau))), fill=c_gauche)

        #Droite
        draw.polygon(((image_out.width-(w_matte_ext-w_biseau), w_matte_ext-w_biseau),
                      (image_out.width-image_out.height/2, image_out.height/2),
                      (image_out.width-image_out.height/2,  image_out.height/2),
                      (image_out.width-(w_matte_ext-w_biseau), image_out.height-(w_matte_ext-w_biseau))), fill=c_droite)

        
        crop_pxl = int( min( image.size )*crop_pct )

        if self.settings["REAL_SIZE"] and self.mesures:
            h_screen=(self.settings["SCREEN_SIZE"]**2/4.16)**0.5*2.54
            screen_to_image_ratio = float(min(h_screen, self.mesures))/h_screen
            out_box = [min(d-2*w_matte_ext-2*w_matte_int, int(screen_to_image_ratio*d) ) for d in image_out.size]
        else :
            out_box = [d-2*w_matte_ext-2*w_matte_int for d in image_out.size]

        draw.rectangle (( w_matte_ext+w_biseau, w_matte_ext+w_biseau, image_out.width-(w_matte_ext+w_biseau), image_out.height-(w_matte_ext+w_biseau) ), "white" )
        image = image.resize ( out_box,
                               box=(crop_pxl,
                                    crop_pxl,
                                    image.width-crop_pxl,
                                    image.height-crop_pxl))
        image_out.paste( image, box=(int((image_out.width-out_box[0])/2), int((image_out.height-out_box[1])/2)))
        image_out.save(filename, format="png")
        return filename
    
    def startRotation(self):
        while True:
            self.rotateImage()
            for i in range( self.settings["TIMER"] * 2):
                self.KODI_MONITOR.waitForAbort(0.5)
                if not self.KODI_MONITOR.ss_active() or self.KODI_MONITOR.abortRequested() :
                    return

    def rotateImage(self):
        lastID    = self.currentID
        self.currentID = CYC_CONTROL()
        try:
            self.setImage(self.currentID)
            self.getControl(lastID).setVisible(False)
            self.getControl(self.currentID).setVisible(True)

        except Exception as e:
            self.log(traceback.format_exc(), xbmc.LOGERROR)
            
    def onAction( self, action ):
        if action.getId() == xbmcgui.ACTION_MOVE_RIGHT:
            self.rotateImage()
        else:
            self.terminer()

    def getRandomImage(self):

        if self.phototype == "Met Museum":
                url=self.IMAGE_URL+"objects/"+str(self.object_list[random.randrange(len(self.object_list))])
                
                data=get_url(url)
                if "primaryImage" in data:
                    url_image=data["primaryImage"]
                elif "primaryImageSmall" in data:
                    url_image=data["primaryImageSmall"]
                else:
                    url_image=None
                
        elif self.phototype == "Rijksmuseum":

                data=self.object_list[random.randrange(len(self.object_list))]
                if "webImage" in data :
                        url_image=data["webImage"]["url"]
                elif "headerImage" in data:
                        url_image=data["headerImage"]["url"]
                else:
                        url_image=None

        return url_image, data

    def getObjectList(self):
        if self.phototype == "Met Museum" :
                self.log("Dept ID: "+str(self.settings["DEPARTMENTID"]), xbmc.LOGDEBUG)
                if self.settings["DEPARTMENTID"]=="0":
                    url=self.IMAGE_URL+ 'search?hasImages=true&dateBegin=%s&dateEnd=%s&q=*'%(self.settings["DATE_BEG"], self.settings["DATE_END"])
                else:
                    url=self.IMAGE_URL+ 'search?hasImages=true&departmentId=%s&dateBegin=%s&dateEnd=%s&q=*'%(self.settings["DEPARTMENTID"], self.settings["DATE_BEG"], self.settings["DATE_END"])
                
                self.log("Trying : " + url, xbmc.LOGDEBUG)
                
                data=get_url(url)
                return data["objectIDs"]
                
        elif self.phototype == "Rijksmuseum" :
                url=self.IMAGE_URL+ '?key=79QWT4ub&imgonly=True&ps=100&type=painting'
                
                self.log("Trying : " + url, xbmc.LOGDEBUG)
                
                data=get_url(url)
                return data["artObjects"]
                

            
    def openURL(self, url):
        hdr = {'User-Agent': USER_AGENT}
        rep = requests.get( url, headers=hdr)
        
        return rep.url

def get_url(url):
    headers = {'User-Agent': USER_AGENT}
    response=requests.get(url, headers=headers)
    return json.loads(response.text)

def rgb_to_hsv(params):
    r, g, b = params
    r = float(r)
    g = float(g)
    b = float(b)
    high = max(r, g, b)
    low = min(r, g, b)
    h, s, v = high, high, high

    d = high - low
    s = 0 if high == 0 else d/high

    if high == low:
        h = 0.0
    else:
        h = {
            r: (g - b) / d + (6 if g < b else 0),
            g: (b - r) / d + 2,
            b: (r - g) / d + 4,
        }[high]
        h /= 6

    return h, s, v

def hsv_to_rgb(params):
    h, s, v = params
    i = math.floor(h*6)
    f = h*6 - i
    p = v * (1-s)
    q = v * (1-f*s)
    t = v * (1-(1-f)*s)

    r, g, b = [
        (v, t, p),
        (q, v, p),
        (p, v, t),
        (p, q, v),
        (t, p, v),
        (v, p, q),
    ][int(i%6)]

    return tuple(int(x) for x in [r, g, b])

def darken(c, p=1):
    c_or=rgb_to_hsv(c)
    return hsv_to_rgb((c_or[0], c_or[1], c_or[2]*p))
