#!/usr/bin/python

'''
Flow completion time client

This client keeps a persistent TCP connection and runs multiple
short flows.

@author: Alexander Froemmgen
'''

import socket
import sys
from struct import *
from timeit import default_timer as timer

import fct_lib

if __name__ == '__main__':
    host = '10.0.0.2'
    port = 5000
    numberOfFlows = 10
    flowSize = 10
    outputFile = "fct_client.log"
    direction = "send"
    wait_for_both_subflows = False

    if len(sys.argv) > 1:
        host = sys.argv[1]
    else:
        print "usage: client.py <host> <port> <numberOfFlows> <flowSize> <direction> <outputFile> <scheduler> <wait_for_both_subflows>"
        print "note: <direction> = send OR receive, both client and server expect the SAME value"
        sys.stdout.flush()
        exit()

    if len(sys.argv) > 2:
        port = int(sys.argv[2])

    if len(sys.argv) > 3:
        numberOfFlows = int(sys.argv[3])

    if len(sys.argv) > 4:
        flowSize = int(sys.argv[4])

    if len(sys.argv) > 5:
        direction = sys.argv[5]

    if len(sys.argv) > 6:
        outputFile = sys.argv[6]
    
    if len(sys.argv) > 7:
        scheduler = sys.argv[7]
    
    if len(sys.argv) > 7:
        wait_for_both_subflows = bool(sys.argv[7])
    
    print "Client is starting to ", host
    sys.stdout.write("IS CONNECTED\n")
    sys.stdout.flush()
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)

    s.connect((host, port))
    
    if scheduler != "norbs":
        s.setsockopt(socket.IPPROTO_TCP, getattr(socket, 'MPTCP_SCHEDULER', 44), scheduler)

    sys.stdout.write("CONNECTED\n")
    sys.stdout.flush()

    if direction == "send":
        fct_lib.runSender(s, flowSize, numberOfFlows, outputFile, scheduler, wait_for_both_subflows)
    elif direction == "receive":
        fct_lib.runReceiver(s, flowSize, numberOfFlows, outputFile, scheduler, wait_for_both_subflows)
    else:
        print "unexpected direction", direction
