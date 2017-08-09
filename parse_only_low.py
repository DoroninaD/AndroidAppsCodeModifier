import re, arm_translate, utils

def getAllSpLinesForLow(lines, new_regs_count):
    to_write = []

    # ищем строки sub (add) sp, #a => sub (add) sp, #a+new_regs_count*4 => to_write
    sub_add_sp_lines = list(filter(None,[re.search('.*(add|sub)(.w)?\s*sp, #[0-9]+', line) for line in lines]))

    # если строки нет, выходим (потом подумать,как сделать) todo
    if len(sub_add_sp_lines) !=2: #не нашли sub и add
        return []

    a = int(sub_add_sp_lines[0].group().split('#')[-1])
    # new_a = int(a)+new_regs_count*4
    #
    # #вычитаем new_regs_count*4 из sub
    # sub_instr = arm_translate.subSpToCode(new_a)
    # sub_line = sub_add_sp_lines[0].group()
    # sub_address = utils.getAddressFromLine(sub_line)
    # sub_code = utils.getCodeFromLine(sub_line)
    # to_write.append((sub_address, len(sub_code) // 2, utils.toLittleEndian(sub_instr)))
    #
    # # добавляем new_regs_count*4 в add
    # add_instr = arm_translate.addSpToCode(new_a)
    # add_line = sub_add_sp_lines[1].group()
    # add_address = utils.getAddressFromLine(add_line)
    # add_code = utils.getCodeFromLine(add_line)
    # to_write.append((add_address, len(add_code) // 2, utils.toLittleEndian(add_instr)))

    #ищем строки вида [sp, #b]
    use_sp_lines = list(filter(None,[re.search('.*(ldr|str)(b|h|sb|sh)?(.w)?.*\[sp, #[0-9]+\]', line) for line in lines]))
    for l in use_sp_lines:
        instr = re.search('v?(ldr|str)(b|h|sb|sh)?(.w)?',l.group()).group()
        b = int(re.search('#[0-9]+', l.group()).group().replace('#',''))
        # если b-a >= -new_regs_count*4 => [sp, #b + new_regs_count*4] => to_write - иначе ничего
        if b >= a:
            rx = re.search('(\s+r10|r11|r12|sp|lr|pc|r[0-9]|((d|s)(([1-2][0-9])|3[0-1]|[0-9]))),', l.group()).group().strip().replace(',','')
            code, is_thumb = utils.getCodeFromLine(l.group())
            new_instr_code = arm_translate.makeLdrOrStr(instr,code , rx, 'sp', b+new_regs_count*4, is_thumb)
            # to_write ... [sp, #b + new_regs_count*4]
            to_write.append((utils.getAddressFromLine(l.group()), len(code) // 2, utils.toLittleEndian(new_instr_code)))

    #ищем строки вида add rx, sp, (#c) - должна быть одна ? todo
    add_sp_to_reg = list(filter(None, [re.search('.*(add|mov)\s*(r[1-9]|r10|r11|r12), sp(, #[1-9]+)?', line) for line in lines]))
    if len(add_sp_to_reg) > 0:
        if len(add_sp_to_reg) > 1:
            #raise Exception('Больше одной строки add rx, sp, (#c)')
            return []
        line = add_sp_to_reg[0].group()
        c = re.search('#[1-9]+', line)
        c = 0 if c is None else int(c.group()[1:])
        reg = re.search('r[1-9]|r11|r10|r12',line).group()

        # Ищем строки вида [reg, #-d]
        use_reg = list(filter(None, [re.search('.*(ldr|str)(b|h|sb|sh|sw)?(.w)?.*\\[{0}, #\\-?[0-9]+\\]'.format(reg), line) for line in lines]))
        for l in use_reg:
            instr = re.search('v?(ldr|str)(b|h|sb|sh)?(.w)?',l.group()).group()
            d = int(re.search('#-?[0-9]+', l.group()).group().replace('#',''))
            # если d < 0 => если c-d<0 =>[reg, #d-new_regs_count*4]
            if c + d >= 0: #todo а что если будет sub rx, sp?
                rx = re.search('(\s+r10|r11|r12|sp|lr|pc|r[0-9]|((d|s)(([1-2][0-9])|3[0-1]|[0-9]))),',
                               l.group()).group().strip().replace(',', '')
                code, is_thumb = utils.getCodeFromLine(l.group())
                new_instr_code = arm_translate.makeLdrOrStr(instr, code, rx, reg, d + new_regs_count * 4, is_thumb)
                #to_write ... [reg, #d-new_regs_count*4]
                to_write.append((utils.getAddressFromLine(l.group()), len(code) // 2, utils.toLittleEndian(new_instr_code)))

    #for i in to_write:
        #print(i)
    return to_write