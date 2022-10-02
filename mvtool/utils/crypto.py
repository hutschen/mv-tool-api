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
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.fernet import Fernet


def derive_key(
    password: str,
    salt: bytes = b"29nC4dp24Jp7pIlP",
    iterations: int = 10000,
    password_encoding: str = "utf-8",
) -> bytes:
    # derive key from password using PBKDF2
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # Fernet needs a key length of 32 bytes
        salt=salt,
        iterations=iterations,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode(password_encoding)))


def encrypt(message: str, key: bytes, encoding="utf-8"):
    encrypted = Fernet(key).encrypt(message.encode(encoding))
    return base64.urlsafe_b64encode(encrypted).decode(encoding)


def decrypt(message: str, key: bytes, encoding="utf-8"):
    encrypted = base64.urlsafe_b64decode(message.encode(encoding))
    return Fernet(key).decrypt(encrypted).decode(encoding)
