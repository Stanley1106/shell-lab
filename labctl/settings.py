"""Building blocks for reading a KEY=VALUE settings file: the format, value checks and student ids."""

import ipaddress
import re

MAX_STUDENTS = 99
SECRET_BYTES = 32
GUEST_OS = ("ubuntu-26.04", "ubuntu-24.04")

KEY = re.compile(r"[A-Z][A-Z0-9_]*")
UNSAFE_VALUE = re.compile(r"[\s'\"#$`\\]")  # Make 和 shell 會改寫這些字元
COHORT = re.compile(r"[a-z][a-z0-9-]{0,23}")
SSH_TARGET = re.compile(r"[A-Za-z0-9._-]+@[A-Za-z0-9.-]+")
SECRET = re.compile(r"[0-9a-f]{64}")
FLAG_PREFIX = re.compile(r"[A-Za-z0-9_-]{1,32}")
LOCALE = re.compile(r"C\.UTF-8|[a-z]{2,3}_[A-Z]{2}\.UTF-8")
TIMEZONE = re.compile(r"UTC|[A-Z][A-Za-z_]+(?:/[A-Z][A-Za-z0-9_+-]*){1,2}")


def student_ids(count):
    return [f"student{n:02d}" for n in range(1, count + 1)]


def select_students(students, selected):
    """`students` in their own order, limited to `selected` (None means everyone)."""
    if selected is None:
        return list(students)
    if len(selected) != len(set(selected)) or not set(selected) <= set(students):
        raise ValueError("student selection contains duplicates or unknown ids")
    return [s for s in students if s in set(selected)]


def parse_env(text):
    values = {}
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep or not KEY.fullmatch(key):
            raise ValueError(f"line {number} must look like KEY=VALUE: {raw!r}")
        if key in values:
            raise ValueError(f"{key} is set twice (line {number})")
        if UNSAFE_VALUE.search(value):
            raise ValueError(f"{key} must not contain spaces, quotes, #, $, ` or \\ (line {number})")
        values[key] = value
    return values


def items(value):
    return [item for item in value.split(",") if item]


def match(key, v, pattern, expected):
    if not pattern.fullmatch(v[key]):
        raise ValueError(f"{key} must be {expected}, got {v[key]!r}")
    return v[key]


def integer(key, v, minimum, maximum):
    if not re.fullmatch(r"[0-9]+", v[key]) or not minimum <= int(v[key]) <= maximum:
        raise ValueError(f"{key} must be an integer from {minimum} to {maximum}")
    return int(v[key])


def network(key, value):
    try:
        net = ipaddress.ip_network(value, strict=True)
    except ValueError:
        raise ValueError(f"{key}: {value!r} is not a network such as 10.231.0.0/16") from None
    if net.version != 4:
        raise ValueError(f"{key} accepts IPv4 only (guests have no IPv6): {net}")
    return net
