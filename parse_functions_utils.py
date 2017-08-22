import re, os.path, cxxfilt, glob, codecs
from timeit import timeit
java_dir = '/home/daria/Desktop/hello-libs (copy)/app/src/main/java/' # todo set directory for java
#java_dir = '/home/daria/Downloads/Telegram-FOSS-master/TMessagesProj/src/main/java/'
#jni_dir = '/home/daria/Downloads/Telegram-FOSS-master/TMessagesProj/jni'
#java_dir = '/home/daria/Documents/android-ndk-master/hello-libs/app/src/main/java/'
jni_dir = '/home/daria/Desktop/hello-libs (copy)/app/src/main/cpp/'
jnih_path = '/home/daria/Android/Sdk/ndk-bundle/sysroot/usr/include/jni.h'

# https://docs.oracle.com/javase/8/docs/technotes/guides/jni/spec/design.html
# http://docs.oracle.com/javase/specs/jls/se7/html/jls-4.html#jls-4.2
Java_types64 = ['long', 'double'] # 64 bits
Java_types32 = ['int', 'byte', 'short', 'char', 'float', 'boolean'] #32 bits
void_type = ['void']
C_types32 = ['int32_t','int16_t', 'int8_t', 'int',
             'float', 'char', 'bool', 'long int', 'wchar_t',
             'jbyte', 'jchar', 'jboolean', 'jshort', 'jint', 'jfloat'] #unsigned не учитываем
jni_objects_types = ['jclass', 'jstring', 'jcharArray'] #todo add other Arrays
C_types64 = ['long long', 'double', 'int64_t', 'jlong', 'jdouble']
C_types128 = ['long double']
JNI_types = ['']

#for native functions declared in Java code
def getJavafunctionType(JNI_function_name):
    function_name = str(JNI_function_name)
    if not function_name.startswith('Java'):
        return -1 #Not right JNI function name
    #ищем escaped символы
    #if re.search('_[0-3]', function_name) is not None:
        #todo заменить на исходные символы
    #todo replace _2, _3, ...
    params = ''
    if '__' in function_name:
        params = parseJavaFuncParams(function_name.split('__')[-1])
        params = [p[:-2]+'(.|\n)*\[\](.|\n)*' for p in params if '[]' in p]
    params_regex = '(.|\n)*,\s*'.join(params)

    function_name = function_name.split('__')[0].replace('_', ' ').replace(' 1','_')
    splitted_path = function_name.split(' ')
    #a = re.split('_[^0-9]', function_name)
    short_func_name = splitted_path[-1]
    if params!='':
        short_func_name+='(.|\n)*\((.|\n)*'+params_regex+'(.|\n)*\)'
    path = java_dir+'/'.join(splitted_path[1:-1])+'.java' #remove Java and func name

    if not os.path.isfile(path):
        print('NO FILE {0}!'.format(path))
        return -1 #todo
    with codecs.open(path, "r", encoding='utf-8', errors='ignore') as f:
        data = f.read()
        func_declaration = re.search('native .* {0}'.format(short_func_name), data)
    if func_declaration is None:
        print('NONE DECLARATION in {0}'.format(path))
        return -1 #todo
    # все типы односложные, нет указателей
    type = func_declaration.group().split('(')[0] #убираем параметры
    type = type.split(' ')[-2]
    if type == '[]': #если в коде 'type []' (есть пробел)
        type = type.split(' ')[-3] + type.split(' ')[-2]
    return type

def getCFunctionType(func_name):
    if func_name == '': # нет функции -> не можем определить тип ->None
        return None
    #jni типы не берем, потому что такие функции начинаются с _Java
    pattern = C_types128 + C_types64 + C_types32 + void_type +['\*', '\[\]'] + jni_objects_types
    type = re.search('({0})\s*\*?\s*'.format('|'.join(pattern)), func_name)
    # учесть указатели!

    if type is None: #функция есть, но тип не 128 и не 64 и не void -> 32
        return ''
    return type.group().strip()

def getTypeSize(type, isJNI):
    if type == None: # не нашли функцию -> может быть любой тип
        return 4
    if not isJNI and type in C_types128:
      return 4
    if isJNI and type in Java_types64 or not isJNI and type in C_types64:
        return 2
    if '*' in type or '[]' in type \
            or isJNI and type in Java_types32 \
            or not isJNI and type in C_types32\
            or type in jni_objects_types:
        return 1
    # важно, что void после *, так как void* = 32 бита
    if type == 'void':
        return 0
    return 4


