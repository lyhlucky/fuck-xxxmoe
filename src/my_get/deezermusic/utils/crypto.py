import binascii

from Cryptodome.Cipher import Blowfish, AES
from Cryptodome.Hash import MD5

def _md5(data):
    h = MD5.new()  ## 创建MD5实例
    h.update(data.encode() if isinstance(data, str) else data) ## 如果data是str，则进行编码转换即data.encode否则直接data
    return h.hexdigest() ## 使用 hexdigest 方法获取计算得到的 MD5 哈希值的十六进制表示形式

def _ecbCrypt(key, data): ## ecb加密
    return binascii.hexlify(AES.new(key.encode(), AES.MODE_ECB).encrypt(data)) ##二进制转成十六进制

def _ecbDecrypt(key, data): ## ecb解密
    return AES.new(key.encode(), AES.MODE_ECB).decrypt(binascii.unhexlify(data.encode("utf-8")))

def generateBlowfishKey(trackId): ## 生成blowfish密钥
    SECRET = 'g4el58wc0zvf9na1'
    idMd5 = _md5(trackId)
    bfKey = ""
    for i in range(16):
        bfKey += chr(ord(idMd5[i]) ^ ord(idMd5[i + 16]) ^ ord(SECRET[i]))
    return str.encode(bfKey)

def decryptChunk(key, data): ## blowfish解密，key：密钥 data：待解密数据
    return Blowfish.new(key, Blowfish.MODE_CBC, b"\x00\x01\x02\x03\x04\x05\x06\x07").decrypt(data) ## 密钥、解密模式、初始化向量
