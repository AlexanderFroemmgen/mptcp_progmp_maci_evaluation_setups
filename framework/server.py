#!/usr/bin/python

'''
Flow completion time server

This server keeps a persistent TCP connection and receives multiple
short flows.

@author: Alexander Froemmgen
'''

import time
import socket
import sys

from struct import *
from timeit import default_timer as timer


import fct_lib

if __name__ == '__main__':
    port = 5000
    numberOfFlows = 10
    flowSize = 10
    outputFile = "fct_server.log"
    direction = "receive"
    scheduler = "simple"
    wait_for_both_subflows = False

    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        print "usage: fct_server.py <port> <numberOfFlows> <flowSize> <direction> <outputFile> <scheduler> <wait_for_both_subflows>"
        print "note: <direction> = send OR receive, both client and server expect the SAME value"
        sys.stdout.flush()
        exit()

    if len(sys.argv) > 2:
        numberOfFlows = int(sys.argv[2])

    if len(sys.argv) > 3:
        flowSize = int(sys.argv[3])

    if len(sys.argv) > 4:
        direction = sys.argv[4]

    if len(sys.argv) > 5:
        outputFile = sys.argv[5]

    if len(sys.argv) > 6:
        scheduler = sys.argv[6]
    
    if len(sys.argv) > 7:
        wait_for_both_subflows = bool(sys.argv[7])
        
    print "Server is starting"

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
    s.bind(("", port))
    s.listen(1)
    conn, addr = s.accept()
    
    print "Server connected"

    if scheduler != "norbs":
        conn.setsockopt(socket.IPPROTO_TCP, getattr(socket, 'MPTCP_SCHEDULER', 44), scheduler)
    sys.stdout.write("CONNECTED WITH " + str(addr) + "\n")
    sys.stdout.flush()

    # send => client send
    if direction == "send":
        fct_lib.runReceiver(conn, flowSize, numberOfFlows, outputFile, scheduler, wait_for_both_subflows)
    elif direction == "receive" :
        fct_lib.runSender(conn, flowSize, numberOfFlows, outputFile, scheduler, wait_for_both_subflows)
    else:
        print "unexpected direction", direction

    s.close()
