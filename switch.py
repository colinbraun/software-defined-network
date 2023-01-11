#!/usr/bin/env python

"""This is the Switch Starter Code for ECE50863 Lab Project 1
Author: Xin Du
Email: du201@purdue.edu
Last Modified Date: December 9th, 2021
"""

import sys
from datetime import date, datetime
from socket import *

# Please do not modify the name of the log file, otherwise you will lose points because the grader won't be able to find your log file
LOG_FILE = "switch#.log" # The log file for switches are switch#.log, where # is the id of that switch (i.e. switch0.log, switch1.log). The code for replacing # with a real number has been given to you in the main function.

# Those are logging functions to help you follow the correct logging standard

# "Register Request" Format is below:
#
# Timestamp
# Register Request Sent

def register_request_sent():
    log = []
    log.append(str(datetime.time(datetime.now())) + "\n")
    log.append(f"Register Request Sent\n")
    write_to_log(log)

# "Register Response" Format is below:
#
# Timestamp
# Register Response Received

def register_response_received():
    log = []
    log.append(str(datetime.time(datetime.now())) + "\n")
    log.append(f"Register Response received\n")
    write_to_log(log) 

# For the parameter "routing_table", it should be a list of lists in the form of [[...], [...], ...]. 
# Within each list in the outermost list, the first element is <Switch ID>. The second is <Dest ID>, and the third is <Next Hop>.
# "Routing Update" Format is below:
#
# Timestamp
# Routing Update 
# <Switch ID>,<Dest ID>:<Next Hop>
# ...
# ...
# Routing Complete
# 
# You should also include all of the Self routes in your routing_table argument -- e.g.,  Switch (ID = 4) should include the following entry: 		
# 4,4:4

def routing_table_update(routing_table):
    log = []
    log.append(str(datetime.time(datetime.now())) + "\n")
    log.append("Routing Update\n")
    for row in routing_table:
        log.append(f"{row[0]},{row[1]}:{row[2]}\n")
    log.append("Routing Complete\n")
    write_to_log(log)

# "Unresponsive/Dead Neighbor Detected" Format is below:
#
# Timestamp
# Neighbor Dead <Neighbor ID>

def neighbor_dead(switch_id):
    log = []
    log.append(str(datetime.time(datetime.now())) + "\n")
    log.append(f"Neighbor Dead {switch_id}\n")
    write_to_log(log) 

# "Unresponsive/Dead Neighbor comes back online" Format is below:
#
# Timestamp
# Neighbor Alive <Neighbor ID>

def neighbor_alive(switch_id):
    log = []
    log.append(str(datetime.time(datetime.now())) + "\n")
    log.append(f"Neighbor Alive {switch_id}\n")
    write_to_log(log) 

def write_to_log(log):
    with open(LOG_FILE, 'a+') as log_file:
        log_file.write("\n\n")
        # Write to log
        log_file.writelines(log)

class Switch:

    def __init__(self, switch_id, controller_port, controller_hostname="localhost"):
        """
        Switch constructor.
        """
        self.switch_id = switch_id
        self.controller_hostname = controller_hostname
        self.controller_port = controller_port
        self.controller_address = (controller_hostname, controller_port)
        self.sock = socket(AF_INET, SOCK_DGRAM)
        # To be updated when registering
        self.neighbor_ids = None
        self.neighbor_addrs = None
        self.neighbor_statuses = None
        # sock.bind(("localhost", int(sys.argv[1])))

    def bootstrap(self):
        """
        Run the bootstrap code. Always run this first after constructing this object.
        """
        self.send_register_request()
        # Initially assume all other neighbors are alive
        self.neighbor_statuses = [True] * len(self.neighbor_addrs)

    def send_register_request(self):
        """
        Send a register request to the controller. Waits for a register response from the controller and returns once received.
        """
        # Construct the message
        message = f"{self.switch_id} Register_Request"
        b_message = message.encode("utf-8")
        # Send it
        self.sock.sendto(b_message, self.controller_address)
        # Log that a register request was sent
        register_request_sent()
        # Wait for the register response
        data, addr = self.sock.recvfrom(1024)
        message = data.decode("utf-8")
        lines = message.split("\n")
        num_neighbors = int(lines[0])
        # The addresses (hostname, port) of the neighbors
        self.neighbor_addrs = [None] * num_neighbors
        # The ids of the neighbors
        self.neighbor_ids = [-1] * num_neighbors
        for neighbor_index in range(num_neighbors):
            parts = lines[neighbor_index + 1].split(" ")
            self.neighbor_ids[neighbor_index] = int(parts[0])
            self.neighbor_addrs[neighbor_index] = (parts[1], int(parts[2]))

    def send_keep_alive(self):
        """
        Send the keep-alive message to all neighbor switches.
        """
        message = f"{self.switch_id} KEEP_ALIVE"
        b_message = message.encode("utf-8")
        for neighbor_addr in self.neighbor_addrs:
            self.sock.sendto(b_message, neighbor_addr)
    
    def send_topology_update(self):
        """
        Send a topology update to the controller, detailing which neighbors are still alive and which are dead.
        """
        message = f"{self.switch_id}\n"
        for i, neighbor_id in enumerate(self.neighbor_ids):
            message += f"{neighbor_id} {self.neighbor_statuses[i]}\n"

        b_message = message.encode("utf-8")
        self.sock.sendto(b_message, self.controller_address)

    

def main():

    global LOG_FILE

    #Check for number of arguments and exit if host/port not provided
    num_args = len(sys.argv)
    if num_args < 4:
        print ("switch.py <Id_self> <Controller hostname> <Controller Port>\n")
        sys.exit(1)

    my_id = int(sys.argv[1])
    LOG_FILE = 'switch' + str(my_id) + ".log" 
    switch = Switch(my_id, int(sys.argv[3]))
    switch.bootstrap()

    # Write your code below or elsewhere in this file

if __name__ == "__main__":
    main()
