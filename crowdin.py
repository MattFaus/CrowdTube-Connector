"""Most of this code copied from upload_i18n.py and download_i18n.py, written
by Craig Silverstein for Khan Academy's i18n effort.

See here for reference:  http://crowdin.net/page/api
"""
import cStringIO
import json
import requests
import zipfile

import secrets

class CrowdInZipFile(object):

    def __init__(self, zip_file):
        self.zip_file = zipfile.ZipFile(cStringIO.StringIO(zip_file))

    @staticmethod
    def get_po_path(title, video_id):
        # TODO(mattfaus): Perform more complex foldering
        return 'subtitles/%s~%s.po' % (title, video_id)

    def get_file_count(self):
        return len(self.zip_file.namelist())

    def get_all_translations(self, file_path):
        """Finds all translations of a specific file_path.

        Returns a dict like: {
            language: pot_format_translated_content,
        }
        """
        found_translations = {}

        for filename in self.zip_file.namelist():
            if filename.endswith('/'):  # a directory
                continue

            locale = filename.split('/', 1)[0]
            path = filename.split('/', 1)[1]

            if path == file_path:
                found_translations[locale] = self.zip_file.read(filename).decode('utf-8')

        return found_translations


class CrowdInClient(object):

    EXPORT_SUCCESS_CODES = ('built', 'success')

    def __init__(self, identifier, key):
        self.identifier = identifier
        self.key = key

    def _build_api_url(self, action):
        """Generate a URL needed for making a request to the translation API."""
        url = ('http://api.crowdin.net/api/project/%(ident)s/%(action)s?key=%(key)s'
               '&json=')  # Causes returns to be JSON instead of XML-encoded

        return (url % {
            'ident': self.identifier,
            'key': self.key,
            'action': action
        })

    def _handle_error_response(self, response):
        if response.status_code != 200:
            print response.status_code, response.content
            return True
        return False

    # Management-related functions
    ###########################################################################
    def edit_project(self, **kwargs):
        """
        http://crowdin.net/page/api/edit-project
        """
        url = self._build_api_url('edit-project')

        bool_fields = (
            'hide_duplicates',
            'export_approved_only',
            'public_downloads',
        )

        # Translate python-bools to crowdin-bools, which are '1' or '0'
        for field in bool_fields:
            if kwargs.get(field) and isinstance(kwargs[field], bool):
                kwargs[field] = str(int(kwargs[field]))

        response = requests.post(url, data=kwargs)

        if self._handle_error_response(response):
            return False
        return True

    # Download-related functions
    ###########################################################################

    def get_project_info(self):
        """Looks like:
        {
          "languages": [
            {
              "code": "ro",
              "name": "Romanian"
            },
            {
              "code": "pt-BR",
              "name": "Portuguese, Brazilian"
            }
          ],
          "files": [
            {
              "node_type": "file",
              "last_accessed": "2013-07-20 11:45:06",
              "last_updated": "2013-04-03 23:28:05",
              "name": "video1.pot",
              "created": "2013-04-04 05:28:28"
            },
            {
              "node_type": "file",
              "last_accessed": "0000-00-00 00:00:00",
              "last_updated": "2013-07-20 13:25:15",
              "name": "testVideo1.sub.pot",
              "created": "2013-07-20 13:25:15"
            },
            {
              "files": [
                {
                  "files": [],
                  "node_type": "directory",
                  "name": "test2"
                }
              ],
              "node_type": "directory",
              "name": "test1"
            }
          ],
          "details": {
            "invite_url": "http://crowdin.net/project/ka-subtitles-test/invite?d=d5m676g6l6j5e5m49313e323",
            "description": "",
            "join_policy": "private",
            "created": "2013-04-04 05:28:28",
            "source_language": {
              "code": "en",
              "name": "English"
            },
            "last_activity": "2013-07-20 13:25:15",
            "last_build": "0000-00-00 00:00:00",
            "identifier": "ka-subtitles-test",
            "name": "KA subtitles test"
          }
        }
        """
        project_info_url = self._build_api_url('info')
        return requests.post(project_info_url).json()

    def get_files_and_dirs(self, project_info=None, dir_prefix=''):
        """Returns all files and directories currently in crowdin.

        If a file is in a subdir, the filename is 'dir/subdir/filename'.

        Arguments:
            project_info: used for recursive calls.
            dir_prefix: used for recursive calls.

        Returns (x, y), where:
            x - a list of all files in CrowdIn
            y - a list of all directories in CrowdIn

        """
        if project_info == None:
            project_info = self.get_project_info()

        found_files = set()
        found_dirs = set()
        for entry in project_info.get('files', []):
            if entry['node_type'] == 'file':
                found_files.add(dir_prefix + entry['name'])
            elif entry['node_type'] == 'directory':
                new_prefix = '%s%s/' % (dir_prefix, entry['name'])
                sub_files, sub_dirs = self.get_files_and_dirs(entry, new_prefix)
                found_files.update(sub_files)
                sub_dirs = set(['%s%s' % (dir_prefix, d) for d in sub_dirs])
                found_dirs.update(sub_dirs)

        if dir_prefix:
            found_dirs.add('%s/' % project_info['name'])

        return (found_files, found_dirs)

    def build_export_zip(self, approved_only=True):
        """Build ZIP archive with the latest translations. Please note that
        this method can be invoked only once for 30 minutes. Also API call will
        be ignored if there were no any changes in project since last export.

        http://crowdin.net/page/api/export

        Returns:
            On failure, the entire response json object.
            On success, the status, usually 'built' or 'skipped'.
                'built' means the .zip file was created and can be downloaded
                'skipped' is returned if there have been no changes since the
                last export
                TODO(mattfaus): Is 'skipped' also returned if you call more
                frequently than once per 30 mins?
        """
        self.edit_project(export_approved_only=approved_only)

        url = self._build_api_url('export')
        response = requests.post(url)

        if self._handle_error_response(response):
            return response.json()
        else:
            return response.json()['success']['status']

    def download_translations(self, package='all'):
        """Download ZIP file with translations. You can choose the language of
        translation you need or download all of them at once.

        http://crowdin.net/page/api/download

        Returns:
            The zip file.
        """
        url = self._build_api_url('download/%s.zip' % package)

        response = requests.get(url)

        if self._handle_error_response(response):
            return None
        else:
            return response.content


    # Upload-related functions
    ###########################################################################

    def add_directory(self, name):
        """
        http://crowdin.net/page/api/add-directory
        """
        url = self._build_api_url('add-directory')
        data = { 'name': name }

        response = requests.post(url, data=data)

        if response.status_code != 200:
            print response.status_code, response.content
            return False
        else:
            return True

    def sync_files(self, files):
        """Intelligently adds or updates files by checking to see if they
        already exist on CrowdIn and issuing the relevant call.

        Also, creates directories as needed.

        Arguments:
            files - A dict like: {
                'full/file/path/video.pot': file-like-object of contents
            }

        """
        existing_files, existing_dirs = self.get_files_and_dirs()

        files_to_upload = set(files.keys())
        directories_to_upload = set([f[:f.rfind('/')+1] for f in files_to_upload])

        add_directories = directories_to_upload - existing_dirs
        for add_dir in add_directories:
            self.add_directory(add_dir)

        add_files = sorted(files_to_upload - existing_files)
        delete_files = sorted(existing_files - files_to_upload)
        update_files = sorted(files_to_upload & existing_files)

        self.add_files({ k:files[k] for k in add_files })
        self.update_files({ k:files[k] for k in update_files })

        # TODO(mattfaus): Return (error_files, to_delete_files)

    def _split_dict(self, files, batch_size):
        """Returns two dicts: the first contains the first batch_size entries,
        the next contains everything else.
        """
        items = files.items()  # Does not return repeatable results
        return (
            dict(items[:batch_size]),
            dict(items[batch_size:])
        )

    def _format_files_dict(self, files):
        """Translates a file dict to the special naming CrowdIn wants."""
        formatted_dict = {}
        for key, value in files.iteritems():
            formatted_dict['files[%s]' % key] = value

        return formatted_dict

    def _upload_files(self, action, files, batch_size):
        """

        Arguments:
            action - one of ('add-file', 'update-file')
            files - A dict like: {
                'full/file/path/video.pot': file-like-object of contents
            }
            batch_size - how many files to upload at once
        """
        url = self._build_api_url(action)
        error_files = []

        while files:
            files_batch, files = self._split_dict(files, batch_size)
            files_batch = self._format_files_dict(files_batch)

            response = requests.post(url, files=files_batch)

            if response.status_code != 200:
                print response.status_code, response.content
                # TODO(mattfaus): Parse the response better, I imagine there
                # is 1 error message per file attempted
                error_files += files_batch.keys()

        return error_files

    def add_files(self, files, batch_size=10):
        """
        http://crowdin.net/page/api/add-file

        Arguments:
            files - A dict like: {
                'full/file/path/video.pot': file-like-object of contents
            }
        """
        return self._upload_files('add-file', files, batch_size)

    def update_files(self, files, batch_size=10):
        """
        http://crowdin.net/page/api/update-file

        Arguments:
            files - A dict like: {
                'full/file/path/video.pot': file-like-object of contents
            }
        """
        return self._upload_files('update-file', files, batch_size)


# A quick test to make sure your CrowdIn credentials are working
if __name__ == "__main__":
    client = CrowdInClient(secrets.crowdin_ident, secrets.crowdin_key)

    print json.dumps(client.get_project_info(), indent=2)

    # files = client.get_files()
    # print files
