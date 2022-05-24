# coding: utf-8
# 
# Copyright 2022 Helmar Hutschenreuter
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation. You may obtain
# a copy of the GNU AGPL V3 at https://www.gnu.org/licenses/.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AGPL V3 for more details.

from os import urandom
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from tornado.ioloop import IOLoop

def _encode_message(message, block_size=16, encoding='utf-8', delimiter=b';'):
    prefix = message.encode(encoding)
    postfix_size = block_size - (len(prefix) % block_size)
    postfix_size = postfix_size if postfix_size else block_size
    postfix = delimiter
    while delimiter in postfix:
        postfix = urandom(postfix_size -1)
    return prefix + delimiter + postfix


def _decode_message(message: bytes, block_size=16, encoding='utf-8', delimiter=b';'):
    prefix, _, _ = message.rpartition(delimiter)
    return prefix.decode(encoding)


def encrypt(message, key, block_size=16, encoding='utf-8'):
    plaintext = _encode_message(message, block_size, encoding)
    initialization_vector = urandom(block_size)
    cipher = Cipher(algorithms.AES(key), modes.CBC(initialization_vector))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(plaintext) # + encryptor.finalize()
    return initialization_vector + ciphertext


def decrypt(message, key, block_size=16, encoding='utf-8'):
    initialization_vector = message[:block_size]
    ciphertext = message[block_size:]
    cipher = Cipher(algorithms.AES(key), modes.CBC(initialization_vector))
    decryptor = cipher.decryptor()
    plaintext = decryptor.update(ciphertext) + decryptor.finalize()
    return _decode_message(plaintext, block_size, encoding)


class SecretCookieMixin(object):
    ''' Mixin for classes derived from tornado.web.RequestHandler
    '''
    async def set_secret_cookie(self, name, value, *args, **kwargs):
        self.require_setting("cookie_secret", "secret cookies")
        key = self.application.settings["cookie_secret"]
        ciphertext = await IOLoop.current().run_in_executor(None, encrypt, value, key)
        self.set_secure_cookie(name, ciphertext, *args, **kwargs)

    async def get_secret_cookie(self, name, *args, **kwargs):
        self.require_setting("cookie_secret", "secret cookies")
        key = self.application.settings["cookie_secret"]
        ciphertext = self.get_secure_cookie(name, *args, **kwargs)
        if ciphertext is not None:
            return await IOLoop.current().run_in_executor(
                None, decrypt, ciphertext, key)
