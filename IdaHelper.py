import re, switcher, utils, ast, cxxfilt

pushPatter = re.compile('(PUSH|(STM.*\s+SP!)).*{.*}', re.IGNORECASE)
popPattern = re.compile('(POP|(LDM.*\s+SP!)).*{.*}', re.IGNORECASE)
pushpopLastRegs = ['lr','pc']
varsDict = {}

def readLines(lines):
    getVars(lines)
    return [l for l in lines if '.text' in l]


def getPush(group):
    return [g for g in group if pushPatter.search(g.line)]

def getPops(group):
    return [g for g in group if popPattern.search(g.line)]

def getFunctions(lines):
    funcs,i = [],0
    funcDict = {}
    startMark, endMark = re.compile('S\s*U\s*B\s*R\s*O\s*U\s*T\s*I\s*N\s*E'), \
                         'End\s*of\s*function\s*'
    while i < len(lines):
        if not '.text' in lines[i]:
            i+=1
            continue
        if startMark.search(lines[i]):
            funcAddr = getAddress(lines[i])
            rows = []
            i += 1
            # ищем имя функции
            while True:
                # name, addr = getFuncName(lines[i]), getAddress(lines[i])
                name = getFuncName(lines[i])
                i+=1
                if name:
                    funcDict[funcAddr] = name
                    break

            #thisFuncEndMark = re.compile(endMark+re.escape(cxxfilt.demangle(name)))
            thisFuncEndMark = re.compile(endMark)
            while not thisFuncEndMark.search(lines[i]):
                l, bytes = lines[i], getBytes(lines[i])
                if not bytes:
                    i+=1
                    continue
                # line addr bytes thumb regs reg name
                rows.append(switcher.rowModel(l, getAddress(l), bytes, isThumb(bytes,l), None, None, None, funcAddr))
                i+=1
            funcs.append(rows)
            i+=1
        i+=1
    return funcs, funcDict


def getFuncName(line):
    nameMatch = re.search('.text:[0-9a-fA-F]+\s*(WEAK)?(EXPORT)?\s[a-zA-Z_\-0-9]+',line,re.IGNORECASE)
    if not nameMatch:
        return None
    return nameMatch.group().split(' ')[-1]


def getAddress(line):
    addrMatch = re.search('.text:[0-9a-fA-F]+',line)
    if not addrMatch:
        return None
    return hex(int(addrMatch.group().split(':')[-1],16))

def isThumb(bytes, line):
    return len(bytes) == 4 or '.W' in line

def getBytes(line):
    bytes = re.search('(\s[0-9a-fA-F]{2}\s[0-9a-fA-F]{2})+',line)
    if not bytes:
        return None
    bytesStr = bytes.group().replace(' ','').replace('\t','')
    firstPair = bytesStr[2:4]+bytesStr[0:2]
    secondPair = bytesStr[6:8]+bytesStr[4:6] if len(bytesStr) == 8 else ''
    if '.W' in line:
        return firstPair+secondPair
    return secondPair+firstPair


def checkOnlyOnePush(group):
    pushes = getPush(group)
    #pushes = utils.searchPattern(pushPatter, [g.line for g in group])
    if len(pushes)!=1 or not checkBigRegs(pushes[0]):
        return False
    return True


def checkTheSameRegsForPushAndPops(group):
    pushpops = dict((g.addr,re.search(pushPatter.pattern+'|'+popPattern.pattern,g.line))
                for g in group)
    pushpops = dict((addr, line.group()) for addr, line in pushpops.items() if line)
    if len(pushpops)==0:
        return False
    # parse regs
    regsSampler = None
    for addr, line in pushpops.items():
        regs = re.search('{.*}',line).group().lower()\
            .replace('{','')\
            .replace('}','')\
            .split(',')
        lastReg = regs[-1]
        if lastReg not in pushpopLastRegs:
            return False
        newRegs = [r for r in regs[:-1] if '-' not in r]
        for reg in regs[:-1]:
            if not '-' in reg:
                continue
            borders = reg.split('-')
            for i in range(int(borders[0][1:]),int(borders[1][1:])+1):
                newRegs.append('r{0}'.format(i))
        newRegs = sorted(newRegs)
        if not regsSampler:
            regsSampler = sorted(newRegs)
        elif len(newRegs)!=len(regsSampler) or \
            any(newRegs[i] != regsSampler[i] for i in range(len(newRegs))):
            return False
        item = [g for g in group if g.addr == addr][0]
        item.regs, item.reg = newRegs, lastReg
    return group


def checkBigRegs(line):
    big_regs = ['sp', 'ip', 'lr', 'pc', 'r12']
    return not any(big_regs[i] in line.line for i in range(len(big_regs)))

def getRelativeRegs(group):
    pattern = re.compile('.*(ldr|str).*\[.*\], ', re.IGNORECASE)
    return [g for g in group if pattern.search(g.line)]

def searchInLines(pattern, group):
    return [g for g in group if pattern.search(g.line)]
    #return utils.searchPattern(pattern, [g.line for g in group])

def searchPattern(pattern, line):
    return pattern.search(line.line)

