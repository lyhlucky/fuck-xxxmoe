# coding: utf8

import json
import traceback
import sys
import os
import logging
import time

appVersion = 'v8.0.1'

def main():
    version = appVersion
    if len(sys.argv) != 2 or sys.argv[1].find('.json') == -1:
        print(version)
        sys.exit(0)

    open_encodings = [None, 'utf-8-sig']
    params_loaded = False
    for encoding in open_encodings:
        try:
            with open(sys.argv[1], 'r', encoding=encoding) as json_file:
                params = json.load(json_file)
                params_loaded = True
        except Exception as e:
            pass

    if not params_loaded:
        print('params load failed')
        sys.exit(0)

    log_file = os.path.join(params['log_path'], f'dl.{int(time.time()*1000)}.log')
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(name)-8s %(levelname)-8s %(message)s',
                        filename=log_file
                        )

    logger = logging.getLogger('main')

    logger.info('dl tool version: ' + version)

    from manager import Manager
    from common import flush_print
    from common import MsgType

    try:
        params['params_filepath'] = sys.argv[1]
        m = Manager(params)
        m.process()

    except Exception as e:
        m.exitSubloop()
        traceback.print_exc()
        resp = {
            'type': MsgType.finished.value,
            'msg': {
                'ret_code': '-1',
                'exception': e.args[0],
            },
        }
        flush_print(json.dumps(resp))
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    main()
