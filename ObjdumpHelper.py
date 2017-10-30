import re, utils


def readLines(lines):
    indices = [i for i, s in enumerate(lines) if '.text' in s]
    lines = lines[indices[0]:]
    return lines



def getFunctions(lines):
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
            address = utils.getAddressFromLine(line)
            stack_lines.append((address,function_name))
        andeq = re.search('andeq', line)
        if andeq is not None:
            stack_lines.append((address, "andeq", "null"))

        #stack_line = re.match('.*((push(.w)?|stmdb(.w)?\s*sp!).*lr}|(pop[a-z]*|ldmia[a-z]*\s*sp!).*(pc|lr)}).*', line)
        stack_line = re.match('.*((push|stmdb[a-z]*\s*sp!).*lr}|(pop|ldmia[a-z]*\s*sp!).*(pc|lr)}).*', line)

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

    return combineFunction(stack_lines), functions



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
