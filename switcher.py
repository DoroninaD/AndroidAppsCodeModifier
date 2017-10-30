import IdaHelper, ObjdumpHelper, re
from recordclass import recordclass

isIDA = True

rowModel = recordclass('row', 'line addr bytes thumb regs reg funcName funcAddr')
rowModel.__new__.__defaults__=(None, None, None, None, None, None, None, None)

def readLines(file):
    lines = file.readlines()
    if isIDA:
        return IdaHelper.readLines(lines)
    return ObjdumpHelper.readLines(lines)

def searchInLines(pattern, group):
    if isIDA:
        return IdaHelper.searchInLines(pattern, group)

def searchPattern(pattern, line):
    if isIDA:
        return IdaHelper.searchPattern(pattern, line)

def getFunctions(lines):
    if isIDA:
        return IdaHelper.getFunctions(lines)


def getPushes(group):
    if isIDA:
        return IdaHelper.getPush(group)

def getPops(group):
    if isIDA:
        return IdaHelper.getPops(group)


def checkSuitable(group):
    if isIDA:
        if not IdaHelper.checkOnlyOnePush(group):
            return []
        return IdaHelper.checkTheSameRegsForPushAndPops(group)

def getRelativeRegs(group):
    if isIDA:
        return IdaHelper.getRelativeRegs(group)

def getNumber(line):
    if isIDA:
        return IdaHelper.getNumber(line)

def getVars(lines):
    if isIDA:
        return IdaHelper.getVars(lines)


def handleExternalJumps(groups, conditions, funcAddrDict):
    if isIDA:
        return IdaHelper.hadleExternalJumps(groups, conditions,funcAddrDict)