def getFunctionsReturnTypeSize(functions):

    #function_types = dict()
    function_types = dict.fromkeys(functions.keys(), '') #адрес - найденнная функция

    functions = dict(functions) # адрес - функция
    backup = functions.copy()
    # обрабатываем JNI функции
    Java_functions = dict((address, func) for address, func in functions.items()
                          if func.startswith('Java'))
    for address, function in Java_functions.items():
        if 'int32' in function or 'int64' in function:
            br = 1
        function_types[address] = getJavafunctionType(function)

    # отпределяем размер для JNI
    return_sizes = dict()
    for address, func in function_types.items():
        if func!='':
            return_sizes[address] = getTypeSize(func, True)

    # обрабатываем C фукнции
    C_functions = dict((address, func) for address, func in functions.items()
         if not func.startswith('Java') and not func == '')

    # demangle mangled functions
    for address, function in C_functions.items():
        if function.startswith('_Z'):
            n = cxxfilt.demangle(function)
            if n.startswith('_JNIEnv'):
                n = n[9:]
            C_functions[address] = n


    # отдельно выносим функции из jni.h
    jni_functions = dict((address, func[7:]) for address, func in C_functions.items() if func.startswith('_JNIEnv'))
    #C_functions = dict((address, func) if address not in jni_functions)

    # ищем определение функций в файлах
    c_found_funcs = findFunctionsInFiles(C_functions) #находим С-функции в h/c(pp) файлах
    for address, function in c_found_funcs.items():
        if address == '362c':
            aaa = 1
        # убираем параметры
        function_types[address] = getCFunctionType(function.split('(')[0])

    #обрабатывым функции из jni.h


    for address, func in function_types.items():
        if address not in return_sizes:
            if address == '362c':
                aaa=1
            return_sizes[address] = getTypeSize(func, False)
    print('4 bytes: ', len([f for f in return_sizes if return_sizes[f]==4]))
    print('2 bytes: ', len([f for f in return_sizes if return_sizes[f]==2]))
    print('1 bytes: ', len([f for f in return_sizes if return_sizes[f]==1]))
    print('0 bytes: ', len([f for f in return_sizes if return_sizes[f]==0]))

    notfound = dict((f, backup[f]) for f in return_sizes if return_sizes[f]==4)
    return return_sizes

# def getJNIFunctionsTypes(functions):
#     with codecs.open(jnih_path, "r", encoding='utf-8', errors='ignore') as f:
#         data = f.read()
#         for func in functions:
#             func_declaration = re.search('native .* {0}'.format(func), data)
#


def searchInFile(patterns_dict,func_dict, file):
    results = dict((key, '') for key in patterns_dict.keys()) #address - pattern
    with codecs.open(file, "r", encoding='utf-8', errors='ignore') as f:
        data = f.read()
        for address, func in func_dict.items():
            if func.split('(')[0] in data:
                result = re.search(patterns_dict[address], data)
                results[address] = result.group() if result is not None else ''
    results = dict((key, value) for key, value in results.items() if value!='')
    return results

types_equals = {'uint32': 'unsigned int',
                'uint64': 'unsigned long long',
                'uint32_t': 'unsigned int',
                'uint64_t': 'unsigned long long',
                'int32': 'int',
                'int64': 'long long',
                'int32_t': 'int',
                'int64_t': 'long long'
                }

types_patterns = {'int':'(int32(_t)?)|(j?int)|(j?size)',
                  'unsigned int':'uint32(_t)?',
                  'long long': '(int64(_t)?)|(j?long( long)?)',
                  'unsigned long long': 'uint64(_t)?',
                  'unsigned char': 'jboolean|(uint8(_t)?)|bool',
                  'signed char': '(j?byte)|int8(_t)?',
                  'short': '(j?short)|int16(_t)?',
                  'float': 'j?float',
                  'unsigned short': 'jchar',
                  'double': 'jdouble',
                  }

