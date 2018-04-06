#!/usr/bin/python

'''
Flow completion time lib

@author: Alexander Froemmgen
'''

import socket
import sys
import time

from struct import *
from timeit import default_timer as timer

def setRegister(s, value, register = 0):
    MPTCP_RBS_REGISTER = 45
    sValue = pack('II', register, value)
    s.setsockopt(socket.IPPROTO_TCP, MPTCP_RBS_REGISTER, sValue)
    
def runFlowAsSender(s, content, scheduler):
    if scheduler != "norbs":
        setRegister(s, 0)
        
    begin = timer()
    s.sendall(content)
    
    if scheduler != "norbs":
        # inform scheduler about the end ...
        setRegister(s, 1)
    
    # ... and wait
    result = s.recv(1)
    end = timer()
    return (begin, end)

def runFlowAsReceiver(s, flowSize, scheduler):
    firstByte = True
    currentSize = 0
    while 1:
        data = s.recv(1024)
        
        if firstByte:
            firstByteTime = time.time()
            firstByte = False
        
        if not data: 
            print "why can this happen?"
            break

        currentSize = currentSize + len(data)
        
        if flowSize == currentSize:
            return (firstByteTime, time.time())
        elif flowSize < currentSize:
            print "how can this happen"
            exit()


def runSender(s, flowSize, numberOfFlows, outputFile, scheduler, wait_for_both_subflows):
    if wait_for_both_subflows:  
        runFlowAsSender(s, "a", scheduler)
        time.sleep(3) # we want to ensure subflows are created                                                                                                             
    content = "a" * flowSize
    results = []
    for i in range(numberOfFlows):
        results.append(runFlowAsSender(s, content, scheduler))

    s.close()

    output = open(outputFile, 'w')
    output.write("flow_begin\tflow_end\tflow_duration\n")

    for (begin, end) in results:
        output.write(str(begin) + "\t" + str(end) + "\t" + str(end - begin) + "\n")
    output.close()

def runReceiver(s, flowSize, numberOfFlows, outputFile, scheduler, wait_for_both_subflows):
    if wait_for_both_subflows:
        runFlowAsReceiver(s, 1, scheduler)
        s.send(" ")
    results = []
    for i in range(numberOfFlows):
        results.append(runFlowAsReceiver(s, flowSize, scheduler))
        s.send(" ")

    #wait before we close...
    
    time.sleep(5)
    s.close()

    output = open(outputFile, 'w')
    output.write("first_byte\tlast_byte\n")

    for (first, last) in results:
        output.write(str(first) + "\t" + str(last) + "\n")

    output.close()
