#!/usr/bin/env python3
"""Stream a compact vehicle catalog without loading all technical profiles into RAM."""
import argparse
import json
from pathlib import Path
import re
import sys
import tempfile

STRING = re.compile(r'"(?:[^"\\]|\\.)*"', re.S)
SPACE = re.compile(r'\s*')
DELIMITER = re.compile(r'[\s{}\[\],:]')
MODEL_PATH = ('brands', '*', 'modeller', '*')


class Tokens:
    def __init__(self, stream):
        self.stream = stream
        self.buffer = ''
        self.pos = 0
        self.eof = False
        self.read_chars = 0
        self.next_progress = 64 * 1024 * 1024

    def refill(self):
        self.buffer = self.buffer[self.pos:]
        self.pos = 0
        chunk = self.stream.read(65536)
        self.eof = not chunk
        self.buffer += chunk
        self.read_chars += len(chunk)
        if self.read_chars >= self.next_progress:
            print(f'Catalog: read approximately {self.read_chars // (1024 * 1024)} Mi characters',
                  file=sys.stderr, flush=True)
            self.next_progress = self.read_chars + 64 * 1024 * 1024

    def next(self):
        while True:
            self.pos = SPACE.match(self.buffer, self.pos).end()
            if self.pos < len(self.buffer):
                break
            if self.eof:
                return None
            self.refill()
        first = self.buffer[self.pos]
        if first in '{}[],:':
            self.pos += 1
            return first
        if first == '"':
            while True:
                match = STRING.match(self.buffer, self.pos)
                if match:
                    token = match.group()
                    self.pos = match.end()
                    # Reject invalid escapes and control characters too.
                    json.loads(token)
                    return token
                if self.eof or len(self.buffer) - self.pos > 16 * 1024 * 1024:
                    raise ValueError('Unterminated or oversized JSON string')
                self.refill()
        while True:
            match = DELIMITER.search(self.buffer, self.pos)
            if match or self.eof:
                end = match.start() if match else len(self.buffer)
                token = self.buffer[self.pos:end]
                self.pos = end
                if token not in {'true', 'false', 'null'}:
                    if not re.fullmatch(r'-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?', token):
                        raise ValueError('Invalid JSON token')
                return token
            if len(self.buffer) - self.pos > 1024:
                raise ValueError('Oversized JSON number')
            self.refill()


def compact_stream(source, destination):
    tokens = Tokens(source)
    stats = {'models': 0, 'profile_fields_removed': 0, 'technical_profiles_removed': 0}

    def emit(output, value):
        if output is not None:
            output.write(value)

    def expect(expected):
        actual = tokens.next()
        if actual != expected:
            raise ValueError(f'Expected JSON {expected!r}, got {actual!r}')

    def value(token, output, path):
        if token is None:
            raise ValueError('Unexpected end of JSON')
        if token == '{':
            if path == MODEL_PATH:
                stats['models'] += 1
            emit(output, '{')
            key = tokens.next()
            first = True
            if key != '}':
                while True:
                    if key is None or not key.startswith('"'):
                        raise ValueError('Expected JSON object key')
                    name = json.loads(key)
                    expect(':')
                    remove = path == MODEL_PATH and name == 'dmr_profiles'
                    if remove:
                        stats['profile_fields_removed'] += 1
                        child_output = None
                    else:
                        if not first:
                            emit(output, ',')
                        emit(output, key + ':')
                        first = False
                        child_output = output
                    value(tokens.next(), child_output, path + (name,))
                    separator = tokens.next()
                    if separator == '}':
                        break
                    if separator != ',':
                        raise ValueError('Expected JSON object separator')
                    key = tokens.next()
            emit(output, '}')
        elif token == '[':
            emit(output, '[')
            item = tokens.next()
            first = True
            while item != ']':
                if not first:
                    emit(output, ',')
                if path == MODEL_PATH + ('dmr_profiles',):
                    stats['technical_profiles_removed'] += 1
                value(item, output, path + ('*',))
                first = False
                separator = tokens.next()
                if separator == ']':
                    break
                if separator != ',':
                    raise ValueError('Expected JSON array separator')
                item = tokens.next()
                if item == ']':
                    raise ValueError('Trailing comma in JSON array')
            emit(output, ']')
        elif token.startswith('"') or token in {'true', 'false', 'null'} or token[0] in '-0123456789':
            emit(output, token)
        else:
            raise ValueError('Expected JSON value')

    first = tokens.next()
    if first != '{':
        raise ValueError('Catalog must be a JSON object')
    value(first, destination, ())
    if tokens.next() is not None:
        raise ValueError('Unexpected content after JSON object')
    if not stats['models']:
        raise ValueError('No model entries found; output not replaced')
    return stats


def compact_file(input_path, output_path):
    source, destination = Path(input_path), Path(output_path)
    if source.resolve() == destination.resolve():
        raise ValueError('Keep the original: input and output must be different files')
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=destination.parent,
                                         delete=False) as output:
            temporary = Path(output.name)
            with source.open(encoding='utf-8-sig') as stream:
                stats = compact_stream(stream, output)
            output.write('\n')
        stats.update(input_bytes=source.stat().st_size, output_bytes=temporary.stat().st_size,
                     original_preserved=True,
                     note='Only model dmr_profiles removed. All other data retained; source import counts describe the original import.')
        temporary.replace(destination)
        return stats
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(compact_file(args.input, args.output), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