#открываем файл, ищем все функции
def findFunctionsInFiles(functions):
    # functions = address:functions
    f_backup = functions.copy()
    result = dict((key,'') for key, value in functions.items()) # адрес - найденная функция

    patterns = dict()
    #выделяем типы входных параметров
    for address, func in functions.items():
        params = re.search('\((.|\n)*\)', func)
        #params_regex = '(.|\n)*'
        #params_regex = '[^;\)]*
        params_regex = '[^;]*'
        if address == '362c':
            aaa=1
        if params is not None: # есть параметры
            params_list = params.group()[1:-1].split(',')
            #tmp = params_list.copy()
            for i in range(len(params_list)):
                p = params_list[i].strip()
                p = p.replace(' const', '') # const меняет место, уберем его
                if p.startswith('_j') and p[-1]=='*': #_jobject*->jobject
                    p = p[1:-1]
                if p.startswith('_J'):
                    p = p[1:]
                non_escaped = p.strip('&').strip('*').strip(' ') #запоминаем nonescaped параметры
                p = re.escape(p) #escape
                #todo unsigned int -> unsigned// int
                if non_escaped in types_patterns:
                    p = p.replace(p, types_patterns[non_escaped])
                #p = '\s*j?'+p #для jni
                #todo make this regexp more effetive!!!
                p = '(\\s*(const)?\\s*' + p + '\\s*(const)?\\s*)'
                params_list[i] = p.replace('\\*', '\\s*\\*\\s*').replace('\\&', '\\s*\\&\\s*')

            #params_regex = '(.|\n)*,(const)?\\s*(const)?'.join(params_list) #todo escape?
            params_regex = '(.|\n)*\\s*'.join(params_list) #todo escape?

            # для jni и void* -> void *
            params_regex= params_regex\
                .replace('_J', 'J').replace('_j', 'j')

        # result_pattern = re.compile('\n.*([a-zA-Z0-9_\*]+\s){0,3}'
        #                             +'\*?{0}\({1}\)(\s[a-zA_Z_]+)?\s'
        #                             .format(re.escape(func.split('(')[0]), params_regex)
        #                             +'{0,};', re.MULTILINE)

        result_pattern = re.compile('\n\s*([a-zA-Z0-9_\"\*\[\]]+\s+){0,3}'
                                    +'\*?{0}\s*\({1}.*\)(\s[a-zA_Z_]+)?\s'
                                    .format(re.escape(func.split('(')[0]), params_regex)
                                    +'*(;|{)', re.MULTILINE)


        patterns[address] = result_pattern

    #patterns = dict((address, '\n.*{0}(.*);'.format(re.escape(func)))
                    #for address, func in functions.items())
    def find(path):
        p = dict((address, pattern) for address,pattern in patterns.items())
        for file in glob.iglob(path, recursive=True):
           # print(file)
            found_func = searchInFile(p, functions, file)
            result.update(found_func)
            #p = dict((key, value) for key, value in patterns.items() if result[key] == '')
            for f in found_func.keys():
                functions.pop(f)
                p.pop(f)
        return p


    patterns = find(jni_dir+'/**/*.h')
    # patterns = dict((address, re.compile(p.pattern[:-1]+re.escape('{'), re.MULTILINE))
    #                for address,p in patterns.items())
    jni_res = dict((addr, f) for addr, f in result.items() if f!='')
    #result.clear()
    #
    patterns  = find(jni_dir+'/**/*.c*')

    return result


def parseJavaFuncParams(params):

    signatures = {'Z':'boolean', 'B':'byte', 'C':'char', 'S':'short', 'I':'int',
                  'J':'long', 'F':'float', 'V':'void', 'D':'double'}

    params = params.replace('_2', ',')
    #complex_types = re.findall('L(?:[a-zA-Z0-9]*(?:_(?:0|1|3))*)*_2', params)
    complex_types = re.findall('L[a-zA-Z0-9_]*,', params)

    replacer = dict()
    for index, type in enumerate(complex_types):
        replacer[type] = str(index)*len(type)
        #заменяем complex_types на пустышки,
        # чтобы не перепутать их с большими буквами из примитивных
        params = params.replace(type, replacer[type])

    #заменяем примитивные типы, разделяем запятыми
    for sign, type in signatures.items():
        params = params.replace(sign, type+',')

    #возвращаем сложные типы
    for index, type in enumerate(complex_types):
        params = params.replace(replacer[type], type)

    #обрабатываем сложные типы
    params = params.replace('L', '').replace('_3', '[')
    #заменяем уникоды
    unicode_chars = re.findall('_0[0-9]+', params)
    for c in unicode_chars:
        params = params.replace(c, chr(int(c[2:])))

    params = params.replace('_','/').replace('_1', '_')
    splitted_params = params[:-1].split(',') #убираем последнюю запятую

    #оставляем только само имя класса
    return  [p.split('/')[-1] for p in splitted_params]
