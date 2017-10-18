# -*- coding: utf-8 -*-
import re, utils, r2.arm_translate,parse_functions_utils, static_functions_helper, config_parser, os
import cxxfilt, colored, sys, r2.parse, r2.utils
from r2.r2Helper import r2Helper

conditions = ['eq','ne','cs','hs','cc','lo','mi','pl','vs','vc','hi','ls','ge','lt','gt','le','al']
conditions_pattern = '|'.join(conditions)

NEW = False
RETURN_TYPES = True

def getPushAndRet(function):
    types = ['push','ret', 'pop']
    legal_pushpop_regs = ['lr','pc']
    new_rows = []
    push_added = False
    push_pattern = re.compile('(push|stmdb[a-z]*\s*sp!).*lr}')
    pop_pattern = re.compile('(pop|ldmia[a-z]*\s*sp!).*(pc|lr)}')
    ret_pattern = re.compile('bx.*lr')
    pushpop_pattern = re.compile('|'.join(x.pattern for x in [push_pattern,pop_pattern]))
    combined_pattern = re.compile('|'.join(x.pattern for x in [pushpop_pattern,ret_pattern]))
    for row in function.rows:
        # убираем строки до push - они не входят в рандомизаицю
        if push_pattern.search(row.opcode):
            push_added = True
        if not push_added:
            continue
        if pushpop_pattern.search(row.opcode):
        #if row.opcode.startswith('push') or row.opcode.startswith('pop'):
            row.opcode = row.opcode \
                .replace('sb', 'r9') \
                .replace('sl', 'r10') \
                .replace('fp', 'r11')
            regs = re.search('{.*}', row.opcode).group()[1:-1].replace(' ', '').split(',')
            row.regs = regs[:-1]
            row.reg = regs[-1]
        if combined_pattern.search(row.opcode):
            new_rows.append(row)

    if len(new_rows) == 0:
        return None
    return r2Helper.func_model(function.address, function.name, new_rows)

def checkOnlyOnePush(opcodes):
    return len([op for op in opcodes if op.type=='push'])==1

def checkPushAndPopsHaveTheSameRegs(opcodes):
    push = ''
    for op in opcodes:
        if op.type == 'push':
            push = op
        if op.opcode.startswith('pop') and op.regs!=push.regs:
            return False
    return True


