import IdaHelper, ObjdumpHelper, re, os, static_functions_helper
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


def resolveStaticFunctions(funcdict, config, fileName, groups):
    # выделяем функции, для которых нет имени
    nonamePattern = re.compile('(sub)|(local)_[0-9a-f]+',re.IGNORECASE)
    noname_functions = dict((addr, func) for addr, func in funcdict.items()
                            if nonamePattern.search(func))
    if len(noname_functions) > 0:
        nonstatic_folder = config.get('nonstatic_app_directory')
        nonstatic_file = os.path.join(nonstatic_folder, os.path.basename(fileName)+'.txt')

        newNames = dict((addr, func) for addr, func in noname_functions.items()
                        if not nonamePattern.search(func))

        while True and os.path.exists(nonstatic_file):
            noname_len = len(noname_functions)
            for addr in list(noname_functions):
                name = static_functions_helper.getName(groups, noname_functions[addr], nonstatic_file, newNames, funcdict)
                if name!='':
                    if name.startswith('j_'):
                        name = name[2:]
                    newNames[addr] = name
                    noname_functions.pop(addr)
            if len(noname_functions) == noname_len:
                break

        for addr in newNames:
            funcdict[addr] = newNames[addr]


def getPushes(group):
    if isIDA:
        return IdaHelper.getPush(group)

def getPops(group):
    if isIDA:
        return IdaHelper.getPops(group)


def checkOnlyOnePush(group):
    if isIDA:
        return IdaHelper.checkOnlyOnePush(group)

def checkTheSameRegsForPushAndPops(groups):
    if isIDA:
        return IdaHelper.checkTheSameRegsForPushAndPops(groups)


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


def handlePopLr(group, conditions, retSize):
    if isIDA:
        regs= IdaHelper.handlePopLr(group, conditions)
        #print(','.join(regs))
        return regs




