# Environment

### ENV int mean_bw "The mean bandwidth at the bottleneck"
### ENV int delay "The delay per link"
### ENV float delay_ratio "write description here..."
### ENV int loss [per hundred] "write description here..."
### ENV int max_queue_size "The max queue size at the bottleneck link"

# Configuration

### CFG string scheduler [filename] "write description here..."
### CFG int mptcp_debug "write description here..."
### CFG int no_heat_up [0 = default, 1] "write description here..."
### CFG int packet_trace [1 = yes, 0 = no (default)] "..."

# Traffic Pattern

### CFG string trafficPattern [iperf, fct, cbr] "write description here..."

### ENV int fct_number_of_requests "write description here..."
### ENV int fct_request_size [byte] "write description here..."
### CFG string fct_waitForSubflowEstablishment [True, False] "write description here..." 

### CFG int cbr_bitrate [kb] "write description here..."
### CFG int cbr_duration [s] "write description here..."


import framework
import os
import re 
import os.path
import subprocess 
import math

import progmp_helper
import time
from progmp import ProgMP
import bwmng

from mininet.net import Mininet
from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.node import CPULimitedHost
from mininet.topo import Topo
from mininet.node import OVSController

class StaticTopo(Topo):
    def build(self):
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')

        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')
        s4 = self.addSwitch('s4')

        # Note: it is important to *not* set delays on the first hop
        # https://progmp.net/mininetPitfalls.html

        # Topology: h1 -- s1 -- bottleneck -- s2 -- h2
        # Topology:     - s3 -- bottleneck -- s4 -  h2
        self.addLink(h1, s1)
        self.addLink(h2, s2)
        self.addLink(s1, s2, bw={{mean_bw}}, delay="{{delay}}ms", max_queue_size={{max_queue_size}}, loss={{loss}})

        delayStr = str({{delay}} * {{delay_ratio}}) + "ms"
        self.addLink(h1, s3)
        self.addLink(h2, s4)
        self.addLink(s3, s4, bw={{mean_bw}}, delay=delayStr, max_queue_size={{max_queue_size}}, loss={{loss}})

def setOneWayDelay(net, delay_out, delay_in, subflow_number):
    h1.cmd("tc qdisc change dev h1-eth" + str(subflow_number) + " parent 5:1 handle 10:0 netem delay " + str(delay_out) + "ms")
    s = net.get("s" + str(subflow_number + 1))
    s.cmd("tc qdisc change dev s" + str(subflow_number + 1) + "-eth2 parent 5:1 handle 10:0 netem delay " + str(delay_out) + "ms")

    h2.cmd("tc qdisc change dev h2-eth" + str(subflow_number) + " parent 5:1 handle 10:0 netem delay " + str(delay_in) + "ms")
    s = net.get("s" + str(subflow_number + 1))
    s.cmd("tc qdisc change dev s" + str(subflow_number + 1) + "-eth1 parent 5:1 handle 10:0 netem delay " + str(delay_in) + "ms")

def setAsymetricDelays(net):
    # prepare asymetric delays
    # Keep RTT constant.
    # O + I = Const
    # O / I = R
    # => I = Const - O
    # => I = Const - R * I
    # => (R + 1) * I = Const
    # => I = Const / (R + 1)
    twiceDelay = float({{delay}}) * 2.0
    delay_in_sbf2 = twiceDelay / (float({{delay_ratio}}) + 1.0)
    delay_out_sbf2 = twiceDelay - delay_in_sbf2

    setOneWayDelay(net, delay_in_sbf2, delay_out_sbf2, 0)
    setOneWayDelay(net, delay_out_sbf2, delay_in_sbf2, 1)

def collectTotalSendData():
    ifconfigResult = subprocess.check_output("ifconfig", shell=True)
    framework.log("ifconfig result", ifconfigResult)

    for line in ifconfigResult.split("\n"):
        matchObj = re.match(r'(.*) Link (.*)', line, re.M)
        if matchObj:
            currentInt = matchObj.group(1)
        else:
            matchObj = re.match(r'(.*)RX bytes:(.*)\((.*) TX bytes:(.*)\((.*)', line, re.M)
            if matchObj:
                framework.record("tx_" + str(currentInt), int(matchObj.group(4)))
                framework.record("rx_" + str(currentInt), int(matchObj.group(2)))

def parseProgMpOutputLine(line):
    if "WARNINGMACI" in line:
        framework.warn("WARNINGMACI", line)
        
    matchObj = re.match(r'\[(.*)\] ProgMP (.*) (.*):(.*) (.*):(.*): (.*) = (.*)', line, re.M)
    if matchObj:
        timestamp = float(matchObj.group(1))
        meta_sk = matchObj.group(2)
        ip_source = matchObj.group(3)
        port_source = matchObj.group(4)
        ip_dest = matchObj.group(5)
        port_dest = matchObj.group(6)
        key = matchObj.group(7)
        value = int(matchObj.group(8))
        return (timestamp, meta_sk, key, value)
    return None

