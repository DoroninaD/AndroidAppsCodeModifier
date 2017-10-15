# -*- coding: utf-8 -*-
import re, utils, arm_translate, parse,parse_functions_utils, static_functions_helper, config_parser, os
import cxxfilt, colored, sys

conditions = ['eq','ne','cs','hs','cc','lo','mi','pl','vs','vc','hi','ls','ge','lt','gt','le','al']
conditions_pattern = '|'.join(conditions)

NEW = True
RETURN_TYPES = True
def run(path, start_group, end_group, DEBUG, config):
    print('DEBUG ', DEBUG)
    f = open(path+'.txt', 'r')
    lines = f.readlines()
    indices = [i for i, s in enumerate(lines) if '.text' in s]
    lines = lines[indices[0]:]
    f.close()

    stack_lines = []

    index = 0
    # выбираем только строки с push/pop, разбираем их на составляющие
    # Также ищем названия функций <func>:
    function_name = ''
    functions = dict() # адрес - функция
    for line in lines:
        is_function_name = re.search('<.*>:', line)
        if is_function_name is not None:
            function_name = is_function_name.group()[1:-2]
            if NEW:
                address = utils.getAddressFromLine(line)
                stack_lines.append((address,function_name))
        if NEW:
            andeq = re.search('andeq', line)
            if andeq is not None:
                stack_lines.append((address, "andeq", "null"))

        #stack_line = re.match('.*((push(.w)?|stmdb(.w)?\s*sp!).*lr}|(pop[a-z]*|ldmia[a-z]*\s*sp!).*(pc|lr)}).*', line)
        stack_line = re.match('.*((push|stmdb[a-z]*\s*sp!).*lr}|(pop|ldmia[a-z]*\s*sp!).*(pc|lr)}).*', line)

        if NEW:
            branch_line = re.match('.*\s(bx|b)({0})?\s.*'.format(conditions_pattern), line)
            if branch_line is not None:
                address = utils.getAddressFromLine(line)
                if address == '3db8':
                    aaa = 1
                code, is_thumb = utils.getCodeFromLine(line)
                jumpto = re.search('\s(bx|b)({0})?\s[0-9a-z]+'.format(conditions_pattern),branch_line.group()).group().split()[-1]
                method = re.search('\s(bx|b)({0})?'.format(conditions_pattern),branch_line.group()).group().strip()
                stack_lines.append((address, code, method, jumpto, is_thumb, index))
        if stack_line is not None:
            method = re.search('(push|stmdb|pop|ldmia)[a-z]*', line).group()
            # берем все регистры в {} и убираем последний (это lr или pc)
            # в дальнешем будем исключать строки, в которых есть регистры > r11
            #registers = re.search('{.*}', line).group().replace('}','').replace('{','').replace(' ','').split(',')[:-1]
            registers = re.search('{.*}', line).group().replace('}','').replace('{','').replace(' ','').split(',')
            last_reg = registers[-1]
            #registers = re.findall("r11|r10|r[1-9]|sp", stack_line.group())
            # убираем лишний sp (sp!)
            #if (method.startswith('stm') or method.startswith('ldm')) and 'sp' in registers:
            #    registers.remove('sp')
            address = utils.getAddressFromLine(line)
            code, is_thumb = utils.getCodeFromLine(line)
            stack_lines.append((address, code, method, registers[:-1], is_thumb, index, last_reg))
            if re.search('pop(.w)?|ldmia(.w)?', method) is None:
                functions[address] = function_name.split('@')[0]
            function_name = ''
        index += 1

    # выделяем функции, для которых нет имени
    if RETURN_TYPES:
        noname_functions = dict((addr, func) for addr, func in functions.items() if func == '')
        if len(noname_functions) > 0:
            nonstatic_folder = config.get('nonstatic_app_directory')
            nonstatic_file = os.path.join(nonstatic_folder, os.path.basename(path)+'.txt')

            newNames = dict((addr, func) for addr, func in noname_functions.items() if func!='')

            while True and os.path.exists(nonstatic_file):
                noname_len = len(noname_functions)
                for addr in list(noname_functions):
                    name = static_functions_helper.getName(lines, addr, nonstatic_file, newNames)
                    if name != '':
                        newNames[addr] = name
                        noname_functions.pop(addr)
                if len(noname_functions) == noname_len:
                    break

            for addr in newNames:
                functions[addr] = newNames[addr]

    groups = combineFunction(stack_lines)

    #находим тип функций
    function_types = []
    if RETURN_TYPES:
        print('FUNCTIONS')
        function_types = parse_functions_utils.getFunctionsReturnTypeSize(functions, config)
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
    print ('GROUPS:',  len(groups))

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

    print("Groups after jumps removing", len(groups))

    gr = groups
    groups = []
    for group in gr:
        #if all(g[6]=='pc' for g in group[1:]):
        #берем только те функции, в которых нет pop lr
        #if len(group) > 1 and all(g[6]=='pc' for g in group[1:]):
        if len(group) > 1:
            groups.append(group)
        #if group[-1][6] == 'pc':
         #   groups.append(group)



    #groups = [group for group in groups if group[i][6]=='pc' for i in range(1,len(group))]
    print ('Groups after pop lr removing:', len(groups))

    #добавляем в to_write (адрес, количество старых байт, новые байты) для перезаписи
    groups_count = 0
    to_write = []
    l = 0
    full_registers_count = 0
    #1935-36
    print(start_group, ":", end_group)

    regs_added = 0
    for group in groups[start_group:end_group]: # 66 libcrypto - pop lr => bl - перезапись регистров
        first, last = group[0], group[-1]
        addr = first[0]
        l+=1
        big_regs = ['sp', 'ip', 'lr', 'pc', 'r12']
        if any(big_regs[i] in first[3] for i in range(len(big_regs))): #and (str(first[2]).startswith('push') or str(first[2]).startswith('stm')):
                    continue

        # добавляем регистры в начало, считает их количество
        real_reg_count = len(first[3])
        return_size = function_types[addr] if RETURN_TYPES else 4
        new_registers, table = utils.addRegistersToStartAndEnd(first[3], first[1], return_size)
        if new_registers == -1:
            full_registers_count+=1
            continue
        # меняем втутренние строки, взаимодействующие с sp
        try:
            inner_lines = parse.getAllSpLinesForLow(lines[first[5] + 1:last[5]], table)
        except:
            aaa=1
        if inner_lines == -1:
            continue
        groups_count+=1
        # добавляем в to_write (адрес, количество старых байт, новые байты) push
        #print (first[0])

        to_write.append((first[0], len(first[1]) // 2,
                         utils.toLittleEndian(arm_translate.pushpopToCode(new_registers, first[1], first[4], real_reg_count, False))))  # добавляем новый push

        # добавлаем все pop
        for a in group[1:]:
           to_write.append((a[0], len(a[1]) // 2,
                            utils.toLittleEndian(
                                arm_translate.pushpopToCode(new_registers, a[1], a[4], real_reg_count, True))))  # добавляем новый pop

        if len(inner_lines) > 0:
            to_write.extend(inner_lines)
        key = cxxfilt.demangle(functions[addr]) if functions[addr]!='' else addr
        print(colored.setColored('{0}: '.format(key), colored.OKGREEN) + 'old {0}, new {1}'.format(first[3], new_registers))
        regs_added += len(new_registers) - len(first[3])
    secured = groups_count/init_group_len*100
    # output = 'End:{0}, full regs:{1}, secured:{2}%, average randomness:{3}'\
    #     .format(groups_count, full_registers_count, secured, regs_added/groups_count)

    output = 'End:{0}, full regs:{1}, secured:{2}%'\
        .format(groups_count, full_registers_count, secured)
    if groups_count>0:
        output += ", average randomness:{0}".format(regs_added/groups_count)

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






