import threading
import datetime
import time
from scipy import rand 
date_time = datetime.datetime.now()
import random
import rpyc
import sys

# global variables
processes = []
listOfPorts = []
queueForTimestamp = {}
states = ["HELD", "WANTED", "DO-NOT-WANT"]
critical_section_time = [10, 10]
time_out = [5, 10]
listOfPorts = []
criticalSectionResource = "Hello"
isCriticalSectionEmpty = False


class Process(threading.Thread):
    def __init__(self, id, data, state, timestamp, time_out, server):
        # creating server with thread in background
        threading.Thread.__init__(self, target=server.start)
        self.id = id
        self.data = None
        self.state = state
        self.timestamp = timestamp
        self.time_out = time_out
        self.server = server

    def exitCS(self):
        global isCriticalSectionEmpty
        self.state = "DO-NOT-WANT"
        self.data = criticalSectionResource
        isCriticalSectionEmpty = False
        self.timestamp = int(datetime.datetime.now().second)
        del queueForTimestamp[self.id]

    def criticalSection(self):
        self.state = "HELD"
        global isCriticalSectionEmpty
        cs_time = random.randint(critical_section_time[0], critical_section_time[1])
        isCriticalSectionEmpty = True
        threading.Timer(cs_time, self.exitCS).start()

    def changeState(self):
        index = states.index(self.state)
        if index != 0 and index != 1:
            self.state = states[index-1]
            self.timestamp = int(datetime.datetime.now().second)
            # asking from other threads if it is okay via rypc
            answers = connectThreads_GetState(self.id)
            queueForTimestamp[self.id] = (self.id + self.timestamp + self.time_out)
            if 'NO' not in answers and isCriticalSectionEmpty == False:
                self.timestamp = int(datetime.datetime.now().second)
                self.state = states[index-2]
                self.criticalSection()
        
    def changeStateAfterTimeOut(self):
        threading.Timer(self.time_out, self.changeState).start()


# Service for threads
class Service(rpyc.Service):
    def exposed_get_status(self, id):
        if processes[id].state == "DO-NOT-WANT":
            return "OK"
        else:
            return "NO" 

# creating threads
def createThreadsConcurrently(numberOfThreads):
    initialStates = "DO-NOT-WANT"
    port = 2022
    for t in range(numberOfThreads):
        initialTimeStamp = int(datetime.datetime.now().second)
        time_outs = random.randint(time_out[0], time_out[1])
        server = rpyc.utils.server.ThreadedServer(Service, port = port)
        th = Process(t, "shared_resources", initialStates, initialTimeStamp, time_outs, server)
        processes.append(th)
        processes[t].daemon = True
        processes[t].start()
        listOfPorts.append(port)
        port += 1
        time.sleep(0.2)
        processes[t].changeStateAfterTimeOut()

def accessCSFromQeueu():
    id = 0 
    if isCriticalSectionEmpty == False:
        if sorted(queueForTimestamp.items(), key=lambda x: x[1], reverse=False) != []:
            id = sorted(queueForTimestamp.items(), key=lambda x: x[1], reverse=False)[0][0]
            processes[id].criticalSection()

def listPorcesses():
    for t in range(len(processes)):
        print(f"P{processes[t].id}, {processes[t].state}") 

# connecting threads through rypc and getting OK or NOT reply
def connectThreads_GetState(client_id):
    id = 0
    answers = []
    for port in listOfPorts:
        if id != client_id:
            # connecting to thread server
            conn = rpyc.connect('localhost', port)
            answers.append(conn.root.exposed_get_status(id))
        id += 1
    return answers

def update_threads_time_outs(t):
    newTime = t
    global time_out
    time_out[1] = newTime
    for p in processes:
        p.time_out = random.randint(time_out[0], time_out[1])

# change states of threads
def changeStatuses():
    for p in processes:
        p.changeStateAfterTimeOut()

# stop threads
def stop():
    for p in processes:
        p.join() 

def main(argument):
    N = int(argument[1])
    if N < 0:
        print("Try to run program again, N should not be below the zero")
    else:
        createThreadsConcurrently(N)
        while True:
            command = input().lower().split(" ")
            cmd = command[0]

            if cmd == "list":
                listPorcesses()
            elif cmd == "time-cs":
                global critical_section_time
                t = int(command[1])
                critical_section_time[1] = t
                print("Critical Section time updated")
            elif cmd == "time-p":
                t = int(command[1])
                update_threads_time_outs(t)
                print("Time outs for every thread updated")
            elif cmd == "exit":
                stop()
                break
            
            changeStatuses()
            accessCSFromQeueu()

if __name__ == "__main__":
    main(sys.argv)