def searchPatterns(pattern, lines):
    return list(filter(None,[pattern.search(l.line) for l in lines]))



def getNumber(line):
    a = line.line
    for key, value in [(key, value) for key, value in varsDict.items() if key[0]==line.funcAddr]:
        a = a.replace(key[1], value)
    number = re.search('#-?(0x)?[0-9a-f\-\+x]+\]?!?\s', a, re.IGNORECASE)
    if not number and '#' not in a:
        return 0
    if not number:
       # return 0
        return None
    try:
        return ast.literal_eval(number.group()
                                .replace(']','')
                                .replace('!','')[1:])
    except:
        return None



def getVars(lines):
   # pattern = re.compile('(ptr|buf|arg|varg|var)_?[0-9a-fr]+\s*=\s*-?(0x)?[a-f0-9]+\s',re.IGNORECASE)
    pattern = re.compile('[a-z]+_?[0-9a-fr]*\s*=\s*-?(0x)?[a-f0-9]+\s',re.IGNORECASE)
    vars = [l for l in lines if pattern.search(l)]
    for var in vars:
        items = ' '.join(var.split(' ')[1:])
        try:
            name = re.search('[a-z]+_?[0-9a-fr]*\s*', items,re.IGNORECASE)\
            .group().strip()
        except:
            aaa=1
        addr = getAddress(var)
        value =  re.search('=\s*-?(0x)?[a-f0-9]+\s',items,re.IGNORECASE)\
            .group().replace('=',' ').strip()
        varsDict[(addr, name)] = value


def hadleExternalJumps(groups, conditions, funcAddrDict):
    have_external_jumps = {}
    ext_jumps_list = {}
    external_jumps = []
    have_not_defined_jumps = []

    # убираем b, которые внутри функции
    for index, group in enumerate(groups):
        containsJumpsPattern = re.compile('\sb('+'|'.join(conditions)+')?(\.w)?\s',re.IGNORECASE)
        #clear = [not group[i][2].startswith('b') for i in range(len(group)) if len(group[i]) > 2]
        containsJumps = searchInLines(containsJumpsPattern, group)
        #if all([not containsJumpsPattern.search(g.line) for g in group]):
        if len(containsJumps)==0:
            continue
        first, last = group[0], group[-1]
        # if len(first) == 2:
        #     first = group[1]
        if pushPatter.search(first.line):
                #and last[2].startswith('pop') or last[2].startswith('ldmia'):
            first_addr, last_addr  = int(first.addr, 16), int(last.addr, 16)
            has_ext_jumps = False
            jumps = []
            for g in containsJumps:
                if re.search('lr|r[0-9|10|11|12]',g.line): #todo ???
                    continue
                #if addr < first_addr or addr > last_addr:
                # if index!=len(groups)-1:
                #     last_addr = int(groups[index+1][0][0],16)
                #addr = int(g.addr,16)
                addr = g.line[containsJumpsPattern.search(g.line).end():].strip().split(';')[0]
                if addr in funcAddrDict: #а что если функция внешняя?
                    addr = funcAddrDict[addr]
                addr = re.sub('[a-z]+_','0x',addr)
                try:
                    addr = int(addr, 16)
                except:
                    have_not_defined_jumps.append(group)
                    break
                #addr = int(addr.replace('[a-z]+_','0x'), 16)
                if addr < first_addr or addr > last_addr:
                    has_ext_jumps = True
                    jumps.append(addr)
                    #break
            if has_ext_jumps:
                    ext_jumps_list[index] = jumps
                    external_jumps.extend(jumps)
                    have_external_jumps[index] = group

    external_jumps = set(external_jumps)
    external_jumps_res = {}
    jumpFunc = {}
    for jump in list(external_jumps):
        try:
            destinationFunc = [g for g in groups
                           if int(g[0].addr,16) <= jump
                           and int(g[-1].addr,16)>=jump][0]
        except:
            continue #todo
        #for index, row in enumerate(lines):
        destinationRow = [row for row in destinationFunc if row.addr == hex(jump)][0]
        destinationIndex = destinationFunc.index(destinationRow)
        # нашли строку, на которую jump
        #проверяем, может прыгнули на push
        # push_method = re.search('push|stmdb', destinationRow)
        # if push_method is not None:
        #     external_jumps_res[jump] = 'push'
        #     continue
        #идем вниз, ищем push/pop/b
        jumpFunc[jump] = destinationFunc
        for index,r in enumerate(destinationFunc[destinationIndex:]):
            if pushPatter.search(r.line):
            #push_method = re.search('push|stmdb', r)
            #if push_method is not None:
                #external_jumps.remove(jump)
                external_jumps_res[jump] = 'push'
                break
            if popPattern.search(r.line):
            #pop_method = re.search('pop|ldmia', r)
            #if pop_method is not None:
                # опасно! надо что-то сделать!
                # либо не обрабатывать эту функцию и все, которые на нее ссылаются по addr
                # либо связать их и обрабатывать вместе
                external_jumps_res[jump] = 'pop'
                break
            #jump_method = re.search('\sb({0})?\s'.format(conditions_pattern), r)
            #if jump_method is not None:
            if index!=0 and containsJumpsPattern.search(r.line):
                # опасно! надо что-то сделать!
                # сделать рекурсию?
                external_jumps_res[jump] = 'jump'
                break

    for key, value in ext_jumps_list.items():
        for i in list(value):
            if i in external_jumps_res.keys() and external_jumps_res[i] == 'push':
                ext_jumps_list[key].remove(i)

    for key, value in ext_jumps_list.items():
        if len(value) == 0:
            have_external_jumps.pop(key)
    external_jumps_res = [addr for addr in external_jumps_res if external_jumps_res[addr] != 'push']
    # убираем те, которые в have_external_jumps
    if len(have_external_jumps)==0:
        return groups
    gr = groups
    groups = []
    removed_gr = 0
    #убираем функции с внешними прыжками и с фунциями, на которые прыгнули (если не push)
    for index, f in enumerate(gr):
        if index in have_external_jumps.keys():
            continue
        nojumps = True
        for jump in external_jumps_res:
            if f==jumpFunc[jump]:
                nojumps = False
        if nojumps and f not in have_not_defined_jumps:
            groups.append(f)
    return groups



    # for index, group in enumerate(gr):
    #     # если jump в этой группе, то ее тоже не обрабатываем
    #     first_addr, last_addr = group[0][0], gr[index + 1][0][0] if index != len(gr) - 1 else 0xFFFFFFFF
    #     handle = True
    #     for jump in external_jumps_res:
    #         if int(jump, 16) >= int(first_addr, 16) and int(jump, 16) <= int(last_addr, 16):
    #             handle = False
    #             removed_gr += 1
    #             break
    #     if handle and index not in have_external_jumps.keys():
    #         # убираем b/beq/...
    #         group = [g for g in group if not g[2].startswith('b')]
    #         groups.append(group)
    # return groups


