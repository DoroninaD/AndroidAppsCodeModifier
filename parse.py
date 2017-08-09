#! /usr/bin/env python
# -*- coding: utf-8 -*-
import re, arm_translate, utils


def getRxLines(lines, line, table, sp_subbed, sub_ind):
    #line = add_sp_to_reg[0].group()
    c = re.search('#[0-9]+', line)
    c = 0 if c is None else int(c.group()[1:])
    reg = re.search('r11|r10|r12|r[0-9]', line).group()

    #определяем строку, с которой будем искать строки вида [reg, #d]
    start_ind = list(lines).index(line+'\n')

    # предполагаем, что изменение sp происходит только в начале и конце функции todo
    # если sp еще не отнят, тогда не нужно учитывать a
    if start_ind < sub_ind:
        sp_subbed = 0

    # end_reg = list(filter(None,
    #                       [re.search('.*(mov(eq|ne)?|(v)?ldr(b|h|sb|sh|sw)?|add)(.w)?\s{0}, .*'.format(reg), line) for
    #                        line in lines[start_ind+1:]]))
    end_reg = utils.searchRe('.*(mov(eq|ne)?|(v)?ldr(b|h|sb|sh|sw)?|add)(.w)?\s{0}, .*'.format(reg),lines[start_ind+1:])
    #определяем строку, ДО которой будем искать строки вида [reg, #d] (mov затирает sp)
    end_ind = list(lines).index(end_reg[0].group()+'\n') if len(end_reg) > 0 else len(lines)

    to_write = []
    # Ищем строки вида [reg, #d]
    # use_reg = list(filter(None,
    #                       [re.search('.*(ldr|str)(b|h|sb|sh|sw|d)?(.w)?.*\[{0}(, #\-?[0-9]+\])?'.format(reg), line) for
    #                        line in lines[start_ind:end_ind]]))

    # ... [rx]
    use_reg = utils.searchRe('.*(ldr|str)(b|h|sb|sh|sw|d)?(.w)?.*\[{0}(, #\-?[0-9]+\])?'.format(reg), lines[start_ind:end_ind])

    d = 0
    #todo если будет str rx, [sp, #] и уже добавлен в to_write по sp, будет перезаписано?
    for l in use_reg:
        instr = re.search('v?(ldr|str)(b|h|sb|sh|d)?(.w)?', l.group()).group()
        try_d = re.search('#-?[0-9]+', l.group())
        d = int(try_d.group().replace('#', '')) if try_d is not None else 0
        # если d < 0 => если c-d<0 =>[reg, #d-new_regs_count*4]
        n = c + d - sp_subbed
        if n >= 0:  # todo а что если будет sub rx, sp?
            rx = re.search('(\s+r10|r11|r12|sp|lr|pc|r[0-9]|((d|s)(([1-2][0-9])|3[0-1]|[0-9]))),',
                           l.group()).group().strip().replace(',', '')
            code, is_thumb = utils.getCodeFromLine(l.group())
            offset = changeOffset(n, d, table)
            #offset = d + before_reg_count * 4
            #if n >= real_reg_count * 4:
            #    offset += after_reg_count * 4
            new_instr_code = arm_translate.makeLdrOrStr(instr, code, rx, reg, offset, is_thumb, l.group())
            # to_write ... [reg, #d-new_regs_count*4]

            to_write.append((utils.getAddressFromLine(l.group()), len(code) // 2, utils.toLittleEndian(new_instr_code)))

    # str rx, [...]
    str_reg = list(filter(None,[re.search('.*str(b|h|sb|sh|sw|d)?(.w)?\s{0}.*'.format(reg), line)for line in lines[start_ind:end_ind]]))
    if  len(str_reg) > 0:
       return -1
    return to_write


def getAllSpLinesForLow(lines, table):
    to_write = []

    # ldr/str/... rx, [sp], ry - не знаем значение ry, не можем сделать правильное смещение => не обрабатываем такие функции
    register_relative = utils.searchRe('.*(ldr|str).*\[.*\], ', lines)
    if len(register_relative) > 0:
        return  -1


    # не обрабатываем функции, в которых есть дополнительные push
    more_pushes = utils.searchRe('.*\d}', lines)
    if len(more_pushes) > 0:
        return -1


    # ищем строки sub (add) sp, #a => sub (add) sp, #a+new_regs_count*4 => to_write
    #sub_add_sp_lines = list(filter(None,[re.search('.*(add|sub)(.w)?\s*sp(, sp)?, #[0-9]+', line) for line in lines]))
    sub_add_sp_lines = utils.searchRe('.*(add|sub)(.w)?\s*sp(, sp)?, #[0-9]+', lines)
    # если строки нет, выходим (потом подумать,как сделать) todo
    #if len(sub_add_sp_lines) < 2: #не нашли sub и add
        #return []


    if len(sub_add_sp_lines) != 0:
        try:
            sub_ind = lines.index([s for s in lines if str(s).startswith(sub_add_sp_lines[0].group())][0])
        except:
            sub_ind = lines.index(sub_add_sp_lines[0].group() + '\n')
        a = int(sub_add_sp_lines[0].group().split('#')[-1])
    else:
        a = 0
        sub_ind = 0

    #ищем строки вида [sp, #b]
   #use_sp_lines = list(filter(None,[re.search('.*(ldr|str)(b|h|sb|sh|d)?(.w)?.*\[sp, #[0-9]+\].*', line) for line in lines]))
    use_sp_lines = utils.searchRe('.*(ldr|str)(b|h|sb|sh|d)?(.w)?.*\[sp, #[0-9]+\].*', lines)
    #todo
    #for i in use_sp_lines:
        #print(i.group())
    if len([s for s in use_sp_lines if '!' in str(s.group())])>0:
        return -1



    for l in use_sp_lines:
        instr = re.search('v?(ldr|str)(b|h|sb|sh|d)?(.w)?',l.group()).group()
        b = int(re.search('#[0-9]+', l.group()).group().replace('#',''))
        if b-a >= 0:
            rx = re.search('(\s+r10|r11|r12|sp|lr|pc|r[0-9]|((d|s)(([1-2][0-9])|3[0-1]|[0-9]))),', l.group()).group().strip().replace(',','')
            code, is_thumb = utils.getCodeFromLine(l.group())
            offset = changeOffset(b-a, b,  table)
            new_instr_code = arm_translate.makeLdrOrStr(instr,code , rx, 'sp', offset, is_thumb, l.group())
            # to_write ... [sp, #b + new_regs_count*4]
            to_write.append((utils.getAddressFromLine(l.group()), len(code) // 2, utils.toLittleEndian(new_instr_code)))

    #ищем строки вида add rx, sp, (#c) - должна быть одна ? todo
    #add_sp_to_reg = list(filter(None, [re.search('.*(add(.w)?|mov)\s*(r[0-9]|r10|r11|r12), sp(, #[1-9]+)?.*', line) for line in lines]))
    add_sp_to_reg = utils.searchRe('.*(add(.w)?|mov)\s*(r[0-9]|r10|r11|r12), sp(, #[1-9]+)?.*', lines)
    #todo
    #for i in add_sp_to_reg:
       # print(i.group())
    if len([s for s in add_sp_to_reg if '!' in str(s.group())])>0:
        return -1

    if len(add_sp_to_reg) > 0:
        for l in add_sp_to_reg:
            new = getRxLines(lines, l.group(), table, a, sub_ind)
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
