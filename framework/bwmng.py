import os

import framework

# dependency bwm-ng
def bw_monitor_start(hosts):
    print "now in bw start"
    global bw_monitors
    os.system("pkill bwm-ng")
    bw_monitors = []
    for host in hosts:
        bw_monitors.append((host, host.popen("bwm-ng -o csv -t 1000 -c 0 -F bw_" + str(host))))

def bw_monitor_stop():
    print "now in bw stop"
    global bw_monitors
    for (h, p) in bw_monitors:
        print "now adding", "bw_" + str(h)
        framework.addLogfile("bw_" + str(h))
        
        p.send_signal( 2 ) # SIGINT
        timeOffset = None
        for line in open("bw_" + str(h), "r"):
            parts = line.split(";")
            if len(parts) < 5:
                break
            
            time = float(parts[0])
            if timeOffset is None:
                timeOffset = time
                
            intf = parts[1]
            try:
                bwOut = float(parts[2]) / 1000 # kbyte
                bwIn = float(parts[3]) / 1000 # kbyte
                framework.record("bwm-ng-kbyte-in-" + intf, bwIn, time - timeOffset)
                framework.record("bwm-ng-kbyte-out-" + intf, bwOut, time - timeOffset)
            except ValueError:
                print "Cant parse bwm values for row", line