def handlePopLr(group, conditions):
    pattern = re.compile('(pop|ldmfd).*,\s*lr}',re.IGNORECASE)
    popLr =  searchInLines(pattern,group)
    if len(popLr) == 0:
        return []
    popLrIndex = group.index(popLr[0])
    conditions = '|'.join(conditions)
    notUseRegs = []

    # jumpsWithoutReturn = re.compile('\sb({0})?(\.w)?\s+'.format(conditions),re.IGNORECASE)
    # if len(searchInLines(jumpsWithoutReturn, group)) > 0:
    #     return ['-1']
    # действие до конца функции, т.к. может прыгнуть куда-нибудь вниз (вверх не должна)
    # смотрим, есть ли вызов функций
    # простые прыжки (b) уже убрали, смотрим на bl
    jumpsPattern = re.compile('\sbl?({0})?(\.w)?\s+'.format(conditions),re.IGNORECASE)
    jumps = searchInLines(jumpsPattern, group[popLrIndex+1:])
    #если есть вызов других функций, то r0-r3 затирать нельзя,
    # т.к. они могут быть переданы как входные
    if len(jumps) > 0:
        notUseRegs.extend(['r0','r1','r2','r3'])

    # смотрим, значения каких функций могут быть переданы в r0-r3
    # ищем просто все регистры, которые задают где-то значения - до вызова последней функции
    #lastFuncIndex = group.index(jumpsWithReturn[-1])
    restOfTheGroup = group[popLrIndex+1:]

    changePattern = re.compile('\s(mov|mvn|sub|add)s?({0})?\s+r[0-9]+(,\s?r[0-9]+)+'
                               .format(conditions), re.IGNORECASE)
    changeRegsLines = searchPatterns(changePattern, restOfTheGroup)
    for l in changeRegsLines:
        #print(l.group())
        regs = l.group().replace(' ','').lower().split(',')[1:]
        notUseRegs.extend([r.strip() for r in regs])

    regPattern = re.compile('r[0-9]+',re.IGNORECASE)
    ldrPattern = re.compile('\s(ldr|str|cbn?z)({0})?\s'.format(conditions), re.IGNORECASE)
    ldrRegLines = searchInLines(ldrPattern, restOfTheGroup)
    for l in ldrRegLines:
        #print(l.line)
        regs = regPattern.findall(l.line.lower().replace(' ','').strip())
        if 'ldr' in l.line:
            regs = regs[1:]
        notUseRegs.extend([r.strip() for r in regs])

    cmpPattern = re.compile('\scmp({0})?.*\s'.format(conditions),re.IGNORECASE)
    cmpLines = searchInLines(cmpPattern, restOfTheGroup)
    for l in cmpLines:
        #print(l.line)
        regs = re.findall('r[0-9]+',l.line.lower(),re.IGNORECASE)
        notUseRegs.extend([r.strip() for r in regs])

    bxRegPattern = re.compile('\sbx\s+r[0-9]+\s',re.IGNORECASE)
    bxRegLines = searchPatterns(bxRegPattern, restOfTheGroup)
    for l in bxRegLines:
        #print(l.group())
        notUseRegs.append(re.search('r[0-9]+',l.group(),re.IGNORECASE).group().lower().strip())
    #print(','.join(notUseRegs))
    return sorted(set(notUseRegs),key = lambda x: int(x[1:]))









