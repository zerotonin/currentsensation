# coding=utf-8
import RPi.GPIO as GPIO
import numpy as np
import time,sched,datetime,os,sys,subprocess,pygame
from pygame.locals import *
import pygame.camera
class currentExp(object):
    def __init__(self, direction = 1):
        # variables
        # the physical location is defiend to be zero near th powerplu and
        # than counts lanes up to the other site.

        # Note that gpio No is only working for Raspberry Pi Model B OR B+ as
        # the pin out might change between models.

        #Model B+ in use!
        #..................................
        #: gpio Pin : gpio No for RPiB+   :
        #...........:.....................:
        #:        2 :                   3 :
        #:        3 :                   5 :
        #:        4 :                   7 :
        #:       17 :                  11 :
        #:..........:.....................:


        # These three lists hold the information shown above by using the
        # physical location as dewsignator on the list. Example You need to
        # know the gpio Pin for lane 7 self.gpioPin[7] will return 11.
        self.pins          = [18, 24, 8, 14,13]
        self.powerLine     = {'red'   : self.pins[0],
                              'blue'  : self.pins[1],
                              'yellow': self.pins[2],
                              'light' : self.pins[3],
                              'shaker': self.pins[4]}
        self.timer         = sched.scheduler(time.time, time.sleep)
        self.activeLine    = 'off'
        self.savePath      = '~'
        self.delayOffSet   = 5
        self.fps           = 25
        self.captureMod    = 'video'
        self.expSchedReady = False
        # RPi.GPIO Layout in use which means we operate in gpio pins (not numbers)
        GPIO.setmode(GPIO.BCM)
        # Set GPIO direction
        for pin in self.pins:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.setup(pin, GPIO.LOW)

    def setPinHigh(self,lineTag):
        if lineTag == 'off':
            self.allOut()
            self.activeLine = 'off'
        else:
            GPIO.output(self.powerLine[lineTag], GPIO.HIGH)
            self.activeLine = lineTag

    def setPinLow(self,lineTag):
        GPIO.output(self.powerLine[lineTag], GPIO.LOW)
        self.activeLine = 'off'

    def allOut(self):
        for pin in self.pins:
            print pin
            GPIO.output(pin, GPIO.LOW)
        self.activeLine = 'off'

    def setExperimentSchedule(self,shakeDur=30.,periStimDur=30.,stimDur=1800.,
                              lines=['red','blue','yellow'],randomiseLines= True,
                              reps = 3):
        if self.captureMod == 'video':
            self.setExperimentScheduleVid(shakeDur,periStimDur,stimDur,
                              lines,randomiseLines,reps)
        elif self.captureMod == 'image':
            self. setExperimentScheduleImg(shakeDur,periStimDur,stimDur,
                              lines,randomiseLines,reps)

        else:
            sys.exit('unknown capture mode: ' + self.captureMod)


    def setExperimentScheduleImg(self,shakeDur=30.,periStimDur=30.,stimDur=1800.,
                              lines=['red','blue','yellow'],randomiseLines= True,
                              reps = 3):

        delay = self.delayOffSet

        # 1st trial without current
        delay  = self.setScheduledShake(delay,shakeDur) # shake shake shake
        delay2 = self.setScheduledLine('off',delay,stimDur) # turn power line off
        self.setScheduledImageCaputre(delay,delay2,'off') # record image
        delay  = delay2


        # pause inbetween trials
        delay = delay + periStimDur
        counter = 0
        # repeat for
        while counter < reps:

            # randomise the succession of lines if wanted
            if randomiseLines == True:
                np.random.shuffle(lines)

            # now trials
            for lineI in lines:
                delay  = self.setScheduledShake(delay,shakeDur) # shake shake shake
                delay2 = self.setScheduledLine(lineI,delay,stimDur) # turn on a powerLine
                self.setScheduledImageCaputre(delay,delay2,lineI) # record image
                delay  = delay2

                delay = delay + periStimDur

            counter += 1


        # last trial without current
        delay  = self.setScheduledShake(delay,shakeDur) # shake shake shake
        delay2 = self.setScheduledLine('off',delay,stimDur) # turn power line off
        self.setScheduledImageCaputre(delay,delay2,'off') # record image
        delay  = delay2

        # stop experiment
        delay = delay + 1
        self.timer.enter(delay,1,self.breakSchedule,['Experiment finished!'])

        # schedule is ready
        self.expSchedReady = True

    def setExperimentScheduleVid(self,shakeDur=30.,periStimDur=30.,stimDur=1800.,
                              lines=['red','blue','yellow'],randomiseLines= True,
                              reps = 3):
        delay = self.delayOffSet
        self.stimDur = stimDur+shakeDur/3.

        # 1st trial without current
        delay  = self.setScheduledShake(delay,shakeDur) # shake shake shake
        delay2 = self.setScheduledLine('off',delay,stimDur) # turn power line off
        delay3 = self.setScheduledVideoCapture('light',delay-shakeDur/3.,stimDur+shakeDur/3.,'off') # record video
        delay  = np.max([delay2,delay3])


        # pause inbetween trials
        delay = delay + periStimDur
        counter = 0
        # repeat for
        while counter < reps:

            # randomise the succession of lines if wanted
            if randomiseLines == True:
                np.random.shuffle(lines)

            # now trials
            for lineI in lines:
                delay  = self.setScheduledShake(delay,shakeDur) # shake shake shake
                delay2 = self.setScheduledLine(lineI,delay,stimDur) # turn on a powerLine
                delay3 = self.setScheduledVideoCapture('light',delay-shakeDur/3.,stimDur+shakeDur/3.,lineI)# record video

                delay  = np.max([delay2,delay3])
                delay = delay + periStimDur

            counter += 1


        # last trial without current
        delay  = self.setScheduledShake(delay,shakeDur) # shake shake shake
        delay2 = self.setScheduledLine('off',delay,stimDur) # turn power line off
        delay3 = self.setScheduledVideoCapture('light',delay-shakeDur/3.,stimDur+shakeDur/3.,'off') # record video
        delay  = np.max([delay2,delay3])

        # stop experiment
        delay = delay + periStimDur
        self.timer.enter(delay,1,self.breakSchedule,['Experiment finished!'])

        # schedule is ready
        self.expSchedReady = True


    def runExperiment(self,justScheduling = False):
        if self.expSchedReady:
            text_file = open(self.savePath+ "lastExpSchedule.txt", "w")
            scheduleList = self.timer.queue
            for eventItem in scheduleList:
                startTime = eventItem.time
                startTime = datetime.datetime.fromtimestamp(startTime)
                startTime = startTime.strftime('%Y-%m-%d--%H-%M-%S-%f--')
                argument = eventItem.argument
                argument = str(argument[0])
                print startTime,argument
                text_file.write(startTime + ': ' + argument + ' \n')
            text_file.close()


            if justScheduling == False:
                if self.captureMod == 'video':
                    self.timer.run()
                elif self.captureMod == 'image':
                    width = 640
                    height = 480
                    self.cam = pygame.camera.init()
                    self.cam = pygame.camera.Camera("/dev/video0",(width,height))
                    self.cam.start()
                    self.timer.run()
                    self.cam.stop()
                else:
                    print('unknown capture mode: ' + self.captureMod)

    def breakSchedule(self,message):
        # I am done the experiment finished
        sys.exit(message)

    def setScheduledLine(self,lineTag,delay,stimDur):
        #schedule power line change
        self.timer.enter(delay,2,self.changeLine,[lineTag])#{'lineTag':lineTag})
        delay = delay + stimDur
        self.timer.enter(delay,2,self.changeLine,['off'])#{'lineTag':lineTag})
        return delay

    def setScheduledVideoCapture(self,lineTag,delay,stimDur,powerLine):
        # schedule start of shaking
        self.timer.enter(delay,2,self.setPinHigh,['light'])
        self.timer.enter(delay,1,self.captureVidSched,[powerLine])
        # add shaking duration
        delay = delay + stimDur
        # schedule end of shaking
        self.timer.enter(delay,2,self.setPinLow,['light'])
        # return changed delay
        return delay

    def setScheduledShake(self,delay,shakeDur):
        # schedule start of shaking
        self.timer.enter(delay,2,self.setPinHigh,['shaker'])
        # add shaking duration
        delay = delay + shakeDur
        # schedule end of shaking
        self.timer.enter(delay,2,self.setPinLow,['shaker'])
        # return changed delay
        return delay

    def setScheduledImageCaputre(self,delayStart,delayEnd,powerLine):

        if self.fps > 9:
            sys.exit('If fps are higher than 9 please use the caputreVid function')

        else:
            lightOffSet = 0.2  # time offset for lights before and after takíng the image in sec
            periode     = 1/self.fps # time between images

            #1st image
            picTS       = delayStart #picture TimeStamp
            lightOn     = picTS - lightOffSet # timestamp to turn turn light on
            lightOff    = picTS + lightOffSet # timestamp to turn turn light off
            self.timer.enter(lightOn,2,self.setPinHigh,['light'])
            self.timer.enter(picTS,1,self.captureImgSched,[powerLine,lightOffSet,periode,delayEnd,picTS])
            self.timer.enter(lightOff,2,self.setPinLow,['light'])

    def changeLine(self,lineTag):
        # turn off every power line
        for i in ['red','blue','yellow']:
            self.setPinLow(i)

        # tell the system which power line is active
        self.activeLine = lineTag

        # if not set to 'off', activate powerline
        if lineTag != 'off':
            self.setPinHigh(lineTag)

    def captureVidSched(self,powerLine):
        now = datetime.datetime.now()
        fName =  self.savePath+now.strftime('%Y-%m-%d--%H-%M-%S-%f--') + powerLine +'.avi'

        commandStr = 'ffmpeg -t ' + str(self.stimDur) + ' -f v4l2 -an -r ' + str(self.fps) + ' -s 640x480 -i /dev/video0 ' + fName + ' &'

        os.system(commandStr)


    def captureImgSched(self,powerLine,lightOffSet,periode,delayEnd,picTS):
        now = datetime.datetime.now()
        image = self.cam.get_image()
        fName =  self.savePath+now.strftime('%Y-%m-%d--%H-%M-%S-%f--') + powerLine+ '.jpg'
        pygame.image.save(image,fName)

        # add new image capture schedule Entry
        picTS       = picTS+periode #picture TimeStamp
        if picTS < delayEnd:
            lightOn     = picTS - lightOffSet # timestamp to turn turn light on
            lightOff    = picTS + lightOffSet # timestamp to turn turn light off
            self.timer.enter(lightOn,2,self.setPinHigh,['light'])
            self.timer.enter(picTS,1,self.captureImgSched,[powerLine,lightOffSet,periode,delayEnd,picTS])
            self.timer.enter(lightOff,2,self.setPinLow,['light'])






