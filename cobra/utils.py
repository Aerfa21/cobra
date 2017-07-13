import os
import sys
import re
import hashlib
# from . import config
from .log import logger
from .exceptions import PickupException, NotExistException, AuthFailedException
from .pickup import Git, NotExistError, AuthError, support_extensions, Decompress

TARGET_MODE_GIT = 'git'
TARGET_MODE_FILE = 'file'
TARGET_MODE_FOLDER = 'folder'
TARGET_MODE_COMPRESS = 'compress'

OUTPUT_MODE_MAIL = 'mail'
OUTPUT_MODE_API = 'api'
OUTPUT_MODE_FILE = 'file'
OUTPUT_MODE_STREAM = 'stream'


class ParseArgs(object):
    def __init__(self, target, formatter, output, rule, exclude):
        self.target = target
        self.formatter = formatter
        self.output = output
        self.rule = rule
        self.exclude = exclude

    @property
    def target_mode(self):
        """
        Parse target mode (git/file/folder/compress)
        :return: str
        """
        target_mode = None
        target_git_cases = ['http://', 'https://', 'ssh://']
        for tgc in target_git_cases:
            if self.target[0:len(tgc)] == tgc:
                target_mode = TARGET_MODE_GIT

        if os.path.isfile(self.target):
            target_mode = TARGET_MODE_FILE
        if os.path.isdir(self.target):
            target_mode = TARGET_MODE_FOLDER
        if target_mode is None:
            logger.critical('[-t <target>] can\'t empty!')
            exit()
        logger.debug('Target Mode: {mode}'.format(mode=target_mode))
        return target_mode

    @property
    def output_mode(self):
        """
        Parse output mode (api/mail/file/stream)
        :return: str
        """
        output_mode = None
        output_mode_api = ['http', 'https']
        output_mode_mail = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
        if re.match(output_mode_mail, self.output) is not None:
            output_mode = OUTPUT_MODE_MAIL
        for oma in output_mode_api:
            if self.output[0:len(oma)] == oma:
                output_mode = OUTPUT_MODE_API
        if os.path.isdir(os.path.dirname(self.output)):
            output_mode = OUTPUT_MODE_FILE
        if output_mode is None:
            output_mode = OUTPUT_MODE_STREAM
        logger.debug('Output Mode: {mode}'.format(mode=output_mode))
        return output_mode

    def target_directory(self, target_mode):
        target_directory = None
        if target_mode == TARGET_MODE_GIT:
            logger.debug('GIT Project')
            branch = 'master'
            username = ''
            password = ''
            gg = Git(self.target, branch=branch, username=username, password=password)

            # Git Clone Error
            try:
                clone_ret, clone_err = gg.clone()
                if clone_ret is False:
                    raise PickupException('Clone Failed ({0})'.format(clone_err), gg)
            except NotExistError:
                raise NotExistException(4001, 'Repository Does not exist!', gg)
            except AuthError:
                raise AuthFailedException('Git Authentication Failed')
            target_directory = gg.repo_directory
        elif target_mode == TARGET_MODE_COMPRESS:
            extension = self.target.split('.')[-1]
            if extension not in support_extensions:
                logger.critical('Not support this compress extension: {extension}'.format(extension=extension))
            target_directory = Decompress(self.target).decompress()
        elif target_mode == TARGET_MODE_FOLDER:
            target_directory = self.target
        elif target_mode == TARGET_MODE_FILE:
            target_directory = self.target
        else:
            logger.critical('exception target mode ({mode})'.format(mode=target_mode))
            exit()

        logger.debug('target directory: {directory}'.format(directory=target_directory))
        return target_directory


def convert_time(seconds):
    """
    Seconds to minute/second
    Ex: 61 -> 1'1"
    :param seconds:
    :return:
    :link: https://en.wikipedia.org/wiki/Prime_(symbol)
    """
    one_minute = 60
    minute = seconds / one_minute
    if minute == 0:
        return str(seconds % one_minute) + "\""
    else:
        return str(minute) + "'" + str(seconds % one_minute) + "\""


