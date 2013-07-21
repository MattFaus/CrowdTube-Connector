import cStringIO
import re


class TranscriptReader(object):
    """Returns subtitle entries stored in either a .sub file or a .pot file."""
    # 0:00:01.389,0:00:06.839
    REGEX_TIMESTAMP = '((?P<start_time>\d:\d\d:\d\d(\.\d\d\d)?),(?P<end_time>\d:\d\d:\d\d(\.\d\d\d)?))'

    def list_entries(self):
        # Sort dictionary entries by their keys
        keys = self.entries.keys()
        keys.sort()

        # TODO(mattfaus): Create named tuples for more readable code?
        return [(k, self.entries[k]) for k in keys]


class SubTranscriptReader(TranscriptReader):

    def __init__(self, content):
        self.content = content
        self._build_entries()

    def _build_entries(self):
        timestamp_regex = re.compile(self.REGEX_TIMESTAMP)

        self.entries = {}

        cur_timestamp = None
        cur_string = ""

        for line in self.content.splitlines():
            timestamp_match = timestamp_regex.search(line)

            if cur_timestamp:
                if not line:  # Entries are seperated by a blank lin
                    # Remove the last newline
                    cur_string = cur_string[:-1]
                    self.entries[cur_timestamp] = cur_string
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
            self.entries[cur_timestamp] = cur_string[:-1]
            cur_timestamp = None
            cur_string = ""


class PotTranscriptReader(TranscriptReader):

    MSGID_BREAKER = 'msgid "'
    MSGSTR_BREAKER = 'msgstr "'

    def __init__(self, content):
        self.content = content
        self._build_entries()

    def _build_entries(self):
        timestamp_regex = re.compile(self.REGEX_TIMESTAMP)

        self.entries = {}

        cur_timestamp = None
        cur_id = ""
        cur_string = ""

        # TODO(mattfaus): Try to do this with a regex instead?
        # http://stackoverflow.com/questions/8433686/is-there-a-php-library-for-parsing-gettext-po-pot-files
        # #: ((?P<start_time>\d:\d\d:\d\d(\.\d\d\d)?),(?P<end_time>\d:\d\d:\d\d(\.\d\d\d)?)).*\n.*msgid\s+("(.*)"\s+)+msgstr

        for line in self.content.splitlines():
            if not line and cur_timestamp and cur_string:
                # We found one, so add it and continue
                self.entries[cur_timestamp] = cur_string[:-1]  # remove last \n
                cur_timestamp = None
                cur_id = ""
                cur_string = ""
                continue

            if not cur_timestamp:
                # We're looking for the next timestamp
                timestamp_match = timestamp_regex.search(line)
                if timestamp_match:
                    cur_timestamp = timestamp_match.groups()[0]
            else:
                if not cur_id:
                    # We're looking for the next msgid
                    if line.startswith(self.MSGID_BREAKER):  # 'msgid "'
                        cur_id += line[len(self.MSGID_BREAKER):-1] + '\n'
                elif line.startswith('"'):
                    cur_id += line[1:-1] + '\n'

                if not cur_string:
                    # We're looking for the next msgstr
                    if line.startswith(self.MSGSTR_BREAKER):  # 'msgstr "'
                        cur_string += line[len(self.MSGSTR_BREAKER):-1] + '\n'
                elif line.startswith('"'):
                    # We're building cur_string
                    cur_string += line[1:-1] + '\n'

        if cur_timestamp and cur_string:
            # We found one, so add it and continue
            self.entries[cur_timestamp] = cur_string[:-1]  # remove last \n


class TranscriptWriter(object):
    def __init__(self, reader):
        if not isinstance(reader, TranscriptReader):
            raise ValueError('Must pass a TranscriptReader')

        self.reader = reader

    def get_file(self):
        """Returns a file-like object with the contents of the transcript."""
        return cStringIO.StringIO(self.content)

    def get_file(self):
        return cStringIO.StringIO(self.content)


class PotTranscriptWriter(TranscriptWriter):

    ENTRY_FORMAT = (
"""#: %(timestamp)s
msgid \"%(text)s\"
msgstr \"%(text)s\"

""")

    def __init__(self, reader):
        super(PotTranscriptWriter, self).__init__(reader)
        self._build_pot_file()

    def _format_line(self, line):
        return line.replace('\n', "\"\n\"")

    def _build_pot_file(self):
        self.content = ""

        for entry in self.reader.list_entries():
            self.content += self.ENTRY_FORMAT % {
                'timestamp': entry[0],
                'text': self._format_line(entry[1]),
            }


class SubTranscriptWriter(TranscriptWriter):

    ENTRY_FORMAT = (
"""%(timestamp)s
%(text)s

""")

    def __init__(self, reader):
        super(SubTranscriptWriter, self).__init__(reader)
        self._build_sub_file()

    def _build_sub_file(self):
        self.content = ""

        for entry in self.reader.list_entries():
            self.content +=self.ENTRY_FORMAT % {
                'timestamp': entry[0],
                'text': entry[1],
            }

