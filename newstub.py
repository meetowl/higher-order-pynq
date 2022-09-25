import typesystem.hop_types as ht

REGSPACE_ADDR = 0x40

class Stub:
    def __init__(self, name, signature, base_addr):
        self.name = name
        self.signature = signature
        self.base_addr = base_addr
        self.regspace_addr = REGSPACE_ADDR

    @classmethod
    def from_meta_dict(funcType, name, meta):
        stubDict = {
            "hardware" : HardwareStub,
            "python"   : PythonStub,
            "cpp"      : CPPStub
        }

        return stubDict[funcType].from_meta_dict(name, meta)

class HardwareStub(Stub):
    def __init__(self, name, signature, base_addr, cep_offset):
        super().__init__(name, signature, base_addr, cep_offset)


    @classmethod
    def from_meta_dict(name, meta):
        signature = ht.parse(meta['signature'])
        base_addr = meta['base']
        cep_offset = meta['cep_offset']
        return HardwareStub(name, signature, base_addr, cep_offset  )
