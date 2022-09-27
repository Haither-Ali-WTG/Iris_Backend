"""
Script reads data from mongo and prints to stdout
"""

import argparse
from datetime import datetime
import logging
import os
import sys

import yaml
from pymongo import MongoClient

def main():
    """Function reads data from mongo and prints to stdout"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', type=str, default="lethe.dante.wtg.ws")
    parser.add_argument('--port', type=int, default=27017)
    parser.add_argument('--username', '-u', type=str, default="charon")
    parser.add_argument('--password', '-p', type=str)
    parser.add_argument('--db', type=str, default="charon")
    parser.add_argument('--replicaSet', default="au2-lethe-a")
    parser.add_argument('--authenticationDatabase', type=str, default="admin")
    parser.add_argument('--collection', type=str,
                        default="default-haproxy-collection")
    parser.add_argument('--output_path', '-o', help="Output file path",
                        type=str, default='mongo_output')
    parser.add_argument('--output_file_name', '-of', help="Output file name",
                        type=str, default='websites_output.yml')
    parser.add_argument('--debug_output', type=int, default=1)
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug_output else logging.INFO,
                        format="%(name)s - %(levelname)s - %(message)s")
    logger = logging.getLogger("Output sites from mongo")

    logger.info('Mongo port: %i', args.port)
    logger.info('Mongo host: %s', args.host)
    logger.info('Mongo user: %s', args.username)
    logger.info('Mongo auth source: %s', args.authenticationDatabase)
    logger.info('Mongo database: %s', args.db)
    logger.info('Mongo collection: %s', args.collection)
    logger.info('Output path: %s', args.output_path)
    logger.info('Output file name: %s', args.output_file_name)

    start_time = datetime.now()

    if not os.path.exists(args.output_path):
        os.mkdir(args.output_path)

    servers = {}

    with MongoClient(f"mongodb://{args.host}:{args.port}/",
                     username=args.username,
                     password=args.password,
                     authSource=args.authenticationDatabase,
                     w="majority",
                     replicaSet=args.replicaSet) as connection:
        db = connection[args.db]
        collection = db[args.collection]
        cursor = collection.find({})

        for document in cursor:
            servers[document['server_name']] = document

    logger.info("Total servers loaded: %i", len(servers))
    logger.info("Total websites loaded: %i",
        sum(len(server['services']) for server in servers.values()))

    with open(f"{args.output_path}/{args.output_file_name}", 'w', encoding="utf8") as outfile:
        yaml.dump(servers, outfile, default_flow_style=None)

    logger.info("Execution duration:: %s", str(datetime.now() - start_time))
    return 0

if __name__ == "__main__":
    sys.exit(main())
