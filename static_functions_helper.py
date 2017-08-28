import re, utils, os, parse_functions_utils

#1. Cоздать {name}_nonstatic.txt - руками или сгенерить

#file = {name}.txt - открытый
#address = адрес push, у которого нет имени

def getName(static_file_lines, address, nonstatic_file, newNames):


    # Найти, где в исходном файле вызывается, т.е. bl|b|bx address
    line_where_called, line_index = searchInLines\
        ('(:?bl|b|bx|b\.n)\s*{0}\s*<.*>'.format(address), static_file_lines)
    if line_where_called is None:
        return ''
        #raise Exception('{0} is not called in static {1}'.format(address, nonstatic_file))
    a1 = utils.getAddressFromLine(static_file_lines[line_index]) #адрес, где вызывается функций
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
    a2, index = getFuncBegin(line_index, static_file_lines)
    if a2 is None:
        return ''
    #теперь в a2 лежит индекс начала функции
    #todo parse strings to ints
    #result, index = searchInLines('<{0}@@Base>:'.format(function_name), static_file_lines)
    #a2 =  utils.getAddressFromLine(static_file_lines[index+1])
    delta = hexstringToInt(a1) - hexstringToInt(a2) # смещение вызова искомой функции относительно начала той, в которой вызывается
    # определяем имя функции по адресу a2
    function_name = re.search('<.*>:', static_file_lines[index-1])
    if function_name is None:
        newname_address = utils.getAddressFromLine(static_file_lines[index])
        if newname_address not in newNames:
            return ''
        function_name = re.sub('plt','@Base',newNames[newname_address])+':'
    else:
        function_name = function_name.group()

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
    with open(nonstatic_file) as f:
        data = f.readlines()
        result, index = searchInLines(function_name, data)
        if result is None:
            return ''
            #raise Exception('{0} is not called in nonstatic {1}'.format(address, nonstatic_file))
        b1 = utils.getAddressFromLine(data[index+1]) # адрес начала функции function_name
        b2 = hexstringToInt(b1) + delta # адрес, где вызывается искомая функция
        # ищем строку в data, у которой этот адрес
        row, ind = searchInLines('.*{0}:.*'.format(hex(b2)[2:]), data)
        if row is None:
            return ''
            #raise Exception('{0} address is not found in nonstatic {1}'.format(b2, nonstatic_file))
        row  = data[ind]
        found_name = re.search('<.*>', row)
        if found_name is None:
            #raise Exception('No func name at {0} in {1}', b2, nonstatic_file)
            return ''
        return found_name.group()

def searchInLines(regex, lines):
    for index, line in enumerate(lines):
        result = re.search(regex, line)
        if result is not None:
            return result.group(), index
    return None, -1

def hexstringToInt(str):
    return int('0x'+str, 16)


def getFuncBegin(start_index, static_file_lines):
    pop_count = 0
    while True:
        if start_index == 0:
            return None, None
        start_index -= 1
        some_func_end = re.search('pop|ldmia', static_file_lines[start_index])
        if some_func_end is not None:
            pop_count+=1
            continue
        result = re.search('push|stmdb', static_file_lines[start_index])
        if result is not None:
            if pop_count == 0:
                break
            pop_count-=1
    return utils.getAddressFromLine(static_file_lines[start_index]), start_index


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


