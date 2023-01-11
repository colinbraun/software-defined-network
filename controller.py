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

# Please do not modify the name of the log file, otherwise you will lose points because the grader won't be able to find your log file
LOG_FILE = "Controller.log"

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
        self.num_switches = int(self.config_lines[0])
        self.switch_ips = [""] * self.num_switches
        self.switch_ports = [-1] * self.num_switches

        # Create a socket
        self.sock = socket(AF_INET, SOCK_DGRAM)
        self.sock.bind(("localhost", port))

    def bootstrap(self):
        """
        Run the bootstrap code.
        1. Wait for all switches to have sent their register request
        """
        #--------------WAIT FOR ALL SWITCH REQUESTS-------------
        num_requests = 0
        while num_requests < self.num_switches:
            data, addr = self.sock.recvfrom(1024) # buffer size is 1024 bytes
            data = data.decode("utf-8")
            switch_id = int(data[0])
            print("received message: %s" % data)
            print(addr)
            print(switch_id)
            self.switch_ips[switch_id] = addr[0]
            self.switch_ports[switch_id] = addr[1]
            num_requests += 1

        # Compute the routing table
        self.compute_routes()
        # Send the register responses
        for switch_id in range(self.num_switches):
            self.send_register_response(switch_id)

    def compute_routes(self):
        """
        Compute the routing table based on the information in the config file.
        """
        #-------------------COMPUTE ROUTING TABLE-----------
        rt_table = []
        lengths = {}
        self.neighbors = [[] for i in range(self.num_switches)]
        for line in self.config_lines[1:]:
            node1, node2, dist = line.split(" ")
            node1 = int(node1)
            node2 = int(node2)
            dist = int(dist)
            lengths[(node1, node2)] = dist
            lengths[(node2, node1)] = dist
            self.neighbors[node1].append(node2)
            self.neighbors[node2].append(node1)
        # Find the shortest paths for each node
        for node_num in range(self.num_switches):
            costs = [9999] * self.num_switches
            costs[node_num] = 0
            pred = [node_num] * self.num_switches
            reached = set()
            candidates = []
            heappush(candidates, node_num)
            while candidates != []:
                x = heappop(candidates)
                reached.add(x)
                for y in self.neighbors[x]:
                    if y not in reached:
                        if costs[x] + lengths[(x, y)] < costs[y]:
                            if costs[y] == 9999:
                                heappush(candidates, y)
                            costs[y] = costs[x] + lengths[(x, y)]
                            pred[y] = x
            # Done computing paths for this node, add to table
            for dest in range(self.num_switches):
                next_hop = dest
                length = costs[dest]
                while pred[next_hop] != node_num:
                    next_hop = pred[next_hop]
                data = [node_num, dest, next_hop, length]
                rt_table.append(data)
        # -------------DONE COMPUTING ROUTING TABLE-----------------
        self.rt_table = rt_table

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


def main():
    #Check for number of arguments and exit if host/port not provided
    num_args = len(sys.argv)
    if num_args < 3:
        print ("Usage: python controller.py <port> <config file>\n")
        sys.exit(1)

    controller = Controller(int(sys.argv[1]), "Config/graph_6.txt")
    # Run the bootstrap process of the controller
    controller.bootstrap()
    
if __name__ == "__main__":
    main()

