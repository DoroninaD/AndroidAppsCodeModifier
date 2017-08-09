# -*- coding: utf-8 -*-
import re, utils, arm_translate, parse, sys

# http://infocenter.arm.com/help/index.jsp?topic=/com.arm.doc.dui0489e/Babefbce.html
# http://www.davespace.co.uk/arm/introduction-to-arm/registers.html
#path = sys.argv[1] #название файла без расширения
path = 'data/telegram/lib/armeabi-v7a/libtmessages.25'
#path = 'data/app-debug/lib/armeabi-v7a/libhello-libs'
#if 'libwhatsapp' in path:
 #   exit()
    #'data/com.whatsapp/lib/armeabi-v7a/libwhatsapp'
f = open(path+'.txt', 'r')
lines = f.readlines()
indices = [i for i, s in enumerate(lines) if '.text' in s]
lines = lines[indices[0]:]
f.close()

stack_lines = []

index = 0
# выбираем только строки с push/pop, разбираем их на составляющие
for line in lines:
    stack_line = re.match('.*((push(.w)?|stmdb(.w)?\s*sp!).*lr}|(pop(.w)?|ldmia(.w)?\s*sp!).*(pc|lr)}).*', line)
    if stack_line is not None:
        method = re.search('push(.w)?|stmdb(.w)?|pop(.w)?|ldmia(.w)?', line).group()

        # берем все регистры в {} и убираем последний (это lr или pc)
        # в дальнешем будем исключать строки, в которых есть регистры > r11
        registers = re.search('{.*}', line).group().replace('}','').replace('{','').replace(' ','').split(',')[:-1]
        #registers = re.findall("r11|r10|r[1-9]|sp", stack_line.group())
        # убираем лишний sp (sp!)
        #if (method.startswith('stm') or method.startswith('ldm')) and 'sp' in registers:
        #    registers.remove('sp')
        address = utils.getAddressFromLine(line)
        code, is_thumb = utils.getCodeFromLine(line)
        stack_lines.append((address, code, method, registers, is_thumb, index))
    index += 1

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

#добавляем в to_write (адрес, количество старых байт, новые байты) для перезаписи
to_write = []
l = 0
for group in groups[:6700]:
    first, last = group[0], group[-1]
    #print(last[0])
    #print(first, last)
    l+=1
    big_regs = ['sp', 'ip', 'lr', 'pc', 'r12']
    if any(big_regs[i] in first[3] for i in range(len(big_regs))): #and (str(first[2]).startswith('push') or str(first[2]).startswith('stm')):
                continue

    # добавляем регистры в начало, считает их количество
    new_registers, count = utils.addRegistersToStart(first[3])

    # добавляем в to_write (адрес, количество старых байт, новые байты) push
    to_write.append((first[0], len(first[1]) // 2,
                     utils.toLittleEndian(arm_translate.pushToCode(new_registers, first[1], first[4]))))  # добавляем новый push
    # добавлаем все pop
    for a in group[1:]:
        to_write.append((a[0], len(a[1]) // 2,
                         utils.toLittleEndian(
                             arm_translate.popToCode(new_registers, a[1], a[4]))))  # добавляем новый pop

    #меняем втутренние строки, взаимодействующие с sp
    inner_lines = parse.getAllSpLinesForLow(lines[first[-1] + 1:last[-1]], count)
    print("POP AT:", last[0])
    for i in inner_lines:
        print(i)
    if len(inner_lines) > 0:
        to_write.extend(inner_lines)


#переписываем файл

f = open(path+'_old.so', 'br')
text = f.read()
f.close()

for line in to_write:
   # print(line)
    offset = int(line[0],16)
    text = text[:offset] + line[2] + text[offset+line[1]:]

f = open(path+'.so', 'bw')
f.write(text)
f.close()
