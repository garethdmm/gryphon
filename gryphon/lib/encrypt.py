from Crypto.Cipher import AES
import base64
import os
import binascii


def encrypt(plain_text, secret_key):
    cipher = AES.new(secret_key)
    plain_text = plain_text + (" " * (16 - (len(plain_text) % 16)))
    return binascii.hexlify(cipher.encrypt(plain_text))
    
def decrypt(encrypted_text, secret_key):
    cipher = AES.new(secret_key)
    return cipher.decrypt(binascii.unhexlify(encrypted_text)).rstrip()
