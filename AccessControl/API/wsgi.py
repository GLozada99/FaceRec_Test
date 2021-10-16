import argparse
from AccessControl.API.api import app


def serve(debug):
    app.run(host='0.0.0.0', debug=debug)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--debug', action='store_true')
    args = vars(ap.parse_args())
    serve(args['debug'])
