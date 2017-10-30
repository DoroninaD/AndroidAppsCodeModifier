# -*- coding: utf-8 -*-
import re, utils, arm_translate, parse,parse_functions_utils, static_functions_helper, config_parser, os
import cxxfilt, colored, sys
import switcher, codecs

conditions = ['eq','ne','cs','hs','cc','lo','mi','pl','vs','vc','hi','ls','ge','lt','gt','le','al']
conditions_pattern = '|'.join(conditions)

NEW = True
RETURN_TYPES = False

def findSpSubbed(groups):
    containSpSubbedPattern = re.compile('\ssub\s+sp,',re.IGNORECASE)
    matching_groups = []
    for group in groups:
        matches = switcher.searchInLines(containSpSubbedPattern,group)
        if len(matches)>0:
            matching_groups.append(group)
    return matching_groups


def findBxLR(groups):
    containSpSubbedPattern = re.compile('bx\s+lr',re.IGNORECASE)
    matching_groups = []
    for group in groups:
        matches = switcher.searchInLines(containSpSubbedPattern,group)
        if len(matches)>0:
            matching_groups.append(group)
    return matching_groups




def run(path, start_group, end_group, DEBUG, config):
    print('DEBUG ', DEBUG)
    f = codecs.open(path+'.txt', 'r','utf-8', errors="ignore")
    lines = switcher.readLines(f)
    f.close()

    groups, addrFuncDict = switcher.getFunctions(lines)
    funcAddrDict = dict(zip(addrFuncDict.values(),addrFuncDict.keys()))

    g = switcher.handleExternalJumps(groups, conditions, funcAddrDict)

    #находим тип функций
    function_types = []
    if RETURN_TYPES:
        print('FUNCTIONS')
        function_types = parse_functions_utils.getFunctionsReturnTypeSize(addrFuncDict, config)
    #todo использовать числа при рандомизации
    # all_registers = ['r1', 'r2', 'r3', 'r4', 'r5', 'r6', 'r7', 'r8', 'r9', 'r10', 'r11']


    #ищем push, записываем для него все pop с теми же регистрами, пока не встретим новый push
    #или название функции <..>
    i = 0
    # groups = []
    # lst = []
    # while i < len(stack_lines)-1:
    #     if len(stack_lines[i]) == 2:
    #         #lst.append(stack_lines[i])
    #         i+=1
    #         continue
    #     probably_push = str(stack_lines[i][2])
    #     if probably_push.startswith('push') or probably_push.startswith('stmdb'):
    #         #lst = [stack_lines[i]]
    #         lst.append(stack_lines[i])
    #         j = i + 1
    #         while len(stack_lines[j]) > 2 \
    #                 and (str(stack_lines[j][2]).startswith("b") or ((str(stack_lines[j][2]).startswith('pop') or str(stack_lines[j][2]).startswith('ldmia')) \
    #                 and stack_lines[j][3] == stack_lines[i][3])):
    #             lst.append(stack_lines[j])
    #             j += 1
    #             if j >= len(stack_lines):
    #                 break
    #         if j - i > 1:
    #             groups.append(lst.copy())
    #             lst.clear()
    #         i = j
    #         lst.clear()
    #     else:
    #         i += 1
    init_group_len = len(groups)



    containSpSubbed = findSpSubbed(groups)
    print('Groups with subbed sp:', len(containSpSubbed))

    #difference = [g for g in groups if g not in f]

    #groups = switcher.hadleExternalJumps(groups)

    # фильтруем группы - убираем те, в которых последний pop нe pc
    print ('GROUPS:',  len(groups))


    print("Groups after jumps removing", len(groups))

    # gr = groups
    # groups = []
    # for group in gr:
    #     #if all(g[6]=='pc' for g in group[1:]):
    #     #берем только те функции, в которых нет pop lr
    #     #if len(group) > 1 and all(g[6]=='pc' for g in group[1:]):
    #     if len(group) > 1:
    #         groups.append(group)
    #     #if group[-1][6] == 'pc':
    #      #   groups.append(group)
    containBXLRbefore = findBxLR(groups)

    # check only one push
    # the same regs for push and pops
    groups = list(filter(None,[switcher.checkSuitable(g) for g in groups]))

    containBXLR = findBxLR(groups)
    print('CONTAINS BX LR:',len(containBXLR))

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
    for group in groups[start_group:end_group]: # 66 libcrypto - pop lr => bl - перезапись регистров
        #first, last = group[0], group[-1]
        push, pops = switcher.getPushes(group)[0], switcher.getPops(group)
        l+=1

        # добавляем регистры в начало, считает их количество
        real_reg_count = len(push.regs)
        return_size = function_types[push.addr] if RETURN_TYPES else 4
        new_registers, table = utils.addRegistersToStartAndEnd\
            (push.regs, push.bytes, return_size)
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
       # print(colored.setColored('{0}: '.format(key), colored.OKGREEN) + 'old {0}, new {1}'.format(push.regs, new_registers))
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











