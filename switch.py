#!/usr/bin/env python

"""This is the Switch Starter Code for ECE50863 Lab Project 1
Author: Xin Du
Email: du201@purdue.edu
Last Modified Date: December 9th, 2021
"""

import sys
from datetime import date, datetime
from socket import *
import time
import threading

# Please do not modify the name of the log file, otherwise you will lose points because the grader won't be able to find your log file
LOG_FILE = "switch#.log" # The log file for switches are switch#.log, where # is the id of that switch (i.e. switch0.log, switch1.log). The code for replacing # with a real number has been given to you in the main function.
K = 2
TIMEOUT = 3 * K

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

    def __init__(self, switch_id, controller_port, controller_hostname="localhost", failed_link_neighbor_id=-1):
        """
        Switch constructor.
        """
        self.switch_id = switch_id
        self.failed_link_neighbor_id = failed_link_neighbor_id
        self.controller_hostname = controller_hostname
        self.controller_port = controller_port
        self.controller_address = (controller_hostname, controller_port)
        self.sock = socket(AF_INET, SOCK_DGRAM)
        # To be updated when registering
        # This is a map that takes a neighbor's id as the key and gives an index into their other data as a value
        self.neighbor_ids_to_index = {}
        self.neighbor_addrs = None
        self.neighbor_statuses = None
        self.last_update_times = None
        # sock.bind(("localhost", int(sys.argv[1])))

    def bootstrap(self):
        """
        Run the bootstrap code. Always run this first after constructing this object.
        This creates a thread for each neighbor, keeping track of whether it has timed out or not.
        """
        self.send_register_request()
        # Start a thread to manage sending periodic keep alive and topology updates
        new_thread = threading.Thread(target=self.thread_keep_alive, daemon=True)
        new_thread.start()
        # Initially assume all other neighbors are alive
        self.neighbor_statuses = [True] * len(self.neighbor_addrs)
        self.last_update_times = [-1] * len(self.neighbor_addrs)
        for neighbor_id in self.neighbor_ids_to_index.keys():
            self.last_update_times[self.neighbor_ids_to_index[neighbor_id]] = time.time()
            new_thread = threading.Thread(target=self.thread_proc, args=(neighbor_id,), daemon=True)
            # Start the new thread
            new_thread.start()
            # Wait a moment to prevent all switches from timing out at the same time
            # time.sleep(0.3)


    def thread_proc(self, neighbor_id):
        """
        Mange whether or not the neighbor with the given id has timed out yet.
        """
        neighbor_index = self.neighbor_ids_to_index[neighbor_id]
        time_elapsed = time.time() - self.last_update_times[neighbor_index]
        while time_elapsed < TIMEOUT:
            # Wait until the TIMEOUT might have happened
            time.sleep(TIMEOUT - time_elapsed)
            time_elapsed = time.time() - self.last_update_times[neighbor_index]
        # If we have broken out of the while loop above, the switch has TIMED OUT -> link is dead
        # Recompute topology, send it out to all live switches, kill this thread.
        print(f"NEIGHBOR {neighbor_id} HAS TIMED OUT")
        neighbor_dead(neighbor_id)
        self.neighbor_statuses[neighbor_index] = False
        # Notify the controller about a topology update
        self.send_topology_update()

    def thread_keep_alive(self):
        """
        A thread to periodically send a KEEP ALIVE message to all neighbors every K seconds
        as well as a topology update to the controller.
        """
        while True:
            time.sleep(K)
            self.send_topology_update()
            # If we should simulate a failure, do nothing. Else send the keep alive like normal
            # if self.failed_link_neighbor_id == -1:
            # Above is not good. The link failure mode is now handled by send_keep_alive
            self.send_keep_alive()

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
        # Log that it was received
        register_response_received()
        message = data.decode("utf-8")
        lines = message.split("\n")
        num_neighbors = int(lines[0])
        # The addresses (hostname, port) of the neighbors
        self.neighbor_addrs = [None] * num_neighbors
        # The ids of the neighbors
        # self.neighbor_ids_to_index = [-1] * num_neighbors
        for neighbor_index in range(num_neighbors):
            parts = lines[neighbor_index + 1].split(" ")
            if parts[0] == "":
                continue
            self.neighbor_ids_to_index[int(parts[0])] = neighbor_index
            self.neighbor_addrs[neighbor_index] = (parts[1], int(parts[2]))
        # print(f"I am switch {self.switch_id}")
        # print(f"My neighbors:\n{self.neighbor_ids}")

    def send_keep_alive(self):
        """
        Send the keep-alive message to all neighbor switches.
        """
        message = f"{self.switch_id} KEEP_ALIVE"
        print(f"Switch {self.switch_id}: Sending KEEP ALIVE message to switch ids {list(self.neighbor_ids_to_index.keys())}")
        b_message = message.encode("utf-8")
        for neighbor_id in self.neighbor_ids_to_index.keys():
            neighbor_index = self.neighbor_ids_to_index[neighbor_id]
            neighbor_addr = self.neighbor_addrs[neighbor_index]
            # If this is not a link we are simulating as dead, send a keep alive message.
            if not self.failed_link_neighbor_id == neighbor_id:
                self.sock.sendto(b_message, neighbor_addr)
            else:
                print(f"Switch {self.switch_id}: DID NOT SEND KEEP ALIVE message to switch id {self.failed_link_neighbor_id}")
    
    def send_topology_update(self):
        """
        Send a topology update to the controller, detailing which neighbors are still alive and which are dead.
        """
        message = f"{self.switch_id}\n"
        print(f"Switch {self.switch_id}: Sending topology update.\nNeighbor IDs to Index: {self.neighbor_ids_to_index}\nNeighbor Statuses: {self.neighbor_statuses}\n")
        for neighbor_id in self.neighbor_ids_to_index.keys():
            message += f"{neighbor_id} {self.neighbor_statuses[self.neighbor_ids_to_index[neighbor_id]]}\n"

        b_message = message.encode("utf-8")
        self.sock.sendto(b_message, self.controller_address)

    def await_messages(self):
        """
        Wait for any messages from switches. This could be a topology update or a register request.

        If it is a register request: When it does, send a register response and
        create a new thread that manages checking if TIMEOUT has happened.
        """
        data, addr = self.sock.recvfrom(1024) # buffer size is 1024 bytes
        data = data.decode("utf-8")
        # If it is a KEEP ALIVE message, note that the connection is still alive if it was alive before
        # If it was dead before, notify the controller of a change in topology
        if "KEEP_ALIVE" in data:
            neighbor_id = int(data[0])
            print(f"Switch {self.switch_id}: Received KEEP ALIVE message from switch id {neighbor_id}")
            neighbor_index = self.neighbor_ids_to_index[neighbor_id]
            self.neighbor_addrs[neighbor_index] = addr
            # If the neighbor id is the one we are simulating as dead, stop what we're doing -> return
            if neighbor_id == self.failed_link_neighbor_id:
                return
            # Get whether it was previously alive or not
            was_alive = self.neighbor_statuses[neighbor_index]
            # Consider it alive now
            self.neighbor_statuses[neighbor_index] = True
            # Reset the timeout
            self.last_update_times[neighbor_index] = time.time()
            # If wasn't previously alive, immediately notify the controller of the change
            if not was_alive:
                self.send_topology_update()
                neighbor_alive(neighbor_id)
        # Otherwise it was a routing update from the controller. Handle it.
        else:
            switch_id = data[0]
            lines = data.split("\n")[1:-1]
            table = []
            for line in lines:
                parts = line.split(" ")
                other_id = int(parts[0])
                next_hop = int(parts[1])
                # TODO: Determine if updating this information should be done. Currently unknown.
                # If this is a neighbor switch
                # if other_id in self.neighbor_ids_to_index:
                #     other_index = self.neighbor_ids_to_index[other_id]
                #     # And if we previously thought it was a dead link but no longer is
                #     if (not self.neighbor_statuses[other_index]) and next_hop != -1:
                #         # Then assume the connection is restored and reset the timeout
                #         self.neighbor_statuses[other_index] = True
                #         self.last_update_times[other_index] = time.time()

                table.append([switch_id, other_id, next_hop])
            # Log the routing table that was received
            routing_table_update(table)


def main():

    global LOG_FILE

    #Check for number of arguments and exit if host/port not provided
    num_args = len(sys.argv)
    if num_args < 4:
        print ("switch.py <Id_self> <Controller hostname> <Controller Port>\n")
        sys.exit(1)

    my_id = int(sys.argv[1])
    LOG_FILE = 'switch' + str(my_id) + ".log" 
    controller_port = int(sys.argv[3])
    # Check if we have the -f flag, set up switch to fail if so
    if num_args == 6:
        neighbor_id = int(sys.argv[5])
        print(f"Failed link mode between {my_id} and {neighbor_id}")
        switch = Switch(my_id, controller_port, failed_link_neighbor_id=neighbor_id)
    else:
        switch = Switch(my_id, controller_port)
    switch.bootstrap()
    # time.sleep(5)
    # switch.send_topology_update()
    # Wait for messages to show up and handle them over and over again
    while True:
        switch.await_messages()

    # Write your code below or elsewhere in this file

if __name__ == "__main__":
    main()
