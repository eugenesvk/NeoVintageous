import logging

DEFAULT_LOG_LEVEL = logging.WARNING
TFMT = '{t.minute:2}:{t.second:2}.{t.microsecond}'

filter_levelname_dict = {'ERROR':'❗','WARNING':'⚠️','INFO':"ⓘ",'KEY':'⌨️','CFG':'Ⓒ'}

def add_module_logger_levels():
  addLoggingLevel('KEYT', DEFAULT_LOG_LEVEL - 20)
  addLoggingLevel('KEY', DEFAULT_LOG_LEVEL - 20)
  addLoggingLevel('MAP', DEFAULT_LOG_LEVEL - 20)
  addLoggingLevel('SET', DEFAULT_LOG_LEVEL - 20)
  addLoggingLevel('CFG', DEFAULT_LOG_LEVEL - 20)

stream_handler = logging.StreamHandler()
formatter = logging.Formatter('NV%(levelname)-1s_%(filename)10s:%(lineno)-3d %(message)s')
stream_handler.setFormatter(formatter)

def filter_levelname(s:str):
  for old,new in filter_levelname_dict.items():
    if s == old:
      return new
  return s

old_factory = logging.getLogRecordFactory()
def record_factory(*args, **kwargs):
  rec           = old_factory(*args, **kwargs)
  rec.levelname = filter_levelname(rec.levelname)
  # record.custom_attribute = "my-attr"
  return rec
logging.setLogRecordFactory(record_factory)

# https://stackoverflow.com/a/35804945
def addLoggingLevel(levelName, levelNum, methodName=None):
  """
  Comprehensively adds a new logging level to the `logging` module and the currently configured logging class.
  `levelName` becomes an attribute of the `logging` module with the value `levelNum`
  `methodName` becomes a convenience method for both `logging` itself and the class returned by `logging.getLoggerClass()` (usually just `logging.Logger`). If `methodName` is not specified, `levelName.lower()` is used.
  To avoid accidental clobberings of existing attributes, this method will raise an `AttributeError` if the level name is already an attribute of the `logging` module or if the method name is already present
  Example
  addLoggingLevel('TRACE', logging.DEBUG - 5)
  logging.getLogger(__name__).setLevel("TRACE")
  logging.getLogger(__name__).trace('that worked')
  logging.trace('so did this')
  logging.TRACE
  → 5
  """
  if not methodName:
    methodName = levelName.lower()
  if hasattr(logging, levelName):
    raise AttributeError('{} already defined in logging module'.format(levelName))
  if hasattr(logging, methodName):
    raise AttributeError('{} already defined in logging module'.format(methodName))
  if hasattr(logging.getLoggerClass(), methodName):
    raise AttributeError('{} already defined in logger class'.format(methodName))

  # This method was inspired by the answers to Stack Overflow post
  # http://stackoverflow.com/q/2183233/2988730, especially
  # http://stackoverflow.com/a/13638084/2988730
  def logForLevel(self, message, *args, **kwargs):
    if self.isEnabledFor(levelNum):
      self._log(levelNum, message, args, **kwargs)
  def logToRoot(message, *args, **kwargs):
    logging.log(levelNum, message, *args, **kwargs)

  logging.addLevelName(levelNum, levelName)
  setattr(logging                 	, levelName , levelNum)
  setattr(logging.getLoggerClass()	, methodName, logForLevel)
  setattr(logging                 	, methodName, logToRoot)

add_module_logger_levels()


import time, threading
class LogToStatus():
  """change .tag after creating an instance to control status message position"""
  def __init__(self):
    self.timeout  = 3
    self.timer    = None
    self.tag      = ''

  def s(self, view, msg, overwrite=False):
    self.set_status(view, msg, overwrite)
  def set_status(self, view, msg, overwrite=False):
    self.cancel_timer()
    self.view = view
    if not view:
      return
    if overwrite:
      self.view.set_status(self.tag, msg)
    else:
      status_cur  = view.get_status(self.tag)
      sep         = '; ' if status_cur else ''
      self.view.set_status(self.tag, status_cur +sep+ msg)
    self.start_timer()

  def cancel_timer(self):
    if self.timer != None:
      self .timer.cancel()
  def start_timer(self):
    self.timer = threading.Timer(self.timeout, self.clear)
    self.timer.start()

  def clear(self):
    self.view.erase_status(self.tag)
