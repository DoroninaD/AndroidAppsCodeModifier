# -*- coding: utf-8 -*-

from utils import calcRegisters, getCode

lo_registers = ['r0', 'r1', 'r2', 'r3', 'r4', 'r5', 'r6', 'r7']

def convertOneToMany(code, is_thumb, is_pop):
    reg = (int(code, 16) >> 12) & 0xF
    if not is_thumb:
        mask = int('11' + '0' * 26, 2) if not is_pop else int('1100001' + '0' * 21, 2)
        return getCode((int(code, 16) ^ mask) & 0xFFFF0000 + pow(2, reg))
    if len(code) == 4:
        return code
    return getCode((int(code, 16) ^ int('10001011'+'0'*21,2)) & 0xFFFF0000 + pow(2, reg)) #todo проверить!



def pushpopToCode(registers, code, is_thumb, real_reg_count, is_pop):
    if real_reg_count == 0:
        code = convertOneToMany(code, is_thumb, is_pop)
    # считаем сумму регистров
    s = calcRegisters(registers)
    #mask = int('1'*8, 2) if is_thumb else int('1'*13, 2)
    if is_thumb:
        mask = int('1' * 8, 2) if len(code)==4 else int('1' * 13, 2)
    else:
        mask = int('1' * 13, 2) #берем только биты для регистров r0-r12, т.к. sp, lr, pc ге должны быть в списке регистров
    c = getCode((int(code,  16) & ~mask) + s)
    if is_thumb:
        return c
    return c[4:] + c[:4]


def makeLdrOrStr(old_instr, old_code, rx, ry, a, is_thumb, l):
    #return getCode(makeLdrOrStrInner(old_instr, old_code, rx, ry, a, is_thumb))
    return makeLdrOrStrInner(old_instr, old_code, rx, ry, a, is_thumb, l)


extended = {'str.w':0xF8C, 'ldr.w':0xF8D, 'strb.w': 0xF88, 'ldrb.w': 0xF89, 'strh.w':0xF8A, 'ldrh.w':0xF8B, 'ldrsh.w':0xF9B, 'ldrsb.w': 0xF99}
basic_arm = {'ldr': 0xE59, 'str':0xE58, 'ldrb': 0xE5D, 'strb': 0xE5C}
basic_thumb = {'ldr': 0x68, 'str':0x60, 'ldrb': 0x78, 'strb': 0x70}
sp_thumb = {'ldr': 0x98, 'str': 0x90}
more_arm = {'ldrh': 0x00B0E1D0, 'strh': 0x00B0E1C0, 'ldrsb':0x00D0E1D0, 'ldrsh':0x00F0E1C0}
more_thumb = {'ldrh': 0x88, 'strh': 0x80}
vcommon = {'vstr': (0xB00ED80, 0xA00ED80), 'vldr':(0xB00ED90, 0xA00ED90)}

regs = {'sp':13, 'lr':14, 'pc':15}

def code(old_code, mask, s, is_thumb):
    c = getCode((int(old_code, 16) & ~mask) + s)
    if is_thumb:
        return c
    return c[4:] + c[:4]

def changeSubSp(old_code, offset, thumb):
    #new = code(old_code, '11110000', new_offset, thumb)
    c = hex(int(old_code, 16)+offset)[2:].upper()
    if thumb:
        return c
    return c[4:] + c[:4]

def makeLdrOrStrInner(old_instr, old_code, rx, ry, a, is_thumb, l):  # ldr rx, [ry + a]
    old_instr = old_instr.lower()
    s = a
    # 11-0
    if old_instr.endswith('.w') \
            or old_instr in ['ldr', 'str', 'ldrb', 'strb'] and not is_thumb\
            or old_instr in ['ldrsh', 'ldrsb'] and is_thumb:
        mask = int('1' * 12, 2)
        return code(old_code, mask, s, is_thumb)

    # 10-6
    if is_thumb and (old_instr in ['str', 'ldr'] and ry!='sp' or old_instr in ['ldrb', 'strb', 'ldrh', 'strh']):
        mask = int('1'*5 + '0'*6, 2)
        #s = a * int('1000000',2)
        s = a * int('10000', 2)
        return code(old_code, mask, s, is_thumb)

    # 11-8 3-0
    if not is_thumb and old_instr in ['ldrh', 'strh', 'ldrsb', 'ldrsh', 'ldrd', 'strd']:
        mask = int('F0F', 16)
        s = a%0x10 + a//0x10 * 0x100
        return code(old_code, mask, s, is_thumb)

    # 7-0
    if is_thumb and (old_instr in ['ldrd', 'strd'] or len(old_instr) == 8
                     or (old_instr in ['str', 'ldr'] and ry == 'sp')):
        mask = int('1'*8, 2)
        s = a//4
        return code(old_code, mask, s, is_thumb)

    ry = regs[ry] if ry in regs else int(ry[1:])

    if old_instr in vcommon:
        if rx[0] == 'd': #d0-d31
            #return vcommon[old_instr][0] + ry + a//4 * 0x10000 + int(rx[1:])%0x10 * 0x10000000 + int(rx[1:])//0x10 * 0x40
            x = vcommon[old_instr][0] + ry + a//4 * 0x10000 + int(rx[1:])%0x10 * 0x10000000 + int(rx[1:])//0x10 * 0x40
            ss = getCode(x)
            if is_thumb:
                return ss[4:]+ss[:4]
            return ss
        elif rx[0] == 's': #s0-s31
            #return vcommon[old_instr][1] + ry + a//4 * 0x10000 + int(rx[1:])//2 * 0x10000000 + int(rx[1:])%2 * 0x40
            x = vcommon[old_instr][1] + ry + a//4 * 0x10000 + int(rx[1:])//2 * 0x10000000 + int(rx[1:])%2 * 0x40
            ss = getCode(x)
            if is_thumb:
                return ss[4:]+ss[:4]
            return ss


