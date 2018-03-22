import pycurl
from io import BytesIO
import re
import time
import subprocess
import configparser
import sys
import shutil
import os

# PYCURL_VERSION = int(pycurl.version_info()[1].split(".")[1])


class Cfg:

    def __init__(self, configFile):
        config = configparser.ConfigParser()
        try:
            config.read(configFile)
        except Exception:
            print("Something went wrong reading config file " + configFile)

        webcam = config['webcam']
        steps = config['steps']
        options = config['options']
        opencv = config['opencv']

        try:
            self.cgiDir = webcam['cgiDir']
            self.urlBase = webcam['urlBase']
            self.cgiDir = webcam['cgiDir']
            self.picDir = webcam['picDir']
            self.username = webcam['username']
            self.password = webcam['password']
            self.smallPicName = webcam['smallPicName']
            self.fullPicName = webcam['fullPicName']

            self.stepsPerPanoramaShot = int(steps['stepsPerPanoramaShot'])
            self.rotateSleep = int(steps['rotateSleep'])
            self.maxVerticalSteps = int(steps['maxVerticalSteps'])
            self.verticalDefaultSteps = int(steps['verticalDefaultSteps'])
            self.horizontalStartSteps = int(steps['horizontalStartSteps'])
            self.horizontalDefaultSteps = int(steps['horizontalDefaultSteps'])
            self.maxHorizontalSteps = int(steps['maxHorizontalSteps'])

            self.calibrateVertical = int(options['calibrateVertical']) == 1
            self.calibrateHorizontal = int(options['calibrateHorizontal']) == 1
            self.calibrateWithCV = int(options['calibrateWithCV']) == 1
            self.fullSizePic = int(options['fullSizePic']) == 1
            self.numOfPanoramaShots = int(options['numOfPanoramaShots'])
            self.restoreInitialPos = int(options['restoreInitialPos']) == 1

            self.compareThreshold = float(opencv['compareThreshold'])
            self.stitcherExec = opencv['stitcherExec']
            self.comparatorExec = opencv['comparatorExec']

        except KeyError as e:
            print("Config value not found: " + str(e))
            sys.exit(-1)

        self.defaultPresetNumber = 0
        self.outDir = "./out"


