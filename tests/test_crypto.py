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

import pytest
from mvtool.crypto import encrypt, decrypt


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
    for _ in range(100):
        key, message = get_random_key_and_message()
        encrypted = encrypt(message, key)
        decrypted = decrypt(encrypted, key)
        assert decrypted == message
