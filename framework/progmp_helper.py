from subprocess import check_call
import argparse
import os.path
import random

def setDefaultScheduler(schedulerName):
	try:
		with open ("/proc/net/mptcp_net/rbs/default", "w") as dst:
			dst.write(schedulerName)
		return True
	except:
		return False

def loadScheduler(schedulerFileName):
	try:
		with open(schedulerFileName, "r") as src:
			content = src.read()
			
		with open("/proc/net/mptcp_net/rbs/schedulers", "w") as dst:
			dst.write(content)
		# TODO more checks
		return True
	except:
		return False

def loadSchedulerFromFile(schedulerFileName):
    try:
        with open(schedulerFileName, "r") as src:
			scheduler = src.read()
        
        # Replace the name of the scheduler
        newName = 'sched' + str(random.randint(0, 99999999)).zfill(8)
        i = scheduler.index("SCHEDULER ") + len("SCHEDULER ")
        j = i + scheduler[i:].index(";")
        newContent = "SCHEDULER " + newName + scheduler[j:];        

        with open("/proc/net/mptcp_net/rbs/schedulers", "w") as dst:
            dst.write(newContent)

        if os.system("cat /proc/net/mptcp_net/rbs/" + newName + "/dump > /dev/null 2> /dev/null") != 0:
            return ""

        return newName
    except (IOError, ValueError):
        return ""

def getSchedulerName(schedulerFileName):
	with open(schedulerFileName, "r") as src:
		content = src.read()
		startIndex = content.index("SCHEDULER ") + len("SCHEDULER ")
		endIndex = content[startIndex:].index(";")
		return content[startIndex:startIndex + endIndex]

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument("-f", "--file", help="The file which contains the scheduler", required=True)
	args = parser.parse_args()
	
	if os.geteuid() != 0:
		print "You have to be root to load a new scheduler."
		exit()
	if not os.path.isfile(args.file):
		print "File ", args.file, " not found."
		exit()
	if not loadScheduler(args.file):
		print "Loading the scheduler in file ", args.file, " failed. Execute dmesg to check output."
		exit()
	schedulerName = getSchedulerName(args.file)
	if not setDefaultScheduler(schedulerName):
		print "Setting the scheduler as default failed. Execute dmesg to check output."
		exit()
	print "Scheduler", schedulerName, "loaded and set as default."