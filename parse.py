#! /usr/bin/env python
# -*- coding: utf-8 -*-
import re, arm_translate, utils, switcher
conditions = ['eq','ne','cs','hs','cc','lo','mi','pl','vs','vc','hi','ls','ge','lt','gt','le','al']


def getRxLines1(lines, line, table, sp_subbed, sub_ind):
    #line = add_sp_to_reg[0].group()
    c = switcher.getNumber(line)
    if c is None:
        return -1
    #c = 0 if not c else int(c.group()[1:],16) if "0x" in c.group() else int(c.group()[1:])
    regsPattern = re.compile('r11|r10|r12|r[0-9]', re.IGNORECASE)
    reg = switcher.searchPattern(regsPattern, line).group()

    #определяем строку, с которой будем искать строки вида [reg, #d]
    start_ind = list(lines).index(line)

    # предполагаем, что изменение sp происходит только в начале и конце функции todo
    # если sp еще не отнят, тогда не нужно учитывать a
    if start_ind < sub_ind:
        sp_subbed = 0

    # end_reg = list(filter(None,
    #                       [re.search('.*(mov(eq|ne)?|(v)?ldr(b|h|sb|sh|sw)?|add)(.w)?\s{0}, .*'.format(reg), line) for
    #                        line in lines[start_ind+1:]]))
    clearRegPattern = re.compile\
        ('.*(mov(eq|ne)?|(v)?ldr(b|h|sb|sh|sw)?|add)(.w)?\s{0},\s?.*'.format(reg),
         re.IGNORECASE)
    end_reg = switcher.searchInLines(clearRegPattern,lines[start_ind+1:])

    #определяем строку, ДО которой будем искать строки вида [reg, #d] (mov затирает sp)
    end_ind = list(lines).index(end_reg[0].group()) if len(end_reg) > 0 else len(lines)

    to_write = []
    # Ищем строки вида [reg, #d]
    # use_reg = list(filter(None,
    #                       [re.search('.*(ldr|str)(b|h|sb|sh|sw|d)?(.w)?.*\[{0}(, #\-?[0-9]+\])?'.format(reg), line) for
    #                        line in lines[start_ind:end_ind]]))

    # ... [rx]
    useRegPattern = re.compile\
        ('.*(ldr|str)(b|h|sb|sh|sw|d)?(.w)?.*\[{0}(,\s?#\-?(0x)?[0-9a-f]+.*\])?'.format(reg),
         re.IGNORECASE)
    use_reg = switcher.searchInLines(useRegPattern, lines[start_ind:end_ind])


    d = 0
    #todo если будет str rx, [sp, #] и уже добавлен в to_write по sp, будет перезаписано?
    for l in use_reg:
        pattern = re.compile('v?(ldr|str)(b|h|sb|sh|d)?(.w)?',re.IGNORECASE)
        instr = switcher.searchPattern(pattern, l).group()
        d = switcher.getNumber(l)
        if d is None:
            return -1
        #try_d = re.search('#-?[0-9]+', l.group())
        #d = int(try_d.group().replace('#', '')) if try_d is not None else 0
        # если d < 0 => если c-d<0 =>[reg, #d-new_regs_count*4]
        n = c + d - sp_subbed
        if n >= 0:  # todo а что если будет sub rx, sp?
            pattern = re.compile('(\s+r10|r11|r12|sp|lr|pc|r[0-9]|((d|s)(([1-2][0-9])|3[0-1]|[0-9]))),', re.IGNORECASE)
            rx = switcher.searchPattern(pattern, l).group().strip().replace(',', '')
            #code, is_thumb = utils.getCodeFromLine(l.group())
            offset = changeOffset(n, d, table)
            #offset = d + before_reg_count * 4
            #if n >= real_reg_count * 4:
            #    offset += after_reg_count * 4
            new_instr_code = arm_translate.makeLdrOrStr(instr, l.bytes, rx, reg, offset, l.thumb, l.line)
            # to_write ... [reg, #d-new_regs_count*4]

            to_write.append((l.addr, len(l.bytes) // 2, utils.toLittleEndian(new_instr_code)))

    # str rx, [...]
    strRegPattern = re.compile('.*str(b|h|sb|sh|sw|d)?(.w)?\s{0}.*'.format(reg), re.IGNORECASE)
    str_reg = switcher.searchInLines(strRegPattern, lines[start_ind:end_ind])
    if len(str_reg) > 0:
       return -1
    return to_write


def getRxLines(lines, line, table, sp_subbed, sub_ind):
    llll = []
    def getJumpIndex(line):
        try:
            jmpAddr = tmp[commonJMPPattern.search(line).end():].strip().split(';')[0]
        except:
            aaa=1
        jmpAddr = re.sub('[a-z]+_', '0x', jmpAddr).lower()
        try:
            int(jmpAddr, 16)
        except:
            return None
        try_ind = [l for l in lines if l.addr == jmpAddr]
        if len(try_ind)==0:
            return None
        return lines.index(try_ind[0])


    def handleLine(index,line):
        llll.append((index,line))
    c = switcher.getNumber(line)
    if c is None:
        return -1
    regsPattern = re.compile('r11|r10|r12|r[0-9]', re.IGNORECASE)
    reg = switcher.searchPattern(regsPattern, line).group()
    useRegPattern = re.compile\
        ('.*(ldr|str)(b|h|sb|sh|sw|d)?(.w)?.*\[{0}(,\s?#\-?(0x)?[0-9a-f]+.*\])?'.format(reg),
         re.IGNORECASE)
    clearRegPattern = re.compile \
        ('.*(mov(eq|ne)?|(v)?ldr(b|h|sb|sh|sw)?|add)(.w)?\s{0},\s?.*'.format(reg),
         re.IGNORECASE)
    simpleJMPPattern = re.compile('\sbl?s?(\.w)?\s', re.IGNORECASE)
    regJumpPattern = re.compile('\sbl?x\s', re.IGNORECASE)
    conditionJumpPattern = re.compile('\s((cbz)|(b(l)?({0})))\s'.format('|'.join(conditions)),re.IGNORECASE)
    commonJMPPattern = re.compile('\s((cbn?z)|(bl?s?({0})?))(\.w)?\s'.format('|'.join(conditions)),re.IGNORECASE)
    #определяем строку, с которой будем искать строки вида [reg, #d]
    start_ind = list(lines).index(line)


    ways, old_ways = [start_ind], [start_ind]
    while(len(ways)>0):
        i = ways[0]
        end_reg = switcher.searchInLines(clearRegPattern, lines[i + 1:])
        # определяем строку, ДО которой будем искать строки вида [reg, #d] (mov затирает sp)
        end_ind = list(lines).index(end_reg[0].group()) if len(end_reg) > 0 else len(lines)
        for l in lines[i:end_ind]:
            tmp = l.line
            if useRegPattern.search(tmp):
                handleLine(i,l)
            if simpleJMPPattern.search(tmp):
                index = getJumpIndex(tmp)
                if index is not None and index not in old_ways:
                    old_ways.append(index)
                    ways.append(index)
                break
            if conditionJumpPattern.search(tmp):
                try:
                    index = getJumpIndex(tmp)
                except:
                    index = getJumpIndex(tmp)
                if index is None:
                    break
                if index not in old_ways:
                    old_ways.append(index)
                    ways.append(index)
        ways.remove(i)

    # предполагаем, что изменение sp происходит только в начале и конце функции todo
    # если sp еще не отнят, тогда не нужно учитывать a



    to_write = []
    # Ищем строки вида [reg, #d]
    # use_reg = list(filter(None,
    #                       [re.search('.*(ldr|str)(b|h|sb|sh|sw|d)?(.w)?.*\[{0}(, #\-?[0-9]+\])?'.format(reg), line) for
    #                        line in lines[start_ind:end_ind]]))

    # ... [rx]

    #use_reg = switcher.searchInLines(useRegPattern, lines[start_ind:end_ind])


    #todo если будет str rx, [sp, #] и уже добавлен в to_write по sp, будет перезаписано?
    for item in llll:
        start_ind, l = item[0],item[1]
        if start_ind < sub_ind:
            sp_subbed = 0
        pattern = re.compile('v?(ldr|str)(b|h|sb|sh|d)?(.w)?',re.IGNORECASE)
        instr = switcher.searchPattern(pattern, l).group()
        d = switcher.getNumber(l)
        if d is None:
            return -1
        n = c + d - sp_subbed
        if n >= 0:  # todo а что если будет sub rx, sp?
            pattern = re.compile('(\s+r10|r11|r12|sp|lr|pc|r[0-9]|((d|s)(([1-2][0-9])|3[0-1]|[0-9]))),', re.IGNORECASE)
            rx = switcher.searchPattern(pattern, l).group().strip().replace(',', '')
            offset = changeOffset(n, d, table)
            new_instr_code = arm_translate.makeLdrOrStr(instr, l.bytes, rx, reg, offset, l.thumb, l.line)
            to_write.append((l.addr, len(l.bytes) // 2, utils.toLittleEndian(new_instr_code)))

    # str rx, [...]
    strRegPattern = re.compile('.*str(b|h|sb|sh|sw|d)?(.w)?\s{0}.*'.format(reg), re.IGNORECASE)
    str_reg = switcher.searchInLines(strRegPattern, lines[start_ind:end_ind])
    if len(str_reg) > 0:
       return -1
    return to_write


def getAllSpLinesForLow(lines, table):
    to_write = []

    # ldr/str/... rx, [sp], ry - не знаем значение ry, не можем сделать правильное смещение => не обрабатываем такие функции
    register_relative = switcher.getRelativeRegs(lines)
    if len(register_relative) > 0:
        return  -1


    # не обрабатываем функции, в которых есть дополнительные push
    more_pushes = switcher.searchInLines(re.compile('.*\d}',re.IGNORECASE),lines)
    if len(more_pushes) > 0:
        return -1



    # не обрабатываем функции, в которых есть дополнительные push
    # more_pushes = utils.searchRe('.*\d}', lines)
    # if len(more_pushes) > 0:
    #     return -1


    # ищем строки sub (add) sp, #a => sub (add) sp, #a+new_regs_count*4 => to_write
    #sub_add_sp_lines = list(filter(None,[re.search('.*(add|sub)(.w)?\s*sp(, sp)?, #[0-9]+', line) for line in lines]))
    addSubPattern = re.compile('.*(add|sub)(.w)?\s*sp(,\s?sp)?,\s?#[0-9]+', re.IGNORECASE)
    #sub_add_sp_lines = utils.searchPattern(addSubPattern, lines)
    sub_add_sp_lines = switcher.searchInLines(addSubPattern, lines)
    # если строки нет, выходим (потом подумать,как сделать) todo
    #if len(sub_add_sp_lines) < 2: #не нашли sub и add
        #return []


    if len(sub_add_sp_lines) != 0:
        sub_ind = lines.index(sub_add_sp_lines[0])
        # pattern = re.compile('#(0x)?[0-9a-f]+',re.IGNORECASE)
        # a = switcher.searchPattern(pattern, sub_add_sp_lines[0]).group()[1:]
        # a = int(a,16) if '0x' in a else int(a)
        a = switcher.getNumber(sub_add_sp_lines[0])
        if a is None:
            return -1

        #a = int(re.search('#(0x)?[0-9a-f]+',sub_add_sp_lines[0], re.IGNORECASE).group(), 16)
    else:
        a = 0
        sub_ind = 0

    #ищем строки вида [sp, #b]
   #use_sp_lines = list(filter(None,[re.search('.*(ldr|str)(b|h|sb|sh|d)?(.w)?.*\[sp, #[0-9]+\].*', line) for line in lines]))
    useSpPattern = re.compile('.*(ldr|str)(b|h|sb|sh|d)?(.w)?.*\[sp,\s?#-?(0x)?[0-9a-f]+.*\].*',re.IGNORECASE)
    use_sp_lines = switcher.searchInLines(useSpPattern, lines)
    #todo
    #for i in use_sp_lines:
        #print(i.group())
    if any(['!' in l.line for l in use_sp_lines]):
    #if len([s for s in use_sp_lines if '!' in str(s.group())])>0:
        return -1

    for l in use_sp_lines:
        LdrStrPattern = re.compile('v?(ldr|str)(b|h|sb|sh|d)?(.w)?',re.IGNORECASE)
        instr = switcher.searchPattern(LdrStrPattern, l).group().lower()
        b = switcher.getNumber(l)
        if b is None:
            return -1

        #b = int(re.search('#[0-9]+', l.group()).group().replace('#',''))
        if b-a >= 0:
            pattern = re.compile\
                ('(\s+r10|r11|r12|sp|lr|pc|r[0-9]|((d|s)(([1-2][0-9])|3[0-1]|[0-9]))),', re.IGNORECASE)
            rx = switcher.searchPattern(pattern, l).group().strip().replace(',','')
            #code, is_thumb = utils.getCodeFromLine(l.group())
            offset = changeOffset(b-a, b,  table)
            new_instr_code = arm_translate.\
                makeLdrOrStr(instr,l.bytes , rx.lower(), 'sp', offset, l.thumb, l.line)
            # to_write ... [sp, #b + new_regs_count*4]
            to_write.append((l.addr,
                         len(l.bytes) // 2, utils.toLittleEndian(new_instr_code)))


    #ищем строки вида add rx, sp, (#c) - должна быть одна ? todo
    #add_sp_to_reg = list(filter(None, [re.search('.*(add(.w)?|mov)\s*(r[0-9]|r10|r11|r12), sp(, #[1-9]+)?.*', line) for line in lines]))
    addSpToRegPattern = re.compile\
        ('.*(add(.w)?|mov)\s*(r[0-9]|r10|r11|r12),\s?sp(,\s?#[1-9]+)?.*', re.IGNORECASE)
    add_sp_to_reg = switcher.searchInLines(addSpToRegPattern, lines)
    #todo
    #for i in add_sp_to_reg:
       # print(i.group())
    #if len([s for s in add_sp_to_reg if '!' in str(s.group())])>0:
    if any(['!' in l.line for l in add_sp_to_reg]):
        return -1

    if len(add_sp_to_reg) > 0:
        for l in add_sp_to_reg:
            new = getRxLines(lines, l, table, a, sub_ind)
            if new == -1:
                return -1
            to_write.extend(new)

    return to_write


def changeOffset(offset, cur, table):   # offset - общее смещение
    if offset < 0:                      # cur - локальное смещение
        return cur                      # table - переменная типа словарь,
    max_key = max(table.keys())         # в котором хранятся соотвествия старых
    if offset > max_key:                # и новых смещений
        return cur + table[max_key]
    return table[offset//4*4]
