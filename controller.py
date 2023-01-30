#!/usr/bin/env python

"""This is the Controller Starter Code for ECE50863 Lab Project 1
Author: Xin Du
Email: du201@purdue.edu
Last Modified Date: December 9th, 2021
"""

import sys
from datetime import date, datetime
from socket import *
from heapq import *
import threading
import time

# Please do not modify the name of the log file, otherwise you will lose points because the grader won't be able to find your log file
LOG_FILE = "Controller.log"
K = 2
TIMEOUT = 3 * K

# Those are logging functions to help you follow the correct logging standard

# "Register Request" Format is below:
#
# Timestamp
# Register Request <Switch-ID>

def register_request_received(switch_id):
    log = []
    log.append(str(datetime.time(datetime.now())) + "\n")
    log.append(f"Register Request {switch_id}\n")
    write_to_log(log)

# "Register Responses" Format is below (for every switch):
#
# Timestamp
# Register Response <Switch-ID>

def register_response_sent(switch_id):
    log = []
    log.append(str(datetime.time(datetime.now())) + "\n")
    log.append(f"Register Response {switch_id}\n")
    write_to_log(log) 

# For the parameter "routing_table", it should be a list of lists in the form of [[...], [...], ...]. 
# Within each list in the outermost list, the first element is <Switch ID>. The second is <Dest ID>, and the third is <Next Hop>, and the fourth is <Shortest distance>
# "Routing Update" Format is below:
#
# Timestamp
# Routing Update 
# <Switch ID>,<Dest ID>:<Next Hop>,<Shortest distance>
# ...
# ...
# Routing Complete
#
# You should also include all of the Self routes in your routing_table argument -- e.g.,  Switch (ID = 4) should include the following entry: 		
# 4,4:4,0
# 0 indicates ‘zero‘ distance
#
# For switches that can’t be reached, the next hop and bandwidth should be ‘-1’ and ‘9999’ respectively. (9999 means infinite distance so that that switch can’t be reached)
#  E.g, If switch=4 cannot reach switch=5, the following should be printed
#  4,5:-1,9999
#
# For any switch that has been killed, do not include the routes that are going out from that switch. 
# One example can be found in the sample log in starter code. 
# After switch 1 is killed, the routing update from the controller does not have routes from switch 1 to other switches.

def routing_table_update(routing_table):
    log = []
    log.append(str(datetime.time(datetime.now())) + "\n")
    log.append("Routing Update\n")
    for row in routing_table:
        log.append(f"{row[0]},{row[1]}:{row[2]},{row[3]}\n")
    log.append("Routing Complete\n")
    write_to_log(log)

# "Topology Update: Link Dead" Format is below: (Note: We do not require you to print out Link Alive log in this project)
#
#  Timestamp
#  Link Dead <Switch ID 1>,<Switch ID 2>

def topology_update_link_dead(switch_id_1, switch_id_2):
    log = []
    log.append(str(datetime.time(datetime.now())) + "\n")
    log.append(f"Link Dead {switch_id_1},{switch_id_2}\n")
    write_to_log(log) 

# "Topology Update: Switch Dead" Format is below:
#
#  Timestamp
#  Switch Dead <Switch ID>

def topology_update_switch_dead(switch_id):
    log = []
    log.append(str(datetime.time(datetime.now())) + "\n")
    log.append(f"Switch Dead {switch_id}\n")
    write_to_log(log) 

# "Topology Update: Switch Alive" Format is below:
#
#  Timestamp
#  Switch Alive <Switch ID>

def topology_update_switch_alive(switch_id):
    log = []
    log.append(str(datetime.time(datetime.now())) + "\n")
    log.append(f"Switch Alive {switch_id}\n")
    write_to_log(log) 

def write_to_log(log):
    with open(LOG_FILE, 'a+') as log_file:
        log_file.write("\n\n")
        # Write to log
        log_file.writelines(log)


