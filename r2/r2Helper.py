from recordclass import recordclass

import r2pipe, json



class r2Helper:
    func_model = recordclass('funcModel', 'address name rows')
    opcode_model = recordclass('opcodeModel', 'offset bytes type opcode size regs reg')
    opcode_model.__new__.__defaults__=(None, None, None, None, None, None, None)

    def __init__(self, filename):
        self.r2 = r2pipe.open(filename)
        self.cmd('e arm.lines=false arm.varsub=false arm.comments=false cfg.bigendian=false')
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
        funcTypes = ['fcn','sub','aav', 'sym'] #todo
        return dict((hex(f['offset']),self.getFuncInfo(f)) for f in funcList if f['type'] in funcTypes)

    def getFuncInfo(self,func):
        func_info = self.cmdJson('pdfj @ {0}'.format(func['offset']))
        print(func['name'])
        opcodes_info = func_info['ops']
        opcodes = [self.opcode_model(hex(oc['offset']), oc['bytes'], oc['type'], oc['opcode'], oc['size'])
                   for oc in opcodes_info
                   if self.valid(oc['type']) and self.valid(oc['opcode'])]
        return self.func_model(hex(func_info["addr"]), func_info["name"], opcodes)

    def valid(self, item):
        return item!='invalid'