def convert_number(number):
    """
    Convert number to , split
    Ex: 123456 -> 123,456
    :param number:
    :return:
    """
    if number is None or number == 0:
        return 0
    number = int(number)
    return '{:20,}'.format(number).strip()


def md5(content):
    """
    MD5 Hash
    :param content:
    :return:
    """
    return hashlib.md5(content).hexdigest()


def allowed_file(filename):
    """
    Allowed upload file
    Config Path: ./config [upload]
    :param filename:
    :return:
    """
    config_extension = config.Config('upload', 'extensions').value
    if config_extension == '':
        logger.critical('Please set config file upload->directory')
        sys.exit(0)
    allowed_extensions = config_extension.split('|')
    return '.' in filename and filename.rsplit('.', 1)[1] in allowed_extensions





def path_to_short(path, max_length=36):
    """
    /impl/src/main/java/com/mogujie/service/mgs/digitalcert/utils/CertUtil.java
    /impl/src/.../utils/CertUtil.java
    :param path:
    :param max_length:
    :return:
    """
    if len(path) < max_length:
        return path
    paths = path.split('/')
    paths = filter(None, paths)
    tmp_path = ''
    for i in range(0, len(paths)):
        # print(i, str(paths[i]), str(paths[len(paths) - i - 1]))
        tmp_path = tmp_path + str(paths[i]) + '/' + str(paths[len(paths) - i - 1])
        if len(tmp_path) > max_length:
            tmp_path = ''
            for j in range(0, i):
                tmp_path = tmp_path + '/' + str(paths[j])
            tmp_path += '/...'
            for k in range(i, 0, -1):
                tmp_path = tmp_path + '/' + str(paths[len(paths) - k])
            if tmp_path == '/...':
                return '.../{0}'.format(paths[len(paths) - 1])
            elif tmp_path[0] == '/':
                return tmp_path[1:]
            else:
                return tmp_path


def path_to_file(path):
    """
    Path to file
    /impl/src/main/java/com/mogujie/service/mgs/digitalcert/utils/CertUtil.java
    .../CertUtil.java
    :param path:
    :return:
    """
    paths = path.split('/')
    paths = filter(None, paths)
    return '.../{0}'.format(paths[len(paths) - 1])


def percent(part, whole, need_per=True):
    """
    Percent
    :param part:
    :param whole:
    :param need_per:
    :return:
    """
    if need_per:
        per = '%'
    else:
        per = ''
    if part == 0 and whole == 0:
        return 0
    return '{0}{1}'.format(100 * float(part) / float(whole), per)


def format_gmt(time_gmt, time_format=None):
    """
    Format GMT time
    Ex: Wed, 14 Sep 2016 17:57:41 GMT to 2016-09-14 17:57:41
    :param time_gmt:
    :param time_format:
    :return:
    """
    import time
    if time_format is None:
        time_format = '%Y-%m-%d %X'
    t = time.strptime(time_gmt, "%a, %d %b %Y %H:%M:%S GMT")
    return time.strftime(time_format, t)


class Tool:
    def __init__(self):
        # `grep` (`ggrep` on Mac)
        self.grep = '/bin/grep'
        # `find` (`gfind` on Mac)
        self.find = '/bin/find'

        if 'darwin' == sys.platform:
            ggrep = ''
            gfind = ''
            for root, dir_names, file_names in os.walk('/usr/local/Cellar/grep'):
                for filename in file_names:
                    if 'ggrep' == filename or 'grep' == filename:
                        ggrep = os.path.join(root, filename)
            for root, dir_names, file_names in os.walk('/usr/local/Cellar/findutils'):
                for filename in file_names:
                    if 'gfind' == filename:
                        gfind = os.path.join(root, filename)
            if ggrep == '':
                logger.critical("brew install ggrep pleases!")
                sys.exit(0)
            else:
                self.grep = ggrep
            if gfind == '':
                logger.critical("brew install findutils pleases!")
                sys.exit(0)
            else:
                self.find = gfind