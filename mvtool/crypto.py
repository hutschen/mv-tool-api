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


import base64
from os import urandom
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def derive_key(
    password: str,
    key_length: int = 16,
    salt: bytes = b"29nC4dp24Jp7pIlP",
    iterations: int = 10000,
    password_encoding: str = "utf-8",
) -> bytes:
    # derive key from password using PBKDF2
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=key_length,
        salt=salt,
        iterations=iterations,
    )
    return kdf.derive(password.encode(password_encoding))


def _message_unpadder(
    message: str, block_size=16, encoding="utf-8", delimiter=b"0"
) -> bytes:
    prefix = message.encode(encoding)
    # padding: generate a random postfix which does not contain the delimiter
    postfix_size = block_size - (len(prefix) % block_size)
    postfix_size = postfix_size if postfix_size else block_size
    postfix = delimiter
    while delimiter in postfix:
        postfix = urandom(postfix_size - 1)
    return prefix + delimiter + postfix


def _message_padder(message: bytes, encoding="utf-8", delimiter=b"0"):
    prefix, _, _ = message.rpartition(delimiter)
    return prefix.decode(encoding)


def _decode_encrypted(message: bytes, encoding="utf-8") -> str:
    return base64.b64encode(message).decode(encoding)


def _encode_encrypted(message: str, encoding="utf-8") -> bytes:
    return base64.b64decode(message.encode(encoding))


def encrypt(message: str, key: bytes, block_size=16, encoding="utf-8"):
    plaintext = _message_unpadder(message, block_size, encoding)
    initialization_vector = urandom(block_size)
    cipher = Cipher(algorithms.AES(key), modes.CBC(initialization_vector))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()
    return _decode_encrypted(initialization_vector + ciphertext, encoding)


def decrypt(message: str, key: bytes, block_size=16, encoding="utf-8"):
    message = _encode_encrypted(message, encoding)
    initialization_vector = message[:block_size]
    ciphertext = message[block_size:]
    cipher = Cipher(algorithms.AES(key), modes.CBC(initialization_vector))
    decryptor = cipher.decryptor()
    plaintext = decryptor.update(ciphertext) + decryptor.finalize()
    return _message_padder(plaintext, encoding)
