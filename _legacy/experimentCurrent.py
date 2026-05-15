# -*- coding: utf-8 -*-
"""
Created on Wed Jul  5 13:54:13 2017

@author: bgeurten
"""

from CurrentSen.currentSensation import currentExp
import time,sched
from random import shuffle

#############
# Variablen #
#############

#  vor/nach Stimulus Dauer
myPeriStim = 30.0
# stimulus dauer
myStimDur  = 60.0
# phasen
lines     = ['red','yellow' ,'blue']
#randomisierte Reihenfolge
shuffle(lines)
print lines
# Object erstellen
gCom = currentExp()
gCom.allOut()
#time scheduler
gCom.savePath = '/home/aggoperfta/experimentCurrent/'
gCom.fps = 2
gCom.captureMod = 'video'
gCom.setExperimentSchedule(reps=3, stimDur=myStimDur, periStimDur= myPeriStim)
gCom.runExperiment()