def run(path, start_group, end_group, DEBUG, config):
    helper = r2Helper(path)
    functions = helper.getFunctions()

    #проверяем, можно ли сделать рандомизацию
    # есть ли push/pop с одинаковыми регистрами

    filtered_functions = {}
    for addr, function in functions.items():
        filtered_func = getPushAndRet(function)
        if filtered_func is None or \
                not checkOnlyOnePush(filtered_func.rows) or \
                not checkPushAndPopsHaveTheSameRegs(filtered_func.rows) or \
                len(filtered_func.rows)<2:
            continue
        filtered_functions[addr]=filtered_func


    #bx lr?
    #jumps

    init_group_len = len(filtered_functions)

    #difference = [g for g in groups if g not in f]

    if NEW:
        have_external_jumps = {}
        ext_jumps_list = {}
        external_jumps = []

        # убираем b, которые внутри функции
        for index, group in enumerate(groups):
            clear = [not group[i][2].startswith('b') for i in range(len(group)) if len(group[i]) > 2]
            if all(clear):
                continue
            first, last = group[0], group[-1]
            if len(first) == 2:
                first = group[1]
            if first[2].startswith('push') or first[2].startswith('stmdb'):
                    #and last[2].startswith('pop') or last[2].startswith('ldmia'):
                first_addr, last_addr  = int(first[0], 16), int(last[0], 16)
                has_ext_jumps = False
                jumps = []
                for g in [group[i] for i in range(len(group)) if group[i][2].startswith('b')]:
                    if re.search('lr|r[0-9|10|11|12]',g[3]) is not None:
                        continue
                    addr = int(g[3],16)
                    if g[3] == '5dec':
                        aaa=1
                    #if addr < first_addr or addr > last_addr:
                    if index!=len(groups)-1:
                        last_addr = int(groups[index+1][0][0],16)
                    if addr < first_addr or addr > last_addr:
                        has_ext_jumps = True
                        jumps.append(hex(addr))
                        #break
                if has_ext_jumps:
                        ext_jumps_list[index] = jumps
                        external_jumps.extend(jumps)
                        have_external_jumps[index] = group

        external_jumps = set(external_jumps)
        external_jumps_res = {}

        for jump in list(external_jumps):
            for index, row in enumerate(lines):
                address = utils.getAddressFromLine(row)
                # нашли строку, на которую jump
                if address == jump[2:]:
                    #проверяем, может прыгнули на push
                    push_method = re.search('push|stmdb', row)
                    if push_method is not None:
                        external_jumps_res[jump] = 'push'
                        continue
                    #идем вниз, ищем push/pop/b
                    for r in lines[index+1:]:
                        push_method = re.search('push|stmdb', r)
                        if push_method is not None:
                            #external_jumps.remove(jump)
                            external_jumps_res[jump] = 'push'
                            break
                        pop_method = re.search('pop|ldmia', r)
                        if pop_method is not None:
                            # опасно! надо что-то сделать!
                            # либо не обрабатывать эту функцию и все, которые на нее ссылаются по addr
                            # либо связать их и обрабатывать вместе
                            external_jumps_res[jump] = 'pop'
                            break
                        jump_method = re.search('\sb({0})?\s'.format(conditions_pattern), r)
                        if jump_method is not None:
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

    # фильтруем группы - убираем те, в которых последний pop нe pc
    print ('GROUPS:',  len(filtered_functions))

    if NEW:
        external_jumps_res = [addr for addr in external_jumps_res if external_jumps_res[addr]!='push']
        # убираем те, которые в have_external_jumps
        gr = groups
        groups = []
        removed_gr = 0
        for index, group in enumerate(gr):
            # если jump в этой группе, то ее тоже не обрабатываем
            first_addr, last_addr = group[0][0], gr[index+1][0][0] if index != len(gr)-1 else 0xFFFFFFFF
            handle = True
            for jump in external_jumps_res:
                if int(jump, 16) >= int(first_addr, 16) and int(jump, 16) <= int(last_addr, 16):
                    handle = False
                    removed_gr+=1
                    break
            if handle and index not in have_external_jumps.keys():
                #убираем b/beq/...
                group = [g for g in group if not g[2].startswith('b')]
                groups.append(group)

    print("Groups after jumps removing", len(filtered_functions))


    #добавляем в to_write (адрес, количество старых байт, новые байты) для перезаписи
    groups_count = 0
    to_write = []
    l = 0
    full_registers_count = 0
    #1935-36
    print(start_group, ":", end_group)

    regs_added = 0
    for addr, func in filtered_functions.items(): # 66 libcrypto - pop lr => bl - перезапись регистров
        push, last = func.rows[0], func.rows[-1]
        l+=1
        big_regs = ['sp', 'ip', 'lr', 'pc']
        try:
            if any(big_regs[i] in push.regs for i in range(len(big_regs))): #and (str(first[2]).startswith('push') or str(first[2]).startswith('stm')):
                    continue
        except:
            aaa=1

        # добавляем регистры в начало, считаем их количество
        real_reg_count = len(push.regs)
        #return_size = function_types[func.addr] if RETURN_TYPES else 4
        new_registers, table = utils.addRegistersToStartAndEnd(push.regs, push.opcode, 4)
        if new_registers == -1:
            full_registers_count+=1
            continue
        # меняем втутренние строки, взаимодействующие с sp
        #inner_lines = r2.parse.getAllSpLinesForLow(functions[addr].rows, table) todo uncomment
        inner_lines = []
        if inner_lines == -1:
            continue
        groups_count+=1
        # добавляем в to_write (адрес, количество старых байт, новые байты) push
        #print (first[0])

        new_code = r2.arm_translate.pushpopToCode(new_registers, r2.utils.prepare(push.bytes), push.size==2, real_reg_count, False)
        to_write.append((push.offset, push.size,r2.utils.toLittleEndian(new_code)))  # добавляем новый push

        # добавлаем все pop
        pops = [row for row in func.rows if row.opcode.startswith('pop')]
        for pop in pops:
            new_code = r2.arm_translate.pushpopToCode(new_registers, r2.utils.prepare(pop.bytes), pop.size==2, real_reg_count, True)
            to_write.append((pop.offset, pop.size,r2.utils.toLittleEndian(new_code)))  # добавляем новый pop

        if len(inner_lines) > 0:
            to_write.extend(inner_lines)
        key = functions[addr].name
        print(colored.setColored('{0}: '.format(key), colored.OKGREEN) + 'old {0}, new {1}'.format(push.regs, new_registers))
        regs_added += len(new_registers) - len(push.regs)
    secured = groups_count/init_group_len*100
    # output = 'End:{0}, full regs:{1}, secured:{2}%, average randomness:{3}'\
    #     .format(groups_count, full_registers_count, secured, regs_added/groups_count)

    output = 'End:{0}, full regs:{1}, secured:{2}%'\
        .format(groups_count, full_registers_count, secured)
    if groups_count>0:
        output += ", average randomness:{0}".format(regs_added/groups_count)

    colored.printColored(output, colored.BOLD)

    #переписываем файл
    f = open(path, 'br')
    text = f.read()
    f.close()

    for line in to_write:
        offset = int(line[0],16)
        text = text[:offset] + line[2] + text[offset+line[1]:]

    f = open(path+'.so', 'bw')
    f.write(text)
    f.close()





