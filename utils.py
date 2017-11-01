# -*- coding: utf-8 -*-
import re, array, binascii, random


def getFunctionStackCode(lines):
    # ищем add(sub) sp, #число
    lines_with_sp = []
    for line in lines:
        # stack_line = re.match('\s*[0-9a-f]+\:.*sp.*', line)
        stack_line = re.match('.*(add|sub)(.w)?\s*sp, #.*', line)
        if stack_line is not None:
            lines_with_sp.append(stack_line.group())
    return lines_with_sp


def getCode(s):
    a = hex(s)[2:]
    if len(a) == 4 or len(a) == 8:
        return a
    if len(a) < 4:
        return a.rjust(4, '0')
    return a.rjust(8, '0')


def toLittleEndian(a):
    y = array.array('h', binascii.unhexlify(a))
    y.byteswap()
    return bytes.fromhex(binascii.hexlify(y).decode())


def calcRegisters(registers):
    s = 0
    for reg in registers:
        s += pow(2, int(reg[1:]))
    return s

def getAllUsedRegisters(lines):
    matches = searchRe('.*(ldr|str|mov|add|sub).*r(10|11|[0-9])', lines)
    regs = [re.findall('r(10|11|[0-9])', match.group()) for match in matches]
    r = set(sum(regs, []))
    return list(r)


registers = ['r1', 'r2', 'r3', 'r4', 'r5', 'r6', 'r7', 'r8', 'r9', 'r10', 'r11']


# добавляем все недостающие регистры в начало
# возвращаем итоговый список регистров и количество добавленных - нужно для изменения add/sub sp, #...
def addRegistersToStart(current_registers):
    if 'r1' in current_registers:
        return current_registers, 0  # в начало уже нечего добавить

    i, new_registers = 1, []

    while 'r{0}'.format(i) not in current_registers and i < len(registers):
        new_registers.append('r{0}'.format(i))
        i += 1

    return new_registers + current_registers, len(new_registers)


def addRegistersToEnd(current_registers):
    if 'r11' in current_registers:
        return current_registers  # в начало уже нечего добавить

    i = 1
    if len(current_registers) > 0:
        i = int(current_registers[-1][1:])+1
    if i > 7:
        return current_registers
    new_registers = []
    while 'r{0}'.format(i) not in current_registers and i <= 7:
        new_registers.append('r{0}'.format(i))
        i += 1

    return  current_registers + new_registers

def addRegistersToStartAndEnd(current_registers, code, returnValueSize, regsNotToUse):
    minreg = returnValueSize
    #minreg = 4
    start = min(minreg, int(current_registers[0][1:])) if len(current_registers) != 0 else minreg
    end = 12 if len(code) > 4 else 8
    new_regs = ['r{0}'.format(i) for i in range(start, end)
                if 'r{0}'.format(i) not in current_registers
                and 'r{0}'.format(i) not in regsNotToUse]
    if len(new_regs) == 0:
        return -1, -1
    # todo - uncomment for randomization
    #random.shuffle(new_regs)
    #new_regs = new_regs[:random.randint(1, len(new_regs))]
    table = {}
    for i in range(len(current_registers)):
        offset = len([k for k in new_regs if int(k[1:]) < int(current_registers[i][1:])])
        table[i*4] = offset*4
    table[len(current_registers)*4] = len(new_regs)*4
    new_regs.extend(current_registers)
    return sorted(new_regs, key = lambda item: int(item[1:])), table



def getRandomNumberOfItems(start, end):
    if start > end:
        return []
    if start == end:
        return [start]
        #return []
    r = list(range(start, end+1))
    random.shuffle(r)
    #return r[:random.randint(1,len(r))]
    return r
    #return r[:1]


def getAddressFromLine(line):
    return line.split(':')[0].split('<')[0].replace(' ', '')

def getCodeFromLine(line):
    code = str(line.split('\t')[1].replace('\t', '')).strip()
    return code.replace(' ', ''), len(code) in [4, 9]


def searchRe(regex, lines):
    return list(filter(None, [re.search(regex, line) for line in lines]))

def searchPattern(pattern, lines):
    return list(filter(None, [pattern.search(line) for line in lines]))
