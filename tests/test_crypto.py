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

from random import randint
from cryptography.fernet import Fernet, InvalidToken
import pytest
from mvtool.utils.crypto import encrypt, decrypt, derive_key


def get_random_key_and_message():
    key = Fernet.generate_key()
    message = "".join(chr(randint(32, 126)) for _ in range(randint(10, 150)))
    return key, message


@pytest.mark.parametrize(
    "password, message",
    [
        ("1234567890123456", "Hello World"),
        ("1234567890123456", "äüöß"),
    ],
)
def test_encrypt_decrypt(password, message):
    key = derive_key(password)
    encrypted = encrypt(message, key)
    decrypted = decrypt(encrypted, key)
    assert message == decrypted


def test_encrypt_decrypt_randomized():
    for _ in range(1000):
        key, message = get_random_key_and_message()
        encrypted = encrypt(message, key)
        decrypted = decrypt(encrypted, key)
        assert decrypted == message


def test_decrypt_nonsense():
    key = derive_key("1234567890123456")
    with pytest.raises(InvalidToken):
        decrypt("nonsense", key)


def test_decrypt_wrong_key():
    password, message = ("1234567890123456", "Hello World")
    key = derive_key(password)
    encrypted = encrypt(message, key)
    wrong_key = derive_key(password + "wrong")
    with pytest.raises(InvalidToken):
        decrypt(encrypted, wrong_key)


@pytest.mark.parametrize(
    "password, key",
    [
        ("äüöß", b"IQ0FBOtyk6z_i_pMya_GUMCMwFDA-boZv1Ov29sOSY8="),
        ("1234567890", b"s3JvTuCCyy6kqHGm8URL0Ql44xP0QpmxhkQ8Q-errSc="),
        (
            "12345678901234567890123456789012",
            b"rbBKh4Ab8T3b-_LXFEue4JOoX0vgxKjMmW7egbUBGGg=",
        ),
    ],
)
def test_derive_key(password, key):
    result = derive_key(password, b"29nC4dp24Jp7pIlP", 10000, "utf-8")
    assert result == key
