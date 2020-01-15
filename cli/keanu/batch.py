import operator
from . import util

class Batch:
    def __init__(_, mode):
        """
        mode - running mode of this batch. Map containing:
        = {
          incremental - boolean - whether to avoid updating data that did not change (optimization)
          order - string - order specification, limiting scripts to run
          dry_run - boolean - if set, don't execute statements for real
          display - boolean - display more information
          warn - boolean - display warnings (supressed by default)
          rewind - boolean - run in rewind mode
          }
        """
        _.mode = {
            'incremental': False,
            'display': False,
            'warn': False,
            'dry_run': False,
            'rewind': False
        }

        _.mode.update(mode)
        _.sources = []
        _.destination = None
        _.scripts = []

    def add_source(_, source):
        _.sources.append(source)

    def add_destination(_, destination):
        _.destination = destination

    def add_transform(_, transform):
        """
        Gets all scripts from this transform and stores them in sorted order
        """
        _.scripts += transform.get_scripts()
        if 'order' in _.mode:
            _.scripts = util.filter_scripts_by_order(_.scripts, _.mode['order'])
        _.scripts = _.sort(_.scripts)
        if _.mode['rewind']:
            _.scripts.reverse()

    def execute(_):
        for scr in _.scripts:
            if _.mode['rewind'] == False:
                for e,d in scr.execute():
                    yield e, d
            else:
                for e,d in scr.delete():
                    yield e, d

    def find_source(_, criteria):
        for s in reversed(_.sources):
            if criteria(s):
                return s
        return None

    @staticmethod
    def sort(scripts):
        scripts.sort(key=operator.attrgetter('order'))
        return scripts

