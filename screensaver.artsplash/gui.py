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

import urllib, urllib2, socket, random, itertools
import xbmc, xbmcaddon, xbmcvfs, xbmcgui
import requests, json

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
ADDON_PATH     = (REAL_SETTINGS.getAddonInfo('path').decode('utf-8'))
SETTINGS_LOC   = REAL_SETTINGS.getAddonInfo('profile').decode('utf-8')

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
        self.settings["KEYWORDS"]       = urllib.quote(REAL_SETTINGS.getSetting("Keywords").encode("utf-8"))
        self.settings["DATE_BEG"]       = REAL_SETTINGS.getSetting('DateBegin')
        self.settings["DATE_END"]       = REAL_SETTINGS.getSetting('DateEnd')
        self.settings["DEPARTMENTID"]   = REAL_SETTINGS.getSetting('DepartmentId')
        self.settings["TIMER"]          = [30,60,120,240][int(REAL_SETTINGS.getSetting("RotateTime"))]
        self.settings["RES"]            = ['1280x720','1920x1080','3840x2160'][int(REAL_SETTINGS.getSetting("Resolution"))]

        self.phototype = ['Met Museum', 'Rijksmuseum'][int(REAL_SETTINGS.getSetting("PhotoType"))]
        self.url_params     = '/%s'%self.phototype

        if self.phototype == "Met Museum":
            self.IMAGE_URL = 'https://collectionapi.metmuseum.org/public/collection/v1/'
        elif self.phototype == "Rijksmuseum":
	    self.IMAGE_URL = 'https://www.rijksmuseum.nl/api/en/collection'
            
        self.object_list=[]
        self.info=""
        self.nextImage=False        
        self.currentID = CYC_CONTROL()
        self.nextID    = CYC_CONTROL()

        self.KODI_MONITOR   = MyMonitor( self.terminer )

    def terminer(self):
        self.close()
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        xbmc.log((ADDON_ID + '-' + ADDON_VERSION + '-' + str(msg)).decode("utf8"), level)
            
            
    def onInit( self ):
        if  self.object_list==[] :
            try:
                self.object_list=self.getObjectList()
                self.log("Found "+str(len(self.object_list))+" objects", xbmc.LOGNOTICE)
            except Exception as e:
                self.log(e, xbmc.LOGERROR)
            
        self.log("INIT", xbmc.LOGERROR)
        self.winid = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
        self.winid.setProperty('artsplash_animation', self.settings["ANIMATION"])
        self.winid.setProperty('artsplash_time', self.settings["TIME"])
        self.winid.setProperty('artsplash_overlay', self.settings["OVERLAY"])
        self.startRotation()

    def setImage(self, id):
        self.log("SetImage:"+str(id), xbmc.LOGERROR)
        url=None

        url,data=self.getRandomImage()

        if url:
	    if self.phototype == "Met Museum":
		    self.log("Trying " + str(url), xbmc.LOGNOTICE)
		    self.info=data["artistDisplayName"] + "(%s-%s)" % (data["artistBeginDate"], data["artistEndDate"]) if data["artistBeginDate"]!="" else ""
		    self.info+="\n%s" % (data["title"]) + "(%s)" % (data["objectEndDate"]) if data["objectEndDate"] != "" else ""
	    elif self.phototype == "Rijksmuseum":
		    self.log("Trying " + str(url), xbmc.LOGNOTICE)
		    self.info=data["principalOrFirstMaker"]
		    self.info+="\n%s" % (data["title"])
        else:
	        self.log("Image not found", xbmc.LOGNOTICE)
	        return

        image = self.openURL(url)
        image = image if len(image) > 0 else self.openURL(url)

        self.getControl(id).setImage(image)
        

    def startRotation(self):
        while True:
            self.changerImage()
            for i in range( self.settings["TIMER"] * 2):
                self.KODI_MONITOR.waitForAbort(0.5)
                if not self.KODI_MONITOR.ss_active() or self.KODI_MONITOR.abortRequested() :
                    return

    def changerImage(self):
        self.nextID    = self.currentID
        self.currentID = CYC_CONTROL()
        try:
            self.setImage(self.currentID)
            self.getControl(self.nextID).setVisible(False)
            self.getControl(self.currentID).setVisible(True)
            self.getControl(30004).setLabel(self.info)
        except Exception as e:
            self.log(e, xbmc.LOGERROR)
            
    def onAction( self, action ):
        if action.getId() == xbmcgui.ACTION_MOVE_RIGHT:
            self.changerImage()
        else:
            self.terminer()

    def getRandomImage(self):

	if self.phototype == "Met Museum":
	        url=self.IMAGE_URL+"objects/"+str(self.object_list[random.randrange(len(self.object_list))])
	        
	        data=get_url(url)
	            
	        if "primaryImageSmall" in data:
	            url_image=data["primaryImageSmall"]
	        elif "primaryImage" in data:
	            url_image=data["primaryImage"]
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
		self.log("Dept ID: "+str(self.settings["DEPARTMENTID"]), xbmc.LOGNOTICE)
		if self.settings["DEPARTMENTID"]=="0":
		    url=self.IMAGE_URL+ 'search?hasImages=true&dateBegin=%s&dateEnd=%s&q=*'%(self.settings["DATE_BEG"], self.settings["DATE_END"])
		else:
		    url=self.IMAGE_URL+ 'search?hasImages=true&departmentId=%s&dateBegin=%s&dateEnd=%s&q=*'%(self.settings["DEPARTMENTID"], self.settings["DATE_BEG"], self.settings["DATE_END"])
		
		self.log("Trying : " + url, xbmc.LOGNOTICE)
		
		data=get_url(url)
		return data["objectIDs"]
		
	elif self.phototype == "Rijksmuseum" :
		url=self.IMAGE_URL+ '?key=79QWT4ub&imgonly=True&ps=100&type=painting'
		
		self.log("Trying : " + url, xbmc.LOGNOTICE)
		
		data=get_url(url)
		return data["artObjects"]
		

            
    def openURL(self, url):
        self.log("openURL url = " + url)
        request = urllib2.Request(url)
        request.add_header('User-Agent', USER_AGENT)
        page = urllib2.urlopen(request, timeout = 15)
        url = page.geturl()
        self.log("openURL return url = " + url)
        return url

def get_url(url):
    headers = {'User-Agent': USER_AGENT}
    response=requests.get(url, headers=headers)
    return json.loads(response.text)