def parseProgMpOutput():
    currentIdForSk = {}
    minTimestamp = None
    for line in open("dmesg.log", "r"):
        result = parseProgMpOutputLine(line)
        if result is not None:
            (timestamp, meta_sk, key, value) = result
            if key == "sbfId":
                currentIdForSk[meta_sk] = value
            if minTimestamp is None:
                minTimestamp = timestamp

            if key != "sbfId":
                if meta_sk in currentIdForSk:
                    usedKey = key + "_" + str(currentIdForSk[meta_sk]) + "_" + str(meta_sk)
                    framework.record(usedKey, value, offset = float(timestamp) * 100.0 - float(minTimestamp) * 100.0)
                else:
                    framework.warn("ProgMP Parser", "Key " + str(key) + " not found as meta_sk")

def runIperfExperiment(source, destination):
    destination.cmd('iperf -s -i 1 -y C > server.log &')
    source.cmd('iperf -c ' + str(destination.IP()) + ' -t 10 > client.log')
    framework.addLogfile("server.log")
    framework.addLogfile("client.log")

    server = open('server.log', 'r')
    bwsamples = []
    minTimestamp = None
    for line in server:
        # 20160622002425,10.0.0.2,5001,10.0.0.1,39345,4,0.0-1.0,14280,114240
        matchObj = re.match(r'(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*)', line, re.M)
        if matchObj:
                timestamp = float(matchObj.group(1))
                bwsample = float(matchObj.group(9)) / 1000.0 / 1000.0 # bits per second -> MBit
                bwsamples.append(bwsample)
                if minTimestamp is None:
                        minTimestamp = timestamp
                framework.record("iperf_mbit_over_time", bwsample, timestamp - minTimestamp)
    framework.record("iperf_mbit_avg", sum(bwsamples) / len(bwsamples), offset=5)
    
def runFctExperiment(h1, h2, schedName, schedName2):
    print "run with", schedName, schedName2
    h1.cmd('python -u server.py 8080 {{fct_number_of_requests}} {{fct_request_size}} send server.log ' + schedName2 + ' {{fctTest_waitForSubflowEstablishment}} &> server.out &')
    h2.cmd('python -u client.py 10.0.0.1 8080 {{fct_number_of_requests}} {{fct_request_size}} send client.log ' + schedName + ' {{fctTest_waitForSubflowEstablishment}} &> client.out')
    
    framework.addLogfile('server.out')
    framework.addLogfile('client.out')
    #framework.addLogfile('server.log') in general, we do not have a server.log
    framework.addLogfile('client.log')

    # store results in framework
    minTimestamp = None
    with open('client.log') as clientLog:
        for line in clientLog:
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            if parts[0] == "flow_begin":
                continue
            if minTimestamp is None:
                minTimestamp = float(parts[0])
            framework.record("AppLayerRTT", float(parts[2]), offset=float(parts[0]) - minTimestamp)

def runCbrExperiment(h1, h2, schedName, schedName2):
    direction_server_receiver = 0
    direction_server_sender = 1
    direction_client_receiver = 1
    direction_client_sender = 0
    os.system("chmod +x cbr_server")
    os.system("chmod +x cbr_client")
    h1.cmd('./cbr_server 8080 {{cbr_bitrate}} {{cbr_duration}} ' + str(direction_server_receiver) + ' &> server.out &')
    h2.cmd('./cbr_client 10.0.0.1 8080 {{cbr_bitrate}} {{cbr_duration}} ' + str(direction_client_sender) + ' &> client.out')
    
    time.sleep(2)

    framework.addLogfile('server.out')
    framework.addLogfile('client.out')
    
    i = 0
    with open('server.out') as serverLog:
        for line in serverLog:
            # just lines of time spans (in ms) it took to read what was expected in one second (1000 ms)
            if line[-1] != "" and line != "finished":
                framework.record("cbr_for_1s", int(line[:-1]), offset = i)
                error = math.pow(1000 - int(line[:-1]), 2)
                framework.record("cbr_error", error, offset = i)
                i = i + 1

