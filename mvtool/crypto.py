# coding: utf-8
#
# Copyright (C) 2022 Helmar Hutschenreuter
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from os import urandom
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def _encode_message(message, block_size=16, encoding="utf-8", delimiter=b";"):
    prefix = message.encode(encoding)
    postfix_size = block_size - (len(prefix) % block_size)
    postfix_size = postfix_size if postfix_size else block_size
    postfix = delimiter
    # generate a random postfix which does not contain the delimiter
    while delimiter in postfix:
        postfix = urandom(postfix_size - 1)
    return prefix + delimiter + postfix


def _decode_message(message: bytes, block_size=16, encoding="utf-8", delimiter=b";"):
    prefix, _, _ = message.rpartition(delimiter)
    return prefix.decode(encoding)


def encrypt(message, key, block_size=16, encoding="utf-8"):
    plaintext = _encode_message(message, block_size, encoding)
    initialization_vector = urandom(block_size)
    cipher = Cipher(algorithms.AES(key), modes.CBC(initialization_vector))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()
    return initialization_vector + ciphertext


def decrypt(message, key, block_size=16, encoding="utf-8"):
    initialization_vector = message[:block_size]
    ciphertext = message[block_size:]
    cipher = Cipher(algorithms.AES(key), modes.CBC(initialization_vector))
    decryptor = cipher.decryptor()
    plaintext = decryptor.update(ciphertext) + decryptor.finalize()
    return _decode_message(plaintext, block_size, encoding)
