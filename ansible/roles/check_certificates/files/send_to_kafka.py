"""
Script data to specified kafka queue
"""
import argparse
import logging

from kafka import KafkaProducer

def main():
    """Function sends data to specified topic"""