class Controller:

    def __init__(self, port, config_file):
        self.port = port

        # Read in the configuration file
        file = open(config_file, "r")
        self.config_lines = file.readlines()
        config_copy = self.config_lines.copy()
        config_copy.insert(0, "START LOGGING CONFIG FILE\n")
        config_copy.append("END LOGGING CONFIG FILE\n")
        write_to_log(config_copy)
        self.total_switches = int(self.config_lines[0])
        self.num_online_switches = 0
        self.switch_hostnames = [""] * self.total_switches
        self.switch_ports = [-1] * self.total_switches
        self.last_update_times = [-1.0] * self.total_switches
        # A list containing True or False when indexed by a switch id indicating alive or dead
        self.switch_statuses = [False] * self.total_switches

        # Create a socket
        self.sock = socket(AF_INET, SOCK_DGRAM)
        self.sock.bind(("localhost", port))

        # Determine the lengths and initially the neighbors of the switches from the config file
        # This assumes that all of the links and switches start in a working state
        self.lengths = {}
        # Keep track of the original lengths so the lengths can be set back when a switch comes back online
        self.original_lengths = {}
        self.neighbors = [[] for i in range(self.total_switches)]
        for line in self.config_lines[1:]:
            node1, node2, dist = line.split(" ")
            node1 = int(node1)
            node2 = int(node2)
            dist = int(dist)
            self.lengths[(node1, node2)] = dist
            self.lengths[(node2, node1)] = dist
            self.original_lengths[(node1, node2)] = dist
            self.original_lengths[(node2, node1)] = dist
            self.neighbors[node1].append(node2)
            self.neighbors[node2].append(node1)

    def bootstrap(self):
        """
        Run the bootstrap code.
        1. Wait for all switches to have sent their register request
        """
        #--------------WAIT FOR ALL SWITCH REQUESTS-------------
        while self.num_online_switches < self.total_switches:
            # Note: Must not use await_register_request() since only send register responses once all requests happen
            data, addr = self.sock.recvfrom(1024) # buffer size is 1024 bytes
            data = data.decode("utf-8")
            switch_id = int(data[0])
            # Log that we received the register request
            register_request_received(switch_id)
            # Consider switch to be alive
            self.switch_statuses[switch_id] = True
            print("Received Register Request: %s" % data)
            print(addr)
            print(switch_id)
            self.switch_hostnames[switch_id] = addr[0]
            self.switch_ports[switch_id] = addr[1]
            self.num_online_switches += 1

        # Compute the routing table
        self.compute_routes()
        # Send the register responses and start threads to keep track of TIMEOUT
        for switch_id in range(self.num_online_switches):
            self.send_register_response(switch_id)
            # Set the last update time to now
            self.last_update_times[switch_id] = time.time()
            # Create a new thread
            new_thread = threading.Thread(target=self.thread_proc, args=(switch_id,), daemon=True)
            # Start the new thread
            new_thread.start()
            # Wait a moment to prevent all switches from timing out at the same time
            # time.sleep(0.3)
        # Send the route updates out
        for switch_id in range(self.total_switches):
            self.send_route_update(switch_id)

    def await_messages(self):
        """
        Wait for any messages from switches. This could be a topology update or a register request.

        If it is a register request: When it does, send a register response and
        create a new thread that manages checking if TIMEOUT has happened.
        """
        data, addr = self.sock.recvfrom(1024) # buffer size is 1024 bytes
        data = data.decode("utf-8")
        # Check if it is a register request
        if "Register_Request" in data:
            switch_id = int(data[0])
            print("Received Register Request: %s" % data)
            print(addr)
            print(switch_id)
            self.switch_hostnames[switch_id] = addr[0]
            self.switch_ports[switch_id] = addr[1]

            # Log that a register request was received
            register_request_received(switch_id)
            # Log that the switch is now alive
            topology_update_switch_alive(switch_id)
            # Start keeping track of time involved in TIMEOUT
            self.last_update_times[switch_id] = time.time()
            # Send register response
            self.send_register_response(switch_id)
            self.switch_statuses[switch_id] = True
            for neighbor_id in self.neighbors[switch_id]:
                # Only if the neighbor is also online, then update the lengths
                if self.switch_statuses[neighbor_id]:
                    self.lengths[(neighbor_id, switch_id)] = self.original_lengths[(neighbor_id, switch_id)]
                    self.lengths[(switch_id, neighbor_id)] = self.original_lengths[(switch_id, neighbor_id)]
            # Since the switch was previously offline, we will have a new topology. Once registered, send it out.
            self.compute_routes()
            for switch_id in range(self.total_switches):
                self.send_route_update(switch_id)
            # Create a new thread
            new_thread = threading.Thread(target=self.thread_proc, args=(switch_id,), daemon=True)
            # Start the new thread
            new_thread.start()
        # Otherwise it is a topology update
        else:
            switch_id = int(data[0])
            print(f"Topology update received from switch id {switch_id}")
            # Update the last update times
            self.last_update_times[switch_id] = time.time()
            topology_update = False
            # Skip the first and last items. First is the switch id, last is a newline at the end
            for line in data.split("\n")[1:-1]:
                neighbor_id = int(line[0])
                alive = True if "True" in line else False
                # If the link was previously dead and is now alive, we have a new topology
                if self.lengths[(switch_id, neighbor_id)] == 9999 and alive:
                    print(f"Link from {switch_id} to {neighbor_id} restored -> Topology Update")
                    # Update the length to be correct now
                    self.lengths[(switch_id, neighbor_id)] = self.original_lengths[(switch_id, neighbor_id)]
                    self.lengths[(neighbor_id, switch_id)] = self.original_lengths[(switch_id, neighbor_id)]
                    topology_update = True
                # Otherwise if the link was previously alive and now is dead, we have a new topology
                elif self.lengths[(switch_id, neighbor_id)] != 9999 and not alive:
                    print(f"Link from {switch_id} to {neighbor_id} dead -> Topology Update")
                    # Update the length to be correct now
                    self.lengths[(switch_id, neighbor_id)] = 9999
                    self.lengths[(neighbor_id, switch_id)] = 9999
                    topology_update = True
                    # Log that this happened
                    topology_update_link_dead(switch_id, neighbor_id)

            # If there is a change in topology, send it out to all the switches
            if topology_update:
                self.compute_routes()
                for switch_id in range(self.total_switches):
                    self.send_route_update(switch_id)

    def thread_proc(self, switch_id):
        """
        The method to be passed as the run method for new threads created each register request.
        """
        time_elapsed = time.time() - self.last_update_times[switch_id]
        while time_elapsed < TIMEOUT:
            # Wait until the TIMEOUT might have happened
            time.sleep(TIMEOUT - time_elapsed)
            time_elapsed = time.time() - self.last_update_times[switch_id]
        # If we have broken out of the while loop above, the switch has TIMED OUT -> Switch is dead
        # Recompute topology, send it out to all live switches, kill this thread.
        print(f"SWITCH {switch_id} HAS TIMED OUT")
        self.switch_statuses[switch_id] = False
        topology_update_switch_dead(switch_id)
        # Set the distances to and from the neighbors to this switch id to 9999
        for neighbor in self.neighbors[switch_id]:
            self.lengths[(switch_id, neighbor)] = 9999
            self.lengths[(neighbor, switch_id)] = 9999
        self.compute_routes()
        for switch_id in range(self.total_switches):
            self.send_route_update(switch_id)

    def compute_routes(self):
        """
        Compute the routing table based on the information in the config file.
        """
        #-------------------COMPUTE ROUTING TABLE-----------
        rt_table = []
        # Find the shortest paths for each node
        for node_num in range(self.total_switches):
            costs = [1E9] * self.total_switches
            costs[node_num] = 0
            pred = [node_num] * self.total_switches
            reached = set()
            candidates = []
            heappush(candidates, (node_num, 0))
            while candidates != []:
                x, _ = heappop(candidates)

                reached.add(x)
                for y in self.neighbors[x]:
                    if y not in reached:
                        if costs[x] + self.lengths[(x, y)] < costs[y]:
                            if costs[y] == 1E9:
                                heappush(candidates, (costs[x] + self.lengths[(x, y)], y))
                            costs[y] = costs[x] + self.lengths[(x, y)]
                            pred[y] = x
            # Done computing paths for this node, add to table
            for dest in range(self.total_switches):
                next_hop = dest
                length = costs[dest]
                while pred[next_hop] != node_num:
                    next_hop = pred[next_hop]
                data = [node_num, dest, next_hop, length]
                # Only if the switch is alive, add this info to the table
                if self.switch_statuses[node_num]:
                    rt_table.append(data)
        #-------------DONE COMPUTING ROUTING TABLE-----------------
        # Update destinations and distances of entries with distance >= 9999
        for row in rt_table:
            if row[3] >= 9999:
                row[2] = -1
                row[3] = 9999

        self.rt_table = rt_table
        print("Routing:")
        print(rt_table)
        # Log that we computed the routing table
        routing_table_update(rt_table)

    def send_route_update(self, switch_id):
        """
        Send the routing information that the particular switch will need.
        """
        message = f"{switch_id}\n"
        for row in self.rt_table:
            if row[0] == switch_id:
                message += f"{row[1]} {row[2]}\n"
        b_message = message.encode("utf-8")
        self.sock.sendto(b_message, ("localhost", self.switch_ports[switch_id]))

    def send_register_response(self, switch_id):
        """
        Send a register response to the given switch id.
        """
        neighbors = self.neighbors[switch_id]
        message = f"{len(neighbors)}\n"
        for neighbor in neighbors:
            message += f"{neighbor} localhost {self.switch_ports[neighbor]}\n"
        b_message = message.encode("utf-8")
        self.sock.sendto(b_message, ("localhost", self.switch_ports[switch_id]))
        # Log that the register response was sent
        register_response_sent(switch_id)


def main():
    #Check for number of arguments and exit if host/port not provided
    num_args = len(sys.argv)
    if num_args < 3:
        print ("Usage: python controller.py <port> <config file>\n")
        sys.exit(1)

    controller = Controller(int(sys.argv[1]), sys.argv[2])
    # Run the bootstrap process of the controller. This creates other threads automatically.
    controller.bootstrap()
    # Wait for messages to show up from the switches
    while True:
        # TODO: Think about whether waiting should be done by multiple threads or not. Fine for now.
        controller.await_messages()

    
if __name__ == "__main__":
    main()

