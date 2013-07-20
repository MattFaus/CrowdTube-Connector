import cStringIO
import re

Format = {
    'SRT': '.srt',
    'POT': '.pot',
}

class Convertor(object):

    def __init__(self, original, format):
        self._check_format(format)
        self.original = original
        self.format = format
        self.file_content = {}

        self.file_content[self.format] = self.original

    def _check_format(self, format):
        if format not in Format:
            raise ValueError('Format %s not understood.' % format)

    def convert_to(self, format):
        self._check_format(format)

        if self.file_content[format]:
            # Conversion has already been done
            return self.file_content[format]

        if self.format == 'SRT' and format == 'POT':
            new_file_content = self.convert_from_srt_to_pot(self.original)

        self.file_content[format] = new_file_content

    @staticmethod
    def convert_from_srt_to_pot(self, srt_content):
        pass


class TranscriptReader(object):

    def list_entries(self):
        """Returns a list of (timestamp, content) tuples in time-order."""
        raise NotImplemented('Sub-classes must implement this.')


class SrtTranscriptReader(TranscriptReader):

    SRT_REGEX_SORT_ID = '\d'
    SRT_REGEX_TIMESTAMP = '((?P<start_time>\d\d:\d\d:\d\d(,\d)?) --> (?P<end_time>\d\d:\d\d:\d\d(,\d)?))'

    def __init__(self, content):
        self.content = content
        self._build_entries()

    def _build_entries(self):
        sort_id_regex = re.compile(self.SRT_REGEX_SORT_ID)
        timestamp_regex = re.compile(self.SRT_REGEX_TIMESTAMP)

        self.entries = {}

        cur_timestamp = None
        cur_string = ""

        # TODO(mattfaus): Implement.

    def list_entries(self):
        # Sort dictionary entries by their keys
        keys = self.entries.keys()
        keys.sort()

        # TODO(mattfaus): Create named tuples for more readable code?
        return [(k, self.entries[k]) for k in keys]


class SubTranscriptReader(TranscriptReader):
    # 0:00:01.389,0:00:06.839
    SUB_REGEX_TIMESTAMP = '((?P<start_time>\d:\d\d:\d\d(\.\d\d\d)?),(?P<end_time>\d:\d\d:\d\d(\.\d\d\d)?))'

    def __init__(self, content):
        self.content = content
        self._build_entries()

    def _build_entries(self):
        timestamp_regex = re.compile(self.SUB_REGEX_TIMESTAMP)

        self.entries = {}

        cur_timestamp = None
        cur_string = ""

        for line in self.content.splitlines():
            timestamp_match = timestamp_regex.search(line)

            if cur_timestamp:
                if not line:
                    # Remove the last newline
                    cur_string = cur_string[:-1]
                    self.entries[cur_timestamp] = (cur_timestamp, cur_string)
                    cur_timestamp = None
                    cur_string = ""
                else:
                    cur_string += line + '\n'
            else:
                if not line:
                    # Extra whitespace / end of file?
                    pass
                elif timestamp_match:
                    cur_timestamp = line
                else:
                    raise ValueError('Format not understood')

        if cur_timestamp and cur_string:
            self.entries[cur_timestamp] = (cur_timestamp, cur_string)
            cur_timestamp = None
            cur_string = ""

    def list_entries(self):
        # Sort dictionary entries by their keys
        keys = self.entries.keys()
        keys.sort()

        # TODO(mattfaus): Create named tuples for more readable code?
        return [(k, self.entries[k][1]) for k in keys]


class TranscriptWriter(object):
    def get_file(self):
        """Returns a file-like object with the contents of the transcript."""
        raise NotImplemented('Must be implemented in Sub-classes.')


class PotTranscriptWriter(TranscriptWriter):

    ENTRY_FORMAT = (
"""#: %(timestamp)s
msgid \"%(text)s\"
msgstr \"%(text)s\"

""")

    def __init__(self, reader):
        if not isinstance(reader, TranscriptReader):
            raise ValueError('Must pass a TranscriptReader')

        self.reader = reader
        self._build_pot_file()

    def _format_line(self, line):
        return line.replace('\n', "\"\n\"")

    def _build_pot_file(self):
        self.pot_content = ""

        for entry in self.reader.list_entries():
            self.pot_content += self.ENTRY_FORMAT % {
                'timestamp': entry[0],
                'text': self._format_line(entry[1]),
            }

    def get_file(self):
        # TODO(mattfaus): Move into base class?
        return cStringIO.StringIO(self.pot_content)
