"""Cache helpers that degrade gracefully when Redis is unavailable."""

import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)


def cache_get(key, default=None):
    try:
        return cache.get(key, default)
    except Exception as exc:
        logger.warning("Cache get failed (%s): %s", key, exc)
        return default


def cache_set(key, value, timeout=None):
    try:
        cache.set(key, value, timeout=timeout)
        return True
    except Exception as exc:
        logger.warning("Cache set failed (%s): %s", key, exc)
        return False


def cache_add(key, value, timeout=None):
    try:
        return cache.add(key, value, timeout=timeout)
    except Exception as exc:
        logger.warning("Cache add failed (%s): %s", key, exc)
        return False


def cache_delete(key):
    try:
        cache.delete(key)
    except Exception as exc:
        logger.warning("Cache delete failed (%s): %s", key, exc)
        return False
    return True


def cache_incr(key):
    try:
        return cache.incr(key)
    except ValueError:
        return None
    except Exception as exc:
        logger.warning("Cache incr failed (%s): %s", key, exc)
        return None
