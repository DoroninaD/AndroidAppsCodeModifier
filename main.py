# -*- coding: utf-8 -*-
import re, utils, arm_translate, sys

# http://infocenter.arm.com/help/index.jsp?topic=/com.arm.doc.dui0489e/Babefbce.html
# http://www.davespace.co.uk/arm/introduction-to-arm/registers.html

#lr = r14, pc = r15, sp = r12

# push {, lr(r14)}
# stmdb	sp!, {, lr}
# stmdb.w sp!, {, lr}

# pop {, pc(r15)} или lr
# ldmia.w	sp!, {, pc}
# ldmia	sp!, {, pc}


# print(arm_translate.pushToCode(['r1', 'r2', 'r3']))
# print(arm_translate.pushToCode(['r1', 'r2', 'r3', 'r8']))
#
# print(arm_translate.popToCode(['r1', 'r2', 'r3']))
# print(arm_translate.popToCode(['r1', 'r2', 'r3', 'r8']))
#
# print(arm_translate.addSpToCode(500))
# print(arm_translate.addSpToCode(256))
# print(arm_translate.subSpToCode(256))
#
# retcode = subprocess.call(". unpack.sh", shell=True)
# if retcode == 0:
#     print("success")
# else:
#     print("failure")
#     raise Exception("UNABLE TO UNPACK ")
#print(sys.argv[1])
path = sys.argv[1] #название файла без расширения

if 'libwhatsapp' in path:
    exit()
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
        #reg  = re.search('{.*}', line).group().strip('}').strip('{').replace(',', '').split()
        registers = re.findall("r11|r10|r[1-9]", stack_line.group())
        address = re.match('.*:', line).group().replace(' ', '').replace(':', '')
        code = line.split('\t')[1].replace(' ', '').replace('\t', '')
        stack_lines.append((address, code, method, registers, index))
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

for group in groups[:2]:
    first, last = group[0], group[-1]
    code_with_sp = utils.getFunctionStackCode(lines[first[-1] + 1:last[-1]])

    #print(first)
    if len(code_with_sp) > 0:
        #print(first)
        #print("START")

        new_registers, count = utils.addRegistersToStart(first[3])

        flag = False
        for aa in code_with_sp:
            number = str(re.search('#[0-9]+', aa).group()).strip(' ').strip('#')
            new_number = int(number) + count * 4
            if new_number > 508:
                flag = True
                break
            if 'add' in aa:
                instr = arm_translate.addSpToCode(new_number)
            elif 'sub' in aa:
                instr = arm_translate.subSpToCode(new_number)
            address = re.match('.*:', aa).group().replace(' ', '').replace(':', '')
            code = aa.split('\t')[1].replace(' ', '').replace('\t', '')

            # добавляем в to_write (адрес, количество старых байт, новые байты) add/sup sp
            to_write.append((address, len(code)//2, utils.toLittleEndian(instr)))  # добавляем add/sub sp

        if flag is False:
            # добавляем в to_write (адрес, количество старых байт, новые байты) push
            to_write.append((first[0], len(first[1]) // 2,
                             utils.toLittleEndian(arm_translate.pushToCode(new_registers))))  # добавляем новый push
            # добавлаем все pop
            for a in group[1:]:
                to_write.append((a[0], len(a[1]) // 2,
                                 utils.toLittleEndian(
                                     arm_translate.popToCode(new_registers, a[1]))))  # добавляем новый pop



                #print(last)
        #print("END")


# for i in to_write:
#     if i[1]!=len(i[2]):
#         to_write.remove(i)

#переписываем файл

f = open(path+'_old.so', 'br')
text = f.read()
f.close()

for line in to_write:
    offset = int(line[0],16)
    text = text[:offset] + line[2] + text[offset+line[1]:]
    #print(to_write)

f = open(path+'.so', 'bw')
f.write(text)
f.close()
