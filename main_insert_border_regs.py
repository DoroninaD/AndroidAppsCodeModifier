# -*- coding: utf-8 -*-
import re, utils, arm_translate, parse,parse_functions_utils, static_functions_helper, config_parser, os



def run(path, start_group, end_group, DEBUG):
    print('DEBUG ', DEBUG)
    f = open(path+'.txt', 'r')
    lines = f.readlines()
    indices = [i for i, s in enumerate(lines) if '.text' in s]
    lines = lines[indices[0]:]
    f.close()

    config = config_parser.ConfigParser()

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
        stack_line = re.match('.*((push(.w)?|stmdb(.w)?\s*sp!).*lr}|(pop(.w)?|ldmia(.w)?\s*sp!).*(pc|lr)}).*', line)
        if stack_line is not None:
            method = re.search('push(.w)?|stmdb(.w)?|pop(.w)?|ldmia(.w)?', line).group()
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
    noname_functions = dict((addr, func) for addr, func in functions.items() if func == '')
    if len(noname_functions) > 0:
        nonstatic_folder = config.get('nonstatic_app_directory')
        nonstatic_file = os.path.join(nonstatic_folder, os.path.basename(path)+'.txt')
        for addr in noname_functions:
            #if addr == '1e3c':
            if addr == '678':
                aaa=1
            name = static_functions_helper.getName(lines, addr, nonstatic_file, dict())
            noname_functions[addr] = name

    #todo more recursive
    newNames = dict((addr, func) for addr, func in noname_functions.items() if func!='')

    for addr in noname_functions:
        if noname_functions[addr] == '':
            name = static_functions_helper.getName(lines, addr, nonstatic_file, newNames)
            noname_functions[addr] = name


    # if len(noname_functions) > 0:
    #     nonstatic_sources = static_functions_helper.getNonStaticSources\
    #         (config, os.path.basename(path))
    #     if nonstatic_sources is not None:
    #         for addr, func in noname_functions.items():
    #             name = static_functions_helper.getName(lines, addr, nonstatic_sources)
    #             noname_functions[addr] = name

    #теперь все статики должны быть найдены, можно удалить static файлы todo

    #находим тип функций
    function_types = []
    if DEBUG:
        print('FUNCTIONS')
        function_types = parse_functions_utils.getFunctionsReturnTypeSize(functions)
    #todo использовать числа при рандомизации
    # all_registers = ['r1', 'r2', 'r3', 'r4', 'r5', 'r6', 'r7', 'r8', 'r9', 'r10', 'r11']


    # ищем push, записываем для него все pop с теми же регистрами, пока не встретим новый push
    i = 0
    groups = []
    while i < len(stack_lines)-1:
        probably_push = str(stack_lines[i][2])
        if probably_push.startswith('push') or probably_push.startswith('stmdb'):
            lst = [stack_lines[i]]
            j = i + 1
            while (str(stack_lines[j][2]).startswith('pop') or str(stack_lines[j][2]).startswith('ldmia')) \
                    and stack_lines[j][3] == stack_lines[i][3]:
                lst.append(stack_lines[j])
                j += 1
                if j >= len(stack_lines):
                    break
            if j - i > 1:
                groups.append(lst)
            i = j

        else:
            i += 1


    # фильтруем группы - убираем те, в которых последний pop нe pc
    print ('GROUPS:',  len(groups))

    gr = groups
    groups = []
    for group in gr:
        if all(g[6]=='pc' for g in group[1:]):
            groups.append(group)
        #if group[-1][6] == 'pc':
         #   groups.append(group)

    #groups = [group for group in groups if group[i][6]=='pc' for i in range(1,len(group))]
    print ('New_GROUPS:', len(groups))

    #добавляем в to_write (адрес, количество старых байт, новые байты) для перезаписи
    groups_count = 0
    to_write = []
    l = 0
    full_registers_count = 0
    #1935-36
    print(start_group, ":", end_group)
    for group in groups[start_group:end_group]: # 66 libcrypto - pop lr => bl - перезапись регистров
        first, last = group[0], group[-1]
        #print(first)
        #return_size = function_types[first[0]]
        #print(return_size)
        #print(parse_functions_utils.getFunctionReturnTypeSize(first[-1]))
        #print(last[0])
        #print(first, last)
        l+=1
        big_regs = ['sp', 'ip', 'lr', 'pc', 'r12']
        if any(big_regs[i] in first[3] for i in range(len(big_regs))): #and (str(first[2]).startswith('push') or str(first[2]).startswith('stm')):
                    continue

        # добавляем регистры в начало, считает их количество
        real_reg_count = len(first[3])
        #return_size = 0 if first[0]=='14e3b4' else 4
        return_size = function_types[first[0]] if DEBUG else 4
        #return_size=4
        if return_size == 0:
            print('0')
        new_registers, table = utils.addRegistersToStartAndEnd(first[3], first[1], return_size)
        if new_registers == -1:
            full_registers_count+=1
            continue
        # меняем втутренние строки, взаимодействующие с sp
        inner_lines = parse.getAllSpLinesForLow(lines[first[5] + 1:last[5]], table)
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


        #print("POP AT:", last[0])
        #for i in inner_lines:
            #print(i)
        if len(inner_lines) > 0:
            to_write.extend(inner_lines)

    print('End: ', groups_count, 'full registers: ', full_registers_count)
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