# -*- coding: utf-8 -*-

from utils import calcRegisters, getCode

lo_registers = ['r0', 'r1', 'r2', 'r3', 'r4', 'r5', 'r6', 'r7']
arm_push_prefix = 'e92d'
thumb_push_prefix = 'b5'
arm_pop_prefix = 'E8BD'
thumb_pop_prefix = 'bd'


def pushToCode(registers, code, is_thumb):
    # считаем сумму регистров
    s = calcRegisters(registers)
    if not is_thumb:
        return getCode(int('4000', 16) + s) + arm_push_prefix
        #return arm_push_prefix +  getCode(int('4000', 16) + s)
    if any(registers[i] not in lo_registers for i in range(len(registers))):
        return  arm_push_prefix + getCode(int('4000', 16) + s)
    # все младшие
    return thumb_push_prefix + getCode(s)


def popToCode(registers, code, is_thumb):
    s = calcRegisters(registers)

    if len(code) > 4 and code[4] == '4':  # pop {lr}
        #return arm_pop_prefix + getCode(int('4000', 16) + s)
        return  getCode(int('4000', 16) + s) + arm_pop_prefix
    if not is_thumb:
        return getCode(int('8000', 16) + s) + arm_pop_prefix
    if any(registers[i] not in lo_registers for i in range(len(registers))):
        return arm_pop_prefix + getCode(int('8000', 16) + s)
        # все младшие
    return thumb_pop_prefix + getCode(s)


arm_addsp255_prefix = "e28dd0"
arm_addsp508_prefix = "e28ddf"
arm_addsp100_prefix = "e28ddc"
thumb_addsubsp_prefix = 'b0'


# add sp, #number
def addSpToCode(number, short=True):
    # thumb is only for less than 508
    if short and number <= 508:
        return thumb_addsubsp_prefix + getCode(number // 4)

    # for arm
    if number > 0x400:
        raise Exception("Tried to convert add sp, #", number)

    if number in [0x100, 0x200, 0x300, 0x400]:
        return arm_addsp100_prefix + getCode(number // 0x100)

    if number < 256:
        return arm_addsp255_prefix + getCode(number)

    return arm_addsp508_prefix + getCode(number // 4)


arm_subsp255_prefix = "e24dd0"
arm_subsp508_prefix = "e24ddf"
arm_subsp100_prefix = "e24ddc"


def subSpToCode(number, short=True):
    # thumb is only for less than 512
    if short and number <= 508:
        return thumb_addsubsp_prefix + getCode(0x80 + number // 4)

    # for arm
    if number > 0x400:
        raise Exception("Tried to convert add sp, #", number)

    if number in [0x100, 0x200, 0x300, 0x400]:
        return arm_subsp100_prefix + getCode(number // 0x100)

    if number < 256:
        return arm_subsp255_prefix + getCode(number)

    return arm_subsp508_prefix + getCode(number // 4)

def makeLdrOrStr(old_instr, old_code, rx, ry, a, is_thumb):
    return getCode(makeLdrOrStrInner(old_instr, old_code, rx, ry, a, is_thumb))


extended = {'str.w':0xF8C, 'ldr.w':0xF8D, 'strb.w': 0xF88, 'ldrb.w': 0xF89, 'strh.w':0xF8A, 'ldrh.w':0xF8B, 'ldrsh.w':0xF9B, 'ldrsb.w': 0xF99}
basic_arm = {'ldr': 0xE59, 'str':0xE58, 'ldrb': 0xE5D, 'strb': 0xE5C}
basic_thumb = {'ldr': 0x68, 'str':0x60, 'ldrb': 0x78, 'strb': 0x70}
sp_thumb = {'ldr': 0x98, 'str': 0x90}
more_arm = {'ldrh': 0x00B0E1D0, 'strh': 0x00B0E1C0, 'ldrsb':0x00D0E1D0, 'ldrsh':0x00F0E1C0}
more_thumb = {'ldrh': 0x88, 'strh': 0x80}
vcommon = {'vstr': (0xB00ED80, 0xA00ED80), 'vldr':(0xB00ED90, 0xA00ED90)}

regs = {'sp':13, 'lr':14, 'pc':15}

def makeLdrOrStrInner(old_instr, old_code, rx, ry, a, is_thumb):  # ldr rx, [ry + a]

    #is_not_thumb = len(old_code) > 4
    is_sp = ry == 'sp'

    ry = regs[ry] if ry in regs else int(ry[1:])

    if old_instr in vcommon:
        if rx[0] == 'd': #d0-d31
            #return vcommon[old_instr][0] + ry + a//4 * 0x10000 + int(rx[1:])%0x10 * 0x10000000 + int(rx[1:])//0x10 * 0x40
            x = vcommon[old_instr][0] + ry + a//4 * 0x10000 + int(rx[1:])%0x10 * 0x10000000 + int(rx[1:])//0x10 * 0x40
            ss = getCode(x)
            #return int(ss[4:]+ss[:4],16)
            return int(ss, 16)
        elif rx[0] == 's': #s0-s31
            #return vcommon[old_instr][1] + ry + a//4 * 0x10000 + int(rx[1:])//2 * 0x10000000 + int(rx[1:])%2 * 0x40
            x = vcommon[old_instr][1] + ry + a//4 * 0x10000 + int(rx[1:])//2 * 0x10000000 + int(rx[1:])%2 * 0x40
            ss = getCode(x)
            #return int(ss[4:]+ss[:4],16)
            return int(ss, 16)


    rx = regs[rx] if rx in regs else int(rx[1:])

    if str(old_instr).endswith('.w'):
        return extended[old_instr]*0x100000 + rx * 0x1000 + ry*0x10000 + a

    if not is_thumb:
        if old_instr in basic_arm:
            #return basic_arm[old_instr] * 0x100000 + ry * 0x10000 + rx * 0x1000 + a
            return basic_arm[old_instr] * 0x10 + ry + (rx * 0x1000 + a) * 0x10000
        if old_instr in more_arm:
            #return more_arm[old_instr] + ry * 0x10000 + rx * 0x1000 + a // 0x10 * 0x100 + a % 0x10
            return more_arm[old_instr] + ry + (rx * 0x1000 + a // 0x10 * 0x100  + a % 0x10)*0x10000
        if old_instr in ['ldrd', 'strd']:
            x = int(old_code, 16) & 0xfffff0f0 + a % 16 + a // 16 * 0x100
            ss = getCode(x)
            return int(ss[4:] + ss[:4], 16)
    else:
        if old_instr in ['ldrd', 'strd']:
            x = (int(old_code, 16) & 0xffffff00) + a//4
            ss = getCode(x)
            return int(ss[4:] + ss[:4], 16)
        if is_sp and old_instr in sp_thumb:
            return sp_thumb[old_instr] * 0x100 + a // 4 + rx * 0x100
        if  old_instr in basic_thumb:
            return basic_thumb[old_instr] * 0x100 + rx + ry * 8 + a * 0x10
        if old_instr in more_thumb:
            return more_thumb[old_instr] * 0x100 +  rx + ry * 8 + 0x20 * a




def pushpopToCode(registers, code, is_thumb):
    # считаем сумму регистров
    s = calcRegisters(registers)
    mask = int('1'*8, 2) if is_thumb else int('1'*13, 2)
    c = getCode((int(code,  16) & ~mask) + s)
    if is_thumb:
        return c
    return c[4:] + c[:4]