class CameraCtrl:
    def __init__(self, cfg, cleanUp=True):
        self.c = pycurl.Curl()
        self.cfg = cfg

        if cleanUp:
            # Initial clean up
            print("Removing old output directory")
            try:
                shutil.rmtree(self.cfg.outDir)
            except FileNotFoundError:
                print("Output directory not found...")

            os.makedirs(self.cfg.outDir)

    def getPath(self, path, dst=None):
        # print("Getting path: " + path)
        self.c.setopt(self.c.URL, self.cfg.urlBase + path)
        self.c.setopt(self.c.HTTPAUTH, self.c.HTTPAUTH_BASIC)

        self.c.setopt(self.c.USERNAME, self.cfg.username)
        self.c.setopt(self.c.PASSWORD, self.cfg.password)
        buffer = BytesIO()
        self.c.setopt(self.c.WRITEDATA, buffer)

        self.c.perform()

        if (dst is not None):
            d = open(dst, "wb")
            d.write(buffer.getvalue())
            d.close()
        else:
            return buffer.getvalue()

    def runCgi(self, cgiName, cgiParams=None):
        fullPath = self.cfg.cgiDir + "/" + cgiName
        if cgiParams:
            fullPath += "?" + cgiParams

        res = self.getPath(fullPath)
        return (re.search("ok", str(res)) is not None)

    def presetPosition(self, action, posNumber):
        return self.runCgi("preset.cgi",
                           "-act=" + action +
                           "&-status=1&-number=" + str(posNumber))

    def gotoPreset(self, posNumber):
        print("Moving to preset: " + str(posNumber))
        res = self.presetPosition("goto", posNumber)
        print("Go to position {}".format(res and "OK" or "ERR"))

    def setPreset(self, posNumber):
        res = self.presetPosition("set", posNumber)
        print("Set position {}".format(res and "OK" or "ERR"))

    def stepTo(self, to, steps=1, setPreset=False):
        if not to:
            print("invalid 'to' position")
            return False

        for i in range(steps):
            if not self.runCgi("ptz" + to + ".cgi"):
                print("step to " + to + " failed")
                return False
            time.sleep(self.cfg.rotateSleep)

        if (setPreset):
            print("Setting preset")
            self.setPreset(self.cfg.defaultPresetNumber)

        return True

    def stepLeft(self, steps=1, setPreset=False):
        return self.stepTo("left", steps, setPreset)

    def stepRight(self, steps=1, setPreset=False):
        return self.stepTo("right", steps, setPreset)

    def stepUp(self, steps=1, setPreset=False):
        return self.stepTo("up", steps, setPreset)

    def stepDown(self, steps=1, setPreset=False):
        return self.stepTo("down", steps, setPreset)

    def bruteForceResetPosition(self):
        if self.cfg.calibrateHorizontal:
            print("brute force reset horizontal")
            # horizontal position
            self.stepLeft(self.cfg.maxHorizontalSteps)

        if self.cfg.calibrateVertical:
            print("brute force reset vertical")
            # vertical position
            self.stepDown(self.cfg.maxVerticalSteps)

    def cvResetPosition(self):
        ref1 = self.cfg.outDir + "/ref1.jpg"
        ref2 = self.cfg.outDir + "/ref2.jpg"

        if self.cfg.calibrateHorizontal:
            print("cv horizontal reset position...")
            curr = ref1
            self.takePicture(False, curr)
            ctr = 0

            while ctr < self.cfg.maxHorizontalSteps:
                print("Move left and take shot...")
                self.stepLeft(self.cfg.stepsPerPanoramaShot)
                ctr += self.cfg.stepsPerPanoramaShot
                curr = (curr == ref1) and ref2 or ref1
                self.takePicture(False, curr)

                print("comparing...")
                cValue = self.compare([ref1, ref2])
                print("Correlation value = " + str(cValue))

                if (cValue >= self.cfg.compareThreshold):
                    print("Found correlation >= threshold " +
                          str(self.cfg.compareThreshold))
                    break

        if self.cfg.calibrateVertical:
            print("TODO")
            raise Exception

    def gotoStartPosition(self):
        if self.cfg.calibrateWithCV:
            self.cvResetPosition()
        else:
            self.bruteForceResetPosition()

        if self.cfg.calibrateHorizontal:
            print("Going to horizontal start position")
            # goto horizontal start
            self.stepRight(steps=self.cfg.horizontalStartSteps)

        if self.cfg.calibrateVertical:
            print("Going to vertical start position")
            # goto vertical start
            self.stepUp(self.cfg.verticalDefaultSteps)

    def takePicture(self, fullSize, dstName):
        baseName = (fullSize and self.cfg.fullPicName or self.cfg.smallPicName)

        baseName += ".jpg"

        self.getPath(self.cfg.picDir + "/" + baseName, dstName)

    def getPanoramaPictures(self):
        generatedImages = []

        if (self.cfg.restoreInitialPos):
            self.setPreset(self.cfg.defaultPresetNumber)

        self.gotoStartPosition()

        ctr = self.cfg.horizontalStartSteps

        for i in range(self.cfg.numOfPanoramaShots):
            dst = self.cfg.outDir + "/" + "pic_" + str(i) + ".jpg"
            print("Getting panorama shot # " + str(i))
            self.takePicture(self.cfg.fullSizePic, dst)
            generatedImages.append(dst)

            ctr += self.cfg.stepsPerPanoramaShot

            setPreset = (not self.cfg.restoreInitialPos) and \
                        (ctr == self.cfg.horizontalDefaultSteps)

            if (i + 1) == self.cfg.numOfPanoramaShots:
                break

            self.stepRight(self.cfg.stepsPerPanoramaShot, setPreset)

        self.gotoPreset(self.cfg.defaultPresetNumber)
        return generatedImages

    def stitch(self, imagesList):
        print("Running stitcher on " + str(len(imagesList)) + " images...")
        args = [self.cfg.stitcherExec] + [ "--output",  self.cfg.outDir +"/panorama.jpg" ] + imagesList
        ret = subprocess.call(args)
        print("Stitcher exited with code: " + str(ret))

    def compare(self, pics):
        print("Running comparator on " + str(pics))
        args = [self.cfg.comparatorExec] + pics

        try:
            strOut = subprocess.check_output(args)
        except subprocess.CalledProcessError as e:
            print("Stitcher exited with code: " + str(e.returncode))
            return 0.0

        return float(strOut)


def main():

    stitchOnly = (len(sys.argv) > 1 and sys.argv[1] == '-s')

    p = CameraCtrl(Cfg("panogen.cfg"), cleanUp=(not stitchOnly))

    if stitchOnly:
        imgList = [
            'out/pic_0.jpg',
            'out/pic_1.jpg',
            'out/pic_2.jpg',
            'out/pic_3.jpg',
            'out/pic_4.jpg',
            'out/pic_5.jpg',
            'out/pic_6.jpg'
            ]
    else:
        imgList = p.getPanoramaPictures()

    p.stitch(imgList)


if __name__ == '__main__':
    main()