def combineFunction(stack_lines):
    functions = []
    items = []
    pops = ['pop','pop.w','ldmia','ldmia.w']

    def is_function_start(line):
        return len(line)==2 or line[2].startswith('push') or line[2].startswith('stmdb')

    for index, line in enumerate(stack_lines):
        if is_function_start(line):
            if line[0]=='ac28':
                aaa=1
            functions.append(items)
            items = []
            items.append(line)
            continue

        if (line[1]!='andeq'):
            items.append(line)

        if (line[2] in pops and line[6]=='pc')\
        or (line[2]=='bx' and line[3]=='lr') or line[1]=='andeq': #предполагаемый конец функции
            # посмотреть, есть ли прыжки дальше (до начала следующей функции)
            # прыжки = b(eq/...)
            # также конец функции только если неусловный pop и bx\

            #находим следующий push/stmdb
            ind, next_func_address = index+1, sys.maxsize
            while True:
                if ind >= len(stack_lines):
                    break
                if is_function_start(stack_lines[ind]):
                    next_func_address = int(stack_lines[ind][0],16)
                    break
                ind+=1

            jumps, func_end = [], int(line[0],16)
            for item in [i for i in items if len(i)>2]:
                if item[2].startswith('b') and not re.match('lr|pc|(r[0-9]*)',item[3]):
                    jump_to = int(item[3],16)
                    if  func_end < jump_to < next_func_address:
                        jumps.append(item[3])
            if len(jumps)==0: # если нет, то конец функции
                functions.append(items)
                items = []
            else: #todo содержит прыжки, посмотерть, выходят ли они за пределы pop pc до push
                # если выходят, то не конец фнукции, идем дальше
                jumps = []
                continue

    filtered = []
    for f in functions:
        if len(f)<2 or len(f[0])<3 or not (f[0][2].startswith('push') or f[0][2].startswith('stmdb')):
            continue
        push_regs, success = f[0][3], True
        for pop in f:
            #убираем функции, в котрых регистры в push и pop разные
            if (pop[2].startswith('pop') or pop[2].startswith('ldmia')) and pop[3]!=push_regs:
                success = False
                break
        if success:
            filtered.append(f)
    return filtered






