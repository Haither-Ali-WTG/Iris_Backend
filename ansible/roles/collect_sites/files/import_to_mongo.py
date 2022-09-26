"""
Script imports data from json files to mongo
"""

import argparse
import logging
import socket
import sys
import yaml

from glob import glob
from datetime import datetime
from os import path

from pymongo import MongoClient

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--servers_config_wildcard', type=str, default='servers/*.yml')
    parser.add_argument('--host', type=str, default="lethe.dante.wtg.ws")
    parser.add_argument('--port', type=int, default=27017)
    parser.add_argument('--username', '-u', type=str, default="charon")
    parser.add_argument('--password', '-p', type=str)
    parser.add_argument('--db', type=str, default="charon")
    parser.add_argument('--replicaSet', default="au2-lethe-a")
    parser.add_argument('--authenticationDatabase', type=str, default="admin")
    parser.add_argument('--collection', type=str,
                        default="default-haproxy-collection")
    parser.add_argument('--debug_output', type=int, default=1)

    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug_output else logging.INFO,
                        format="%(name)s - %(levelname)s - %(message)s")
    logger = logging.getLogger("import servers data to mongo")

    logger.info('Server files are loaded from: %s', args.servers_config_wildcard)
    logger.info('Mongo port: %i', args.port)
    logger.info('Mongo host: %s', args.host)
    logger.info('Mongo user: %s', args.username)
    logger.info('Mongo auth source: %s', args.authenticationDatabase)
    logger.info('Mongo database: %s', args.db)
    logger.info('Mongo collection: %s', args.collection)

    start_time = datetime.now()

    with MongoClient("mongodb://{0}:{1}/".format(args.host, args.port),
                     username=args.username,
                     password=args.password,
                     authSource=args.authenticationDatabase,
                     w="majority",
                     replicaSet=args.replicaSet) as connection:

        db = connection[args.db]
        collection = db[args.collection]

        config_files = glob(args.servers_config_wildcard)

        for config in config_files:
            server_name = path.basename(config)
            server_name = path.splitext(server_name)[0]

            server_data = dict()
            with open(config, 'r') as stream:
                try:
                    server_data['services'] = yaml.safe_load(stream)
                except yaml.YAMLError as exc:
                    print(exc)

            server_data['server_name'] = server_name
            try:
                server_data['ip'] = socket.gethostbyname(server_name)
            except socket.gaierror:
                server_data['ip'] = 'unresolved'
                logger.info("Unable to resolve hostname: %s", server_name)

            collection.replace_one({"server_name": server_name}, server_data, upsert=True)
            logger.info('Server data uploaded: %s', server_name)

    logger.info("Execution duration: %s", str(datetime.now() - start_time))
    return 0

if __name__ == "__main__":
    sys.exit(main())
