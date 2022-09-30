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

from base64 import b64encode
import pytest
from mvtool.utils.crypto import encrypt, decrypt, derive_key


def get_random_key_and_message():
    from os import urandom
    from random import randint

    key = urandom(16)
    # generate random string
    message = "".join(chr(randint(32, 126)) for _ in range(randint(10, 150)))
    return key, message


@pytest.mark.parametrize(
    "key, message",
    [
        (b"1234567890123456", "Hello World"),
        (b"1234567890123456", "äüöß"),
    ],
)
def test_encrypt_decrypt(key, message):
    encrypted = encrypt(message, key)
    decrypted = decrypt(encrypted, key)
    assert message == decrypted


def test_encrypt_decrypt_randomized():
    for _ in range(1000):
        key, message = get_random_key_and_message()
        encrypted = encrypt(message, key)
        decrypted = decrypt(encrypted, key)
        assert decrypted == message


def test_derive_key():
    key = derive_key("password", 16, b"29nC4dp24Jp7pIlP", 10000, "utf-8")
    assert key == b".\x18\x97 qH\x19\xe3\xd3\x1b\xa6\xb6\xecx\xf1J"
