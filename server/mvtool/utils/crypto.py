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
from tornado.web import RequestHandler


def encrypt(message, key, encoding='utf-8'):
    plaintext = message.encode(encoding)
    initialization_vector = urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CBC(initialization_vector))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(plaintext)
    return initialization_vector + ciphertext


def decrypt(message, key, encoding='utf-8'):
    initialization_vector = message[:16]
    ciphertext = message[16:]
    cipher = Cipher(algorithms.AES(key), modes.CBC(initialization_vector))
    decryptor = cipher.decryptor()
    plaintext = decryptor.update(ciphertext) + decryptor.finalize()
    return plaintext.decode(encoding)


class SecretCookieMixin(RequestHandler):
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
        return await IOLoop.current().run_in_executor(None, decrypt, ciphertext, key)
