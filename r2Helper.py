from collections import namedtuple

import r2pipe, json

func_model = namedtuple('funcModel','address name rows')
opcode_model = namedtuple('opcodeModel','offset bytes type opcode size')


class r2Helper:
    def __init__(self, filename):
        self.r2 = r2pipe.open(filename)
        self.cmd('e arm.lines=false arm.varsub=false arm.comments=false')
        self.cmd('aaa')

    def open(self,filename):
        self.cmd('o--')
        self.cmd('o {0}'.format(filename))
        self.cmd('e arm.lines=false arm.varsub=false arm.comments=false')
        self.cmd('aaa')

    def cmd(self, s):
        return self.r2.cmd(s)

    def cmdJson(self, s, *args):
        return json.loads(self.cmd(s))

    def getFunctions(self):
        funcList = self.cmdJson('aflj')
        funcTypes = ['fcn','sub','aav'] #todo
        return [self.getFuncInfo(f) for f in funcList if f['type'] in funcTypes]

    def getFuncInfo(self,funcname):
        func_info = self.cmdJson('pdfj @ {0}'.format(funcname['name']))
        print(funcname['name'])
        opcodes_info = func_info['ops']
        opcodes = [opcode_model(oc['offset'], oc['bytes'], oc['type'], oc['opcode'], oc['size'])
                   for oc in opcodes_info
                   if self.valid(oc['type']) and self.valid(oc['opcode'])]
        return func_model(func_info["addr"], func_info["name"], opcodes)

    def valid(self, item):
        return item!='invalid'


r2 = r2Helper('/home/daria/Documents/dimplom/apps/audio/lib/armeabi-v7a/libnative-audio-jni.so')
functions = r2.getFunctions()

