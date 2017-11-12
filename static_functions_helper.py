import re, utils, os, parse_functions_utils, switcher, codecs

#1. Cоздать {name}_nonstatic.txt - руками или сгенерить

#file = {name}.txt - открытый
#address = адрес push, у которого нет имени

def getName(static_file_lines, address, nonstatic_file, newNames, funcAddr):

    pattern = re.compile('(:?bl|b|bx|b\.n)\s*{0}'.format(address),re.IGNORECASE)
    line_where_called = None
    for g in static_file_lines:
        l = switcher.searchInLines(pattern, g)
        if len(l)!=0:
            line_where_called = l[0]

    # Найти, где в исходном файле вызывается, т.е. bl|b|bx address
    # line_where_called, line_index = searchInLines\
    #     ('(:?bl|b|bx|b\.n)\s*{0}\s*<.*>'.format(address), static_file_lines)
    if line_where_called is None:
        return ''
        #raise Exception('{0} is not called in static {1}'.format(address, nonstatic_file))
    a1 = line_where_called.addr #адрес, где вызывается функций
    #извлекаем имя функции из line_where_called
    #function_name = re.search('<.*@@', line_where_called).group()[1:-2]
    #delta = re.search('Base\+.*>', line_where_called).group()[5:-1]
    #ищем начало функции - идем вверх по Lines, пока не встретим push
    # while True:
    #     line_index -= 1
    #     result = re.search('push|stmdb', static_file_lines[line_index])
    #     if result is not None:
    #         break
    # a2 = utils.getAddressFromLine(static_file_lines[line_index])
    #a2, index = getFuncBegin(line_where_called, static_file_lines)
    a2 = line_where_called.funcAddr
    if a2 is None:
        return ''
    #теперь в a2 лежит индекс начала функции
    #todo parse strings to ints
    #result, index = searchInLines('<{0}@@Base>:'.format(function_name), static_file_lines)
    #a2 =  utils.getAddressFromLine(static_file_lines[index+1])
    delta = int(a1,16) - int(a2,16) # смещение вызова искомой функции относительно начала той, в которой вызывается
    # определяем имя функции по адресу a2
    #function_name = re.search('<.*>:', static_file_lines[index-1])]
    function_name = funcAddr[a2]
    if re.search('((sub)|(local))_[0-9a-f]+',function_name,re.IGNORECASE):
        newname_address = a2
        if newname_address not in newNames:
            return ''
        function_name = newNames[newname_address]
        #function_name = re.sub('plt','@Base',newNames[newname_address])+':'


    #ищем, в каком файле находится определение функции function_name
    # demangled_function_name = function_name[1:-2] #убираем <>:
    # if not function_name.startswith('Java'):
    #     demangled_function_name = parse_functions_utils.demangleNativeFunctionName(function_name)
    #     demangled_function_name = parse_functions_utils.makePattern(demangled_function_name)
    #
    # nonstatic_file = nonstatic_files[0]
    #
    # if len(nonstatic_files)>0:
    #     for file in nonstatic_files:
    #         with open(file, 'r') as f:
    #             found = re.search(demangled_function_name, f.read())
    #             if found:
    #                 nonstatic_file = file
    #                 break

    #открываем nonstatic_file, ищем начало функции function_name
    with codecs.open(nonstatic_file, 'r', 'utf-8', errors="ignore") as f:
        data = f.readlines()
        data = [l for l in data if '.text' in l]
        ns_funcs,ns_dict = switcher.getFunctions(data)
        #result, index = searchInLines(function_name, data)
        ns_funcAddr = dict(zip(ns_dict.values(), ns_dict.keys()))
        addr = ns_funcAddr[function_name]
        group = [f for f in ns_funcs if f[0].addr == addr][0]
        # if result is None:
        #     return ''
            #raise Exception('{0} is not called in nonstatic {1}'.format(address, nonstatic_file))
        #b1 = utils.getAddressFromLine(data[index+1]) # адрес начала функции function_name
        b1 = group[0].addr
        b2 = int(b1,16) + delta # адрес, где вызывается искомая функция
        # ищем строку в data, у которой этот адрес
        #row, ind = searchInLines('.*{0}:.*'.format(hex(b2)[2:]), data)
        row = [l for l in group if l.addr == hex(b2)][0]
        # if row is None:
        #     return ''
            #raise Exception('{0} address is not found in nonstatic {1}'.format(b2, nonstatic_file))
        #row  = data[ind]
        #found_name = re.search('<.*>', row)
        found_name = row.line.split(';')[0].strip().split(' ')[-1]
        return found_name
        # if found_name is None:
        #     #raise Exception('No func name at {0} in {1}', b2, nonstatic_file)
        #     return ''
        # if re.search('(:?@@Base|@plt)>',found_name.group()) is None:
        #     return ''
        #return found_name.group().split('@')[0][1:]

def searchInLines(regex, lines):
    for index, line in enumerate(lines):
        result = re.search(regex, line)
        if result is not None:
            return result.group(), index
    return None, -1

def hexstringToInt(str):
    return int('0x'+str, 16)


def getFuncBegin(line, static_file_lines):
    group = [g for g in static_file_lines if g[0].addr == line.funcAddr][0]
    start_index = group.index(line)
    pop_count = 0
    while True:
        if start_index == 0:
            return None, None
        start_index -= 1
        popPattern, pushPattern = re.compile('pop|ldmia|ldmfd',re.IGNORECASE),\
        re.compile('push|stmdb|stmfd', re.IGNORECASE)
        some_func_end = switcher.searchPattern(popPattern,group[start_index])
        if some_func_end is not None:
            pop_count+=1
            continue
        result = switcher.searchPattern(pushPattern,group[start_index])
        if result is not None:
            if pop_count == 0:
                break
            pop_count-=1
    return group[start_index].addr, start_index


def generateNonStaticFile(in_file, path):
    with open(os.path.join(path,in_file), 'r') as f:
        in_data = f.read();
        out_data = re.sub('\s+static\s+', ' ', in_data)
        if out_data == in_data:
            return None
    out_file = os.path.join(path, 'nonstatic_'+in_file)
    if os.path.isfile(out_file):
        #raise Exception('File {0} already exists! Please remove or rename it!')
        os.remove(out_file)
    with open(out_file, 'w+') as f:
        f.write(out_data)
    return out_file


def getNonStaticSources(config, lib_name):
    # получаем все исходники данной либы
    sources = config.getLibSourceFiles(lib_name)
    sources = [source for source in sources if os.path.splitext(source)[1]!='.h']
    if len(sources) == 0:
        return None
    sources_path = config.get('native_directory')
    # для каждого исходника (в котором есть static)
    # генерируем файл, в котором все статики убраны
    nonstatic_sources = dict()
    for source in sources:
        nonstatic_file = generateNonStaticFile\
            (source, sources_path)
        if nonstatic_file is not None:
            nonstatic_sources[source] = nonstatic_file
    return nonstatic_sources