if __name__ == '__main__':
    framework.start()

    # we ignore the seed here, but we do not want to get a warning
    framework.param("seed")

    usedLinuxKernel = subprocess.check_output("uname -a", shell=True)
    framework.log("Used Linux kernel", usedLinuxKernel)

    loadedSchedulers = subprocess.check_output("cat /proc/net/mptcp_net/rbs/schedulers", shell=True)
    framework.log("Loaded schedulers", loadedSchedulers)

    # clean up
    os.system('sudo mn -c')
    os.system('sudo dmesg -c > /dev/null')

    # configure system    
    os.system('sysctl -w net.mptcp.mptcp_enabled=1')
    os.system("echo 1 > /proc/sys/net/ipv6/conf/all/disable_ipv6")
    os.system('sysctl -w net.mptcp.mptcp_debug={{mptcp_debug}}')
    os.system('sysctl -w net.mptcp.mptcp_path_manager=fullmesh')

    # configure scheduler
    ProgMP.setDefaultScheduler('simple')
    if "{{scheduler}}" == "default":
        os.system('sysctl -w net.mptcp.mptcp_scheduler=default')
        schedName = "norbs"
        schedName2 = "norbs"
    elif "{{scheduler}}" == "redundant":
        os.system('sysctl -w net.mptcp.mptcp_scheduler=redundant')
        schedName = "norbs"
        schedName2 = "norbs"
    elif "{{scheduler}}" == "roundrobin":
        os.system('sysctl -w net.mptcp.mptcp_scheduler=roundrobin')
        schedName = "norbs"
        schedName2 = "norbs"
    else:
        os.system('sysctl -w net.mptcp.mptcp_scheduler=rbs')
        schedName = progmp_helper.loadSchedulerFromFile("{{scheduler}}.progmp")
        if schedName == "":
            print "\n\n#### ProgMP scheduler loading error\n\n"
            if not os.path.isfile("{{scheduler}}.progmp"):
                print "Scheduler file not found." 
            os.system('dmesg > dmesg.log')
            try:
                with open('dmesg.log', 'r') as myfile:
                    print myfile.read()
            except IOError:
                framework.warn(filename, "IO Error while adding logfile for dmesg")
            
            framework.stop()
            exit(1)
        schedName2 = progmp_helper.loadSchedulerFromFile("{{scheduler}}.progmp")
        
        # Here, we set rbs to the default. You might want to remove 
        # this line and choose the scheduler per client
        os.system('echo ' + schedName + ' > /proc/net/mptcp_net/rbs/default')
        print "use rbs scheduler ", schedName, "and", schedName2

    # debug output?
    os.system("echo 0 > /sys/module/mptcp_rbs_sched/parameters/mptcp_rbs_extended_msgs")
    os.system("echo 0 > /sys/module/mptcp_rbs_sched/parameters/mptcp_rbs_check_for_gaps_in_seq")
    os.system("echo 0 > /sys/module/mptcp_rbs_sched/parameters/mptcp_rbs_check_for_work_conservingness")
    os.system("echo 0 > /sys/module/mptcp_rbs_sched/parameters/mptcp_ooo_opt")

    ignoreSbfCwnd = subprocess.check_output("cat /sys/module/mptcp_rbs_sched/parameters/ignoreSbfCwndConfig", shell=True)
    framework.log("ignoreSbfCwndConfig", ignoreSbfCwnd)


    # start experiment
    net = Mininet(topo=StaticTopo(), link=TCLink, controller = OVSController)
    net.start()
    h1 = net.get('h1')
    h2 = net.get('h2')

    if {{packet_trace}} == 1:
        print "Start packet trace"
        os.system("tcpdump -w mydump.pcap &")

    # configure IP adresses (there is probably a better way)
    for i in range(0, 2):
        h1.cmd('ifconfig h1-eth' + str(i) + ' 1' + str(i) + '.0.0.1')
        h2.cmd('ifconfig h2-eth' + str(i) + ' 1' + str(i) + '.0.0.2')

    # heat up the network
    if {{no_heat_up}} == 1:
        framework.warn("heat up", "no heat up is just for illustration, be careful")
    else:
        for i in range(0, 2):
            h1.cmd("ping 1" + str(i) + ".0.0.2 -c 4 > ping_" + str(i) + ".log")
            framework.addLogfile("ping_" + str(i) + ".log")

    bwmng.bw_monitor_start([h1, h2])

    # EXPERIMENT CODE

    if "{{trafficPattern}}" == "iperf":
        runIperfExperiment(h1, h2)
    elif "{{trafficPattern}}" == "fct":
        runFctExperiment(h1, h2, schedName, schedName2)
    elif "{{trafficPattern}}" == "cbr":
        runCbrExperiment(h1, h2, schedName, schedName2)
    else:
        framework.warn("traffic pattern", "provided traffic pattern not supported")
        framework.stop()
        exit(1)

    # END OF ACTUAL EXPERIMENT CODE

    time.sleep(2)
    bwmng.bw_monitor_stop()
    collectTotalSendData()

    if {{packet_trace}} == 1:
        os.system("pkill tcpdump")
        time.sleep(1)
        framework.addLogfile("mydump.pcap")

    net.stop()

    os.system('dmesg > dmesg.log')
    framework.addLogfile('dmesg.log')

    # Most schedulers do not print debug stuff, but parsing nothing does not harm
    parseProgMpOutput()

    # clean progmp scheduler if used progmp
    if schedName != "norbs":
        time.sleep(1)
        ProgMP.setDefaultScheduler('simple')
        ProgMP.removeScheduler(schedName)
        ProgMP.removeScheduler(schedName2)
    
    framework.stop()