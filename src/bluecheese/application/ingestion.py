"""Bounded append-only file follower; caller serializes database access."""
import hashlib
import os
from pathlib import Path


class SourceGap(RuntimeError):
    pass


class EveFollower:
    def __init__(self, store, path, scenario='live', variant='replay',
                 max_read=262144, max_line=65536):
        self.store = store
        self.path = Path(path).resolve()
        self.source = f'file:{self.path}'
        self.scenario, self.variant = scenario, variant
        self.max_read, self.max_line = max_read, max_line
        cursor = store.db.execute('SELECT identity,offset_bytes,prefix_hash FROM cursors WHERE source=?', [self.source]).fetchone()
        self.identity, self.committed, self.prefix_hash = cursor or (None, 0, '')
        self.scanned = self.committed
        self.pending = b''
        self.oversized = False
        self.line_start = self.committed

    def poll_once(self):
        with self.path.open('rb') as stream:
            stat = os.fstat(stream.fileno())
            identity = f'{stat.st_dev}:{stat.st_ino}'
            if self.identity and (identity != self.identity or stat.st_size < self.scanned):
                raise SourceGap('Source replaced or truncated: stopped. Continuity lost; select a new file/state to reset. Full rotation recovery is deferred.')
            stream.seek(0)
            prefix = stream.read(min(self.committed, 4096))
            if self.prefix_hash and hashlib.sha256(prefix).hexdigest() != self.prefix_hash:
                raise SourceGap('Committed source prefix changed: stopped with a continuity gap.')
            self.identity = identity
            stream.seek(self.scanned)
            chunk = stream.read(self.max_read)
            new_stat = self.path.stat()
            if f'{new_stat.st_dev}:{new_stat.st_ino}' != identity or new_stat.st_size < self.scanned + len(chunk):
                raise SourceGap('Source changed while reading: stopped with a continuity gap.')
        if not chunk:
            return dict(bytes_read=0, committed_offset=self.committed, partial_bytes=self.scanned-self.committed)
        old_state = (self.scanned, self.pending, self.oversized, self.line_start, self.committed, self.prefix_hash)
        self.store.db.execute('BEGIN')
        try:
            parts = chunk.split(b'\n')
            for index, part in enumerate(parts):
                complete = index < len(parts) - 1
                piece = part + (b'\n' if complete else b'')
                self.scanned += len(piece)
                if len(self.pending) + len(piece) > self.max_line:
                    self.oversized = True
                self.pending = (self.pending + piece)[:self.max_line]
                if not complete:
                    continue
                source_identity = f'{self.source}#{identity}'
                if self.oversized:
                    self.store.db.execute('INSERT INTO quarantine VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING',
                        [self.scenario, self.variant, source_identity, self.line_start,
                         self.pending, f'Line exceeds {self.max_line} bytes; raw quarantine prefix truncated'])
                else:
                    self.store.insert(self.scenario, self.variant, source_identity, self.line_start, self.pending)
                self.committed = self.scanned
                self.line_start = self.scanned
                self.pending = b''
                self.oversized = False
            with self.path.open('rb') as stream:
                self.prefix_hash = hashlib.sha256(stream.read(min(self.committed, 4096))).hexdigest()
            self.store.db.execute('INSERT INTO cursors VALUES (?, ?, ?, ?) ON CONFLICT(source) DO UPDATE '
                                  'SET identity=excluded.identity, offset_bytes=excluded.offset_bytes, prefix_hash=excluded.prefix_hash',
                                  [self.source, identity, self.committed, self.prefix_hash])
            self.store.db.execute('COMMIT')
        except Exception:
            self.store.db.execute('ROLLBACK')
            self.scanned, self.pending, self.oversized, self.line_start, self.committed, self.prefix_hash = old_state
            raise
        return dict(bytes_read=len(chunk), committed_offset=self.committed, partial_bytes=self.scanned-self.committed)
