# Morphing Network Slices

## Introduction
This project shows how to use RYU SDN controller to dynamically change the topology of a predefined network. The network we take into consideration is composed of two sub-networks, each of them is made up of five switches, one of them is in the middle and is connected to all the other four swithces that may also be connected to other switches or hosts. The physical topology of the two subnetworks is thus a star topology. 
Every host can communicate with all the other hosts and can host services, the topology of the network changes based on the type of packet that is sent by the hosts.

Hosts can use three types of different services: 
documents -> TCP packet with 8880 as destination port 
messages -> TCP packet with 8888 as destination port 
video -> UDP packet with 9999 as the destination port

For documents packets the upper subnet will use a star topology and the lower one will use a ring topology.
For messages packets the upper subnet will use a line topology and the lower one will use a star topology.
For video packets the upper subnet will use a rign topology and the lower one will use a line topology.

# Image of the topology
![alt text](https://github.com/nicolacasagrande-unitn/sdn_morphing/blob/main/network_topology.png)

## How to Run 

You can run the emulation process by using the following commands:

1. From the comnetsemu repository start the virtual machine by running:
    ```bash
    vagrant up comnetsemu
    ```
2. Open two different terminals and connect to the comnetsemu virtual machine in both of them by running:
    ```bash
    vagrant ssh comnetsemu
    ```
3. In the first terminal clear Mininet using the following command:
    ```bash
    sudo mn -c
    ```
4. In the second terminal run the RYU controller in the background with:
    ```bash
    ryu-manager morphing_controller.py &
    ```
5. In the first terminal run the following command to start mininet and create the topology
    ```bash
    sudo -E python3 network.py
    ```

## How to Test
1. We can test if the network topology has been created correctly using the following command in the mininet console:
    ```bash
    links
    ```
# Testing the documents service

1. In the mininet console run two terminals for h2 and h4 using:
    ```bash
    xterm h2 h4
    ```
2. To initialize h4 as a server and start listening for TCP packets on port 8880 run the following command in the h4 terminal:
    ```bash
    iperf -s -p 8880 -b 10M
    ```
3. To send a TCP packet on port 8880 to server h4 from host h2 
    ```bash
    iperf -c 10.0.0.4 -p 8880 -b 10M -t 5 -i 1 
    ```






