# -*- coding: utf-8 -*-
import re, utils, arm_translate, parse,parse_functions_utils, static_functions_helper, config_parser, os
import cxxfilt, colored, sys
import switcher, codecs

conditions = ['eq','ne','cs','hs','cc','lo','mi','pl','vs','vc','hi','ls','ge','lt','gt','le','al']
conditions_pattern = '|'.join(conditions)

NEW = True
RETURN_TYPES = False

# def findSpSubbed(groups):
#     containSpSubbedPattern = re.compile('\ssub\s+sp,',re.IGNORECASE)
#     matching_groups = []
#     for group in groups:
#         matches = switcher.searchInLines(containSpSubbedPattern,group)
#         if len(matches)>0:
#             matching_groups.append(group)
#     return matching_groups


def findInGroups(pattern,groups):
    #containSpSubbedPattern = re.compile('bx\s+lr',re.IGNORECASE)
    matching_groups = []
    for group in groups:
        matches = switcher.searchInLines(pattern,group)
        if len(matches)>0:
            matching_groups.append(group)
    return matching_groups


def run(path, start_group, end_group, DEBUG, config):
    print('DEBUG ', DEBUG)
    f = codecs.open(path+'.txt', 'r','utf-8', errors="ignore")
    lines = switcher.readLines(f)
    f.close()

    groups, addrFuncDict = switcher.getFunctions(lines)
    switcher.resolveStaticFunctions(addrFuncDict, config, path,groups)
    funcAddrDict = dict(zip(addrFuncDict.values(),addrFuncDict.keys()))
    init_group_len = len(groups)
    print('GROUPS:',  len(groups))

    #находим тип функций
    function_types = []
    if RETURN_TYPES:
        print('FUNCTIONS')
        function_types = parse_functions_utils.getFunctionsReturnTypeSize(addrFuncDict, config)
    #todo использовать числа при рандомизации

    containSpSubbed = findInGroups(re.compile('\ssub\s+sp,',re.IGNORECASE),groups)
    print('Groups with subbed sp:', len(containSpSubbed))

    containBXLRbefore = findInGroups(re.compile('bx\s+lr',re.IGNORECASE),groups)

    # check only one push
    # the same regs for push and pops

    a = list(filter(None,[switcher.checkOnlyOnePush(g) for g in groups]))
    print("Only one push:", len(a))

    a = list(filter(None,[switcher.checkTheSameRegsForPushAndPops(g) for g in groups]))
    print("The same regs for push and pop:", len(a))


    groups = list(filter(None,[switcher.checkSuitable(g) for g in groups]))
    print("Suitable groups (push and pop with the same registers, only one push):", len(groups))


    groups = switcher.handleExternalJumps(groups, conditions, funcAddrDict)
    print("Groups after jumps removing", len(groups))

    containBXLR = findInGroups(re.compile('bx\s+lr',re.IGNORECASE),groups)
    print('CONTAINS BX LR:',len(containBXLR))
    containPOPLR = findInGroups(re.compile('(pop|ldmfd).*,lr}',re.IGNORECASE),groups)
    print('CONTAINS POP LR:',len(containPOPLR))

    restrictedRegsDict = dict((g[0].addr,switcher.handlePopLr(g, conditions,4)) for g in containPOPLR)
    # for key, value in restrictedRegsDict.items():
    #     print('{0}:{1}'.format(key, ','.join(value)))


    #groups = [group for group in groups if group[i][6]=='pc' for i in range(1,len(group))]
    print ('Functions with push-pop pairs', len(groups))

    #добавляем в to_write (адрес, количество старых байт, новые байты) для перезаписи
    groups_count = 0
    to_write = []
    l = 0
    full_registers_count = 0
    #1935-36
    print(start_group, ":", end_group)

    regs_added = 0
    handledGroups = []
    handledFuncs = []
    for index,group in enumerate(groups[start_group:end_group]): # 66 libcrypto - pop lr => bl - перезапись регистров
        #first, last = group[0], group[-1]
        push, pops = switcher.getPushes(group)[0], switcher.getPops(group)
        l+=1
        # добавляем регистры в начало, считает их количество
        real_reg_count = len(push.regs)
        return_size = function_types[group[0].addr] if RETURN_TYPES else 4
        restrictedRegs = restrictedRegsDict[group[0].addr]\
            if group[0].addr in restrictedRegsDict else []
        #print(','.join(restrictedRegs),'Next')

        new_registers, table = utils.addRegistersToStartAndEnd\
            (push.regs, push.bytes, return_size, restrictedRegs)
        if new_registers == -1:
            full_registers_count+=1
            continue
        # меняем втутренние строки, взаимодействующие с sp
        inner_lines = parse.getAllSpLinesForLow(group, table)

        if inner_lines == -1:
            continue
        groups_count+=1
        handledGroups.append(group)
        # добавляем в to_write (адрес, количество старых байт, новые байты) push
        #print (first[0])

        to_write.append((push.addr, len(push.bytes) // 2,
                         utils.toLittleEndian
                         (arm_translate.pushpopToCode
                          (new_registers, push.bytes, push.thumb, real_reg_count, False))))  # добавляем новый push

        # добавлаем все pop
        for pop in pops:
           to_write.append((pop.addr, len(pop.bytes) // 2,
                            utils.toLittleEndian(
                                arm_translate.pushpopToCode
                                (new_registers, pop.bytes, pop.thumb, real_reg_count, True))))  # добавляем новый pop

        if len(inner_lines) > 0:
            to_write.extend(inner_lines)
        funcAddr = group[0].addr
        key = cxxfilt.demangle(addrFuncDict[funcAddr]) \
            if addrFuncDict[funcAddr]!='' else push.addr
        #print(colored.setColored('{0}: '.format(key), colored.OKGREEN) + 'old {0}, new {1}'.format(push.regs, new_registers))
        regs_added += len(new_registers) - len(push.regs)
    secured = groups_count/init_group_len*100
    # output = 'End:{0}, full regs:{1}, secured:{2}%, average randomness:{3}'\
    #     .format(groups_count, full_registers_count, secured, regs_added/groups_count)

    output = 'End:{0}, full regs:{1}, secured:{2}%'\
        .format(groups_count, full_registers_count, secured)
    if groups_count>0:
        output += ", average randomness:{0}".format(regs_added/groups_count)

    colored.printColored(output, colored.BOLD)

    onlyForContainsSub = [item for item in containSpSubbed if item not in handledGroups]
    onlyWithPushes = [item for item in handledGroups if item not in containSpSubbed]
    output = 'Only for SUB_SP:{0}, only for PUSH:{1}, common: {2}'\
        .format(len(onlyForContainsSub), len(onlyWithPushes), len(handledGroups) - len(onlyWithPushes))
    colored.printColored(output, colored.BOLD)


    notHandledPushes = [item for item in groups if item not in onlyWithPushes
                        and item in containSpSubbed]
    #onlyForContainsSub.extend(notHandledPushes)
    s = sorted(onlyForContainsSub,key=lambda x: x[0].addr)
    l = []
    handled = 0
    print('SUB SP:::')
    for item in onlyForContainsSub:
        if item[0].addr == 0x4a60:
            continue
        res = parse.getAllSpLinesForSub(item)
        if res == -1 or len(res)==0:
            aaa=1
        if res!=-1 and len(res) > 0:
            handled+=1
            l.extend(res)
            key = cxxfilt.demangle(addrFuncDict[item[0].addr]) \
                if addrFuncDict[item[0].addr] != '' else item[0].addr
            print(colored.setColored('{0}: '.format(key), colored.OKGREEN))
    print ('Handled with SUB SP (only sub sp lines):', handled)
    to_write.extend(l)



    #переписываем файл
    f = open(path+'_old.so', 'br')
    text = f.read()
    f.close()

    for line in to_write:
        offset = int(line[0],16)
        text = text[:offset] + line[2] + text[offset+line[1]:]

    f = open(path+'.so', 'bw')
    f.write(text)
    f.close()











