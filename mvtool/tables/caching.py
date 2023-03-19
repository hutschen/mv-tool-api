# coding: utf-8
#
# Copyright (C) 2023 Helmar Hutschenreuter
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

from ..models.common import EqualityMixin


class ModelsCache:
    """A cache for instances of a single model derived from the EqualityMixin class.

    The ModelsCache class provides a factory method `get_or_create` that takes the
    constructor arguments for a single model class as input. If an instance with the
    same values has already been created, it returns the cached instance. Otherwise, it
    creates a new instance, stores it in the cache, and returns it.

    The cache relies on the __eq__ and __hash__ methods provided by the EqualityMixin
    class to determine if two instances are equal.

    Attributes:
        _cache (Dict[int, EqualityMixin]): A dictionary storing the cached instances.
        model_class (Type[EqualityMixin]): The class of the model to be cached, derived
        from EqualityMixin.
    """

    def __init__(self, model_class):
        if not issubclass(model_class, EqualityMixin):
            raise ValueError(
                f"{model_class.__name__} must be a subclass of EqualityMixin"
            )

        self._cache = {}
        self.model_class = model_class

    @property
    def instance_count(self) -> int:
        """Get the number of instances of the model class that are currently cached.

        Returns:
            int: The number of instances of the model class that are currently cached.
        """
        return len(self._cache)

    def get_or_create(self, *args, **kwargs) -> EqualityMixin:
        """Retrieve an existing instance of a model from the cache or create and cache a
        new one.

        Args:
            *args: The positional arguments to pass to the model's constructor.
            **kwargs: The keyword arguments to pass to the model's constructor.

        Returns:
            EqualityMixin: The cached or newly created instance of the model.
        """
        instance = self.model_class(*args, **kwargs)

        # Check if an instance with the same hash value already exists in the cache
        instance_hash = hash(instance)
        cached_instance = self._cache.get(instance_hash, None)
        if cached_instance is not None:
            return cached_instance
        else:
            self._cache[instance_hash] = instance
            return instance

    def clear(self):
        """Clear the cache."""
        self._cache = {}